import os
import datetime
import argparse
import asyncio
import tkinter as tk
from enum import Enum
from tkinter.scrolledtext import ScrolledText
from contextlib import asynccontextmanager

import aiofiles
from dotenv import load_dotenv


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


async def save_messages(filepath, queue):
    message = await queue.get()

    decode_message = f"{message}\n"

    async with aiofiles.open(filepath, 'a') as file:
        await file.write(decode_message)


async def read_msgs(host, port, messages_queue, history_message_queue):
    async with create_chat_connection(host, port) as connection:
        reader, writer = connection

        while not reader.at_eof():
            try:
                message = await reader.readline()

                message = message.decode('utf-8').strip()

                messages_queue.put_nowait(message)
                history_message_queue.put_nowait(message)

                await save_messages(
                    settings.history_path,
                    history_message_queue
                )

            except asyncio.CancelledError:
                print("Ошибка сетевого подключения")


@asynccontextmanager
async def create_chat_connection(host, port):
    reader, writer = await asyncio.open_connection(host, port)
    try:
        yield reader, writer
    finally:
        writer.close()
        await writer.wait_closed()


async def main():
    await asyncio.gather(
        draw(messages_queue, sending_queue, status_updates_queue),
        read_msgs(
            settings.get_host,
            settings.get_port,
            messages_queue,
            history_message_queue
        )
    )


if __name__ == '__main__':
    settings = get_settings()
    loop = asyncio.get_event_loop()

    history_message_queue = asyncio.Queue()
    messages_queue = asyncio.Queue()
    sending_queue = asyncio.Queue()
    status_updates_queue = asyncio.Queue()

    if os.path.exists(settings.history_path):
        with open(settings.history_path, 'r') as file:
            for line in file.readlines():
                messages_queue.put_nowait(line.replace('\n', ''))

    loop.run_until_complete(main())
