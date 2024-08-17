import os
import json
import logging
import asyncio
import argparse
from tkinter import messagebox
from contextlib import asynccontextmanager

import aiofiles
from dotenv import load_dotenv
from async_timeout import timeout
from anyio import create_task_group, run

import gui
import registration


class UnixTimeFormatter(logging.Formatter):
    def formatTime(self, record, datefmt=None):
        return f"[{int(record.created)}]"


class Invalidtoken(Exception):
    def __init__(self, message="Invalid token", errors=None):
        super().__init__(message)
        self.errors = errors


def get_settings():
    load_dotenv()
    parser = argparse.ArgumentParser(
        description='This is async chat. You can send messages',
    )

    parser.add_argument(
        "-t",
        "--token",
        type=str,
        default="",
        help="Your token. For example: bcd77b02-4e86-11ef-abed-02"
    )

    parser.add_argument(
        "-ph",
        "--post_host",
        type=str,
        default=os.getenv("POST_HOST"),
        help="Your host. For example: minechat.dvmn.org",
    )

    parser.add_argument(
        "-pp",
        "--post_port",
        type=int,
        default=os.getenv("POST_PORT"),
        help="Your port. For example: 5050"
    )

    parser.add_argument(
        "-gh",
        "--get_host",
        type=str,
        default=os.getenv("GET_HOST"),
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
        "-hp",
        "--history_path",
        type=str,
        default=os.getenv("HISTORY_PATH"),
        help="Path to history file. For example: messages.txt"
    )

    return parser.parse_args()


def escape_stickiness_removed(text):
    return text.replace("\\n", " ").strip()


async def watch_for_connection(watchdog_queue, watchdog_logger):
    while True:
        try:
            async with timeout(10):
                msg = await watchdog_queue.get()
                watchdog_logger.info('Connection is alive. %s', msg)

        except asyncio.TimeoutError:
            watchdog_logger.warning('Reconnecting...')
            raise ConnectionError


@asynccontextmanager
async def create_chat_connection(host, port):
    reader, writer = await asyncio.open_connection(host, port)
    try:
        yield reader, writer
    finally:
        writer.close()
        await writer.wait_closed()


async def save_messages(history_message_queue, history_path):
    async with aiofiles.open(history_path, 'a') as file:
        while True:
            msg = await history_message_queue.get()
            await file.write(msg)


async def read_messages(
        messages_queue,
        history_message_queue,
        get_host,
        get_port,
        status_updates_queue,
        watchdog_queue):

    status_updates_queue.put_nowait(gui.ReadConnectionStateChanged.INITIATED)

    async with create_chat_connection(get_host, get_port) as (reader, writer):
        status_updates_queue.put_nowait(
            gui.ReadConnectionStateChanged.ESTABLISHED)

        while True:
            message = await reader.readline()

            messages_queue.put_nowait(
                escape_stickiness_removed(message.decode()))

            history_message_queue.put_nowait(message.decode())

            watchdog_queue.put_nowait("New chat message")


async def authorise(account_hash, post_reader, post_writer):
    data = await post_reader.read(200)

    post_writer.write((account_hash + "\n").encode())

    data = await post_reader.read(200)

    if json.loads(data.decode().split("\n")[0]) is None:
        raise Invalidtoken

    nickname = json.loads(data.decode().split("\n")[0])['nickname']

    return nickname


async def send_messages(
        post_host,
        post_port,
        account_hash,
        sending_queue,
        status_updates_queue,
        watchdog_queue):

    status_updates_queue.put_nowait(
        gui.SendingConnectionStateChanged.INITIATED)

    async with create_chat_connection(post_host, post_port) as (post_reader, post_writer):
        status_updates_queue.put_nowait(
            gui.SendingConnectionStateChanged.ESTABLISHED)

        watchdog_queue.put_nowait("Prompt before auth")

        try:
            nickname = await authorise(account_hash, post_reader, post_writer)

        except Invalidtoken:
            messagebox.showerror(
                "Неверный токен",
                "Проверьте токен, сервер его не узнал."
            )
            exit(0)

        status_updates_queue.put_nowait(gui.NicknameReceived(nickname))
        watchdog_queue.put_nowait("Authorization done")

        while True:
            message = await sending_queue.get()

            message = escape_stickiness_removed(message)

            post_writer.write((message + "\n\n").encode())

            watchdog_queue.put_nowait("Message sent")


async def handle_connection(
        get_host,
        get_port,
        post_host,
        post_port,
        history_path,
        account_hash,
        watchdog_logger,
        sending_queue,
        messages_queue,
        watchdog_queue,
        status_updates_queue,
        history_message_queue):

    while True:
        try:
            async with create_task_group() as task_group:
                task_group.start_soon(
                    read_messages,
                    messages_queue,
                    history_message_queue,
                    get_host,
                    get_port,
                    status_updates_queue,
                    watchdog_queue
                )

                task_group.start_soon(
                    send_messages,
                    post_host,
                    post_port,
                    account_hash,
                    sending_queue,
                    status_updates_queue,
                    watchdog_queue
                )

                task_group.start_soon(
                    watch_for_connection,
                    watchdog_queue,
                    watchdog_logger
                )

                task_group.start_soon(
                    save_messages,
                    history_message_queue,
                    history_path
                )

        except BaseException as e:
            if isinstance(e, ConnectionError):
                status_updates_queue.put_nowait(
                    gui.ReadConnectionStateChanged.CLOSED)

                status_updates_queue.put_nowait(
                    gui.SendingConnectionStateChanged.CLOSED)

                continue

            if isinstance(e, asyncio.CancelledError):
                break


async def main(account_hash):
    formatter = UnixTimeFormatter(
        '%(asctime)s %(name)s %(levelname)s: %(message)s'
    )
    handler = logging.StreamHandler()
    handler.setFormatter(formatter)

    logging.basicConfig(level=logging.DEBUG, handlers=[handler,])
    watchdog_logger = logging.getLogger('watchdog')

    settings = get_settings()

    get_host = settings.get_host
    get_port = settings.get_port

    post_host = settings.post_host
    post_port = settings.post_port

    history_path = settings.history_path

    history_message_queue = asyncio.Queue()
    messages_queue = asyncio.Queue()
    sending_queue = asyncio.Queue()
    status_updates_queue = asyncio.Queue()
    watchdog_queue = asyncio.Queue()

    if os.path.exists(history_path):
        with open(history_path, 'r') as file:
            while True:
                msg = file.readline()
                if msg:
                    messages_queue.put_nowait(escape_stickiness_removed(msg))
                else:
                    break

    async with create_task_group() as task_group:
        task_group.start_soon(
            gui.draw,
            messages_queue,
            sending_queue,
            status_updates_queue
        )

        task_group.start_soon(
            handle_connection,
            get_host,
            get_port,
            post_host,
            post_port,
            history_path,
            account_hash,
            watchdog_logger,
            sending_queue,
            messages_queue,
            watchdog_queue,
            status_updates_queue,
            history_message_queue
        )


def check_for_registration():
    auth_file_path = "auth.json"
    token = get_settings().token

    if token:
        account_hash = token

    elif os.path.exists(auth_file_path):
        with open(auth_file_path, 'r') as file:
            account_data = file.read()
            account_hash = json.loads(account_data)['account_hash']
    else:
        registration.draw(auth_file_path)

        with open(auth_file_path, 'r') as file:
            account_data = file.read()
            account_hash = json.loads(account_data)['account_hash']

    try:
        run(main, account_hash)
    except asyncio.CancelledError:
        logging.info("Program interrupted by user")
    except BaseException:
        logging.info("Program exited gracefully")


if __name__ == '__main__':
    check_for_registration()
