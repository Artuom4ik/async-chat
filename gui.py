import os
import json
import logging
import argparse
import asyncio
import tkinter as tk
import anyio.abc
import async_timeout
from tkinter import messagebox
from enum import Enum
from tkinter.scrolledtext import ScrolledText
from contextlib import asynccontextmanager

import anyio
import aiofiles
from dotenv import load_dotenv


class UnixTimeFormatter(logging.Formatter):
    def formatTime(self, record, datefmt=None):
        return f"[{int(record.created)}]"


class Invalidtoken(Exception):
    def __init__(self, message="Invalid token", errors=None):
        super().__init__(message)
        self.errors = errors


class TkAppClosed(Exception):
    pass


class ReadConnectionStateChanged(Enum):
    INITIATED = 'устанавливаем соединение'
    ESTABLISHED = 'соединение установлено'
    CLOSED = 'соединение закрыто'

    def __str__(self):
        return str(self.value)


class SendingConnectionStateChanged(Enum):
    INITIATED = 'устанавливаем соединение'
    ESTABLISHED = 'соединение установлено'
    CLOSED = 'соединение закрыто'

    def __str__(self):
        return str(self.value)


class NicknameReceived:
    def __init__(self, nickname):
        self.nickname = nickname


def get_settings():
    load_dotenv()
    parser = argparse.ArgumentParser(
        description='This is async chat. You can see history of messages by your link',
    )

    parser.add_argument(
        "-gh",
        "--get_host",
        type=str,
        default=os.getenv("GET_HOST"),
        help="Your host. For example: minechat.dvmn.org",
    )

    parser.add_argument(
        "-ph",
        "--post_host",
        type=str,
        default=os.getenv("POST_HOST"),
        help="Your host. For example: minechat.dvmn.org",
    )

    parser.add_argument(
        "-gp",
        "--get_port",
        type=int,
        default=os.getenv("GET_PORT"),
        help="Your port. For example: 5000"
    )

    parser.add_argument(
        "-pp",
        "--post_port",
        type=int,
        default=os.getenv("POST_PORT"),
        help="Your port. For example: 5050"
    )

    parser.add_argument(
        "-t",
        "--token",
        type=str,
        default="",
        help="Your authorization token.",
    )

    parser.add_argument(
        "-n",
        "--name",
        type=str,
        default="",
        help="If you are not authorized, you can enter a login to register",
    )

    parser.add_argument(
        "-hp",
        "--history_path",
        type=str,
        default=os.getenv("HISTORY_PATH"),
        help="Path to history file. For example: messages.txt"
    )

    return parser.parse_args()


def process_new_message(input_field, sending_queue):
    text = input_field.get()
    sending_queue.put_nowait(text)
    input_field.delete(0, tk.END)


async def update_tk(root_frame, interval=1 / 120):
    while True:
        try:
            root_frame.update()
        except tk.TclError:
            # if application has been destroyed/closed
            raise TkAppClosed()
        await asyncio.sleep(interval)


async def update_conversation_history(panel, messages_queue):
    while True:
        msg = await messages_queue.get()

        panel['state'] = 'normal'
        if panel.index('end-1c') != '1.0':
            panel.insert('end', '\n')
        panel.insert('end', msg)
        # TODO сделать промотку умной, чтобы не мешала просматривать историю сообщений
        # ScrolledText.frame
        # ScrolledText.vbar
        panel.yview(tk.END)
        panel['state'] = 'disabled'


async def update_status_panel(status_labels, status_updates_queue):
    nickname_label, read_label, write_label = status_labels

    read_label['text'] = f'Чтение: нет соединения'
    write_label['text'] = f'Отправка: нет соединения'
    nickname_label['text'] = f'Имя пользователя: неизвестно'

    while True:
        msg = await status_updates_queue.get()
        if isinstance(msg, ReadConnectionStateChanged):
            read_label['text'] = f'Чтение: {msg}'

        if isinstance(msg, SendingConnectionStateChanged):
            write_label['text'] = f'Отправка: {msg}'

        if isinstance(msg, NicknameReceived):
            nickname_label['text'] = f'Имя пользователя: {msg.nickname}'


def create_status_panel(root_frame):
    status_frame = tk.Frame(root_frame)
    status_frame.pack(side="bottom", fill=tk.X)

    connections_frame = tk.Frame(status_frame)
    connections_frame.pack(side="left")

    nickname_label = tk.Label(
        connections_frame,
        height=1,
        fg='grey',
        font='arial 10',
        anchor='w'
    )
    nickname_label.pack(side="top", fill=tk.X)

    status_read_label = tk.Label(
        connections_frame,
        height=1, fg='grey',
        font='arial 10',
        anchor='w'
    )
    status_read_label.pack(side="top", fill=tk.X)

    status_write_label = tk.Label(
        connections_frame,
        height=1,
        fg='grey',
        font='arial 10',
        anchor='w'
    )
    status_write_label.pack(side="top", fill=tk.X)

    return (nickname_label, status_read_label, status_write_label)


async def draw(messages_queue, sending_queue, status_updates_queue):
    root = tk.Tk()

    root.title('Чат Майнкрафтера')

    root_frame = tk.Frame()
    root_frame.pack(fill="both", expand=True)

    status_labels = create_status_panel(root_frame)

    input_frame = tk.Frame(root_frame)
    input_frame.pack(side="bottom", fill=tk.X)

    input_field = tk.Entry(input_frame)
    input_field.pack(side="left", fill=tk.X, expand=True)

    input_field.bind("<Return>", lambda event: process_new_message(
        input_field,
        sending_queue))

    send_button = tk.Button(input_frame)
    send_button["text"] = "Отправить"
    send_button["command"] = lambda: process_new_message(
        input_field,
        sending_queue
    )
    send_button.pack(side="left")

    conversation_panel = ScrolledText(root_frame, wrap='none')
    conversation_panel.pack(side="top", fill="both", expand=True)

    await asyncio.gather(
        update_tk(root_frame),
        update_conversation_history(conversation_panel, messages_queue),
        update_status_panel(status_labels, status_updates_queue)
    )


def escape_stickiness_removed(text):
    return text.replace("\\n", " ").strip()


async def authorise(account_hash, post_reader, post_writer):
    watchdog_queue.put_nowait('Prompt before auth')

    data = await post_reader.read(200)

    post_writer.write((account_hash + "\n").encode())

    data = await post_reader.read(200)

    if json.loads(data.decode().split("\n")[0]) is None:
        raise Invalidtoken

    nickname = json.loads(data.decode().split("\n")[0])['nickname']

    status_updates_queue.put_nowait(NicknameReceived(nickname=nickname))

    status_updates_queue.put_nowait(SendingConnectionStateChanged.ESTABLISHED)

    watchdog_queue.put_nowait('Authorization done')


async def save_messages(filepath, queue):
    message = await queue.get()

    decode_message = f"{message}\n"

    async with aiofiles.open(filepath, 'a') as file:
        await file.write(decode_message)


async def read_msgs(
        get_host,
        get_port,
        messages_queue,
        history_message_queue,
        watchdog_queue):
    while True:
        status_updates_queue.put_nowait(
            ReadConnectionStateChanged.INITIATED
        )

        async with create_chat_connection(get_host, get_port) as connection:
            reader, writer = connection

            status_updates_queue.put_nowait(ReadConnectionStateChanged.ESTABLISHED)

            try:
                while not reader.at_eof():
                    async with async_timeout.timeout(2) as cm:
                        message = await reader.readline()

                        message = message.decode('utf-8').strip()

                        messages_queue.put_nowait(message)
                        history_message_queue.put_nowait(message)

                        watchdog_queue.put_nowait('New message in chat')

                        await save_messages(
                            settings.history_path,
                            history_message_queue
                        )

            except asyncio.TimeoutError:
                status_updates_queue.put_nowait(ReadConnectionStateChanged.CLOSED)
                watchdog_queue.put_nowait('1s timeout is elapsed')


async def send_msgs(
        post_host,
        post_port,
        sending_queue,
        watchdog_queue):

    status_updates_queue.put_nowait(
        SendingConnectionStateChanged.INITIATED
    )

    async with create_chat_connection(post_host, post_port) as (post_reader, post_writer):
        if settings.token:
            await authorise(settings.token, post_reader, post_writer)

        elif os.path.exists(auth_file_name):
            async with aiofiles.open(auth_file_name, 'r') as file:
                account_data = await file.read()

            account_data = json.loads(account_data)

            await authorise(account_data["account_hash"], post_reader, post_writer)

        while True:
            message = await sending_queue.get()

            message = escape_stickiness_removed(message)

            post_writer.write((message + "\n\n").encode())

            watchdog_queue.put_nowait('Message sent')


@asynccontextmanager
async def create_chat_connection(host, port):
    reader, writer = await asyncio.open_connection(host, port)
    try:
        yield reader, writer
    finally:
        writer.close()
        await writer.wait_closed()


async def watch_for_connection():
    while True:
        try:
            msg = await watchdog_queue.get()
            watchdog_logger.info('Connection is alive. %s', msg)

        except asyncio.CancelledError:
            watchdog_logger.warning('Connection aborted')
            break


async def handle_connection(
        get_host,
        get_port,
        post_host,
        post_port,
        status_updates_queue,
        messages_queue,
        sending_queue,
        watchdog_queue):

    while True:
        try:
            async with anyio.create_task_group() as task_group:
                status_updates_queue.put_nowait(
                    ReadConnectionStateChanged.INITIATED
                )
                status_updates_queue.put_nowait(
                    SendingConnectionStateChanged.INITIATED
                )

                task_group.start_soon(
                    read_msgs,
                    get_host,
                    get_port,
                    messages_queue,
                    history_message_queue,
                    watchdog_queue,
                )
                task_group.start_soon(
                    send_msgs,
                    post_host,
                    post_port,
                    sending_queue,
                    watchdog_queue,
                )

                task_group.start_soon(watch_for_connection)

        except BaseException as e:
            if isinstance(e, ConnectionError):
                status_updates_queue.put_nowait(
                    ReadConnectionStateChanged.CLOSED
                )
                status_updates_queue.put_nowait(
                    SendingConnectionStateChanged.CLOSED
                )

            continue


async def main():
    get_host = settings.get_host
    post_host = settings.post_host
    get_port = settings.get_port
    post_port = settings.post_port

    try:
        await asyncio.gather(
            draw(messages_queue, sending_queue, status_updates_queue),
            handle_connection(
                get_host=get_host,
                get_port=get_port,
                post_host=post_host,
                post_port=post_port,
                status_updates_queue=status_updates_queue,
                messages_queue=messages_queue,
                sending_queue=sending_queue,
                watchdog_queue=watchdog_queue
            )
        )

    except Invalidtoken:
        messagebox.showinfo(
            'Неверный токен',
            'Проверьте токен, сервер его не узнал'
        )


if __name__ == '__main__':
    formatter = UnixTimeFormatter(
        '%(asctime)s %(name)s %(levelname)s: %(message)s'
    )
    handler = logging.StreamHandler()
    handler.setFormatter(formatter)

    logging.basicConfig(level=logging.DEBUG, handlers=[handler,])
    watchdog_logger = logging.getLogger('watchdog')

    settings = get_settings()
    loop = asyncio.get_event_loop()

    history_message_queue = asyncio.Queue()
    messages_queue = asyncio.Queue()
    sending_queue = asyncio.Queue()
    status_updates_queue = asyncio.Queue()
    watchdog_queue = asyncio.Queue()

    auth_file_name = "auth.json"

    if os.path.exists(settings.history_path):
        with open(settings.history_path, 'r') as file:
            for line in file.readlines():
                messages_queue.put_nowait(line.replace('\n', ''))

    loop.run_until_complete(main())
