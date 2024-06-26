import os
import argparse
import json
import asyncio
import aiofiles
import logging
from contextlib import asynccontextmanager

from dotenv import load_dotenv


def get_settings():
    parser = argparse.ArgumentParser(
        description='This is async chat. You can send messages',
    )

    parser.add_argument(
        "-t",
        "--token",
        type=str,
        default="",
        help="Your authorization token.",
    )

    parser.add_argument(
        "-ho",
        "--host",
        type=str,
        default=os.getenv("POST_HOST"),
        help="Your host. For example: minechat.dvmn.org",
    )

    parser.add_argument(
        "-p",
        "--port",
        type=int,
        default=os.getenv("POST_PORT"),
        help="Your port. For example: 5050"
    )

    parser.add_argument(
        "-n",
        "--name",
        type=str,
        default="",
        help="If you are not authorized, you can enter a login to register",
    )

    return parser.parse_args()


def escape_stickiness_removed(text):
    return text.replace("\\n", " ").strip()


async def register(reader, writer):
    data = await reader.read(100)

    writer.write("\n".encode())

    data = await reader.read(100)
    logging.debug(msg=data.decode())

    username = input() if not settings.name else settings.name

    writer.write((escape_stickiness_removed(username) + "\n").encode())

    response = await reader.readline()

    auth_data = json.loads(response.decode().strip())

    writer.close()

    async with aiofiles.open(auth_file_name, 'w') as file:
        await file.write(json.dumps(auth_data))

    return auth_data


async def authorise(account_hash, reader, writer):
    data = await reader.read(200)

    writer.write((account_hash + "\n").encode())

    data = await reader.read(200)

    logging.debug(msg=data.decode().split("\n")[1], extra={"type": "sender"})

    await submit_message(reader, writer)


async def submit_message(reader, writer):
    try:
        message = escape_stickiness_removed(input())

        writer.write((message + "\n\n").encode())

        logging.debug("Закрытие соединения")
        writer.close()

    except asyncio.CancelledError:
        logging.error(msg="Ошибка сетевого подключения")


@asynccontextmanager
async def create_chat_connection(host, port):
    reader, writer = await asyncio.open_connection(host, port)
    try:
        yield reader, writer
    finally:
        writer.close()
        await writer.wait_closed()


async def main():
    host = settings.host
    port = settings.port

    if settings.token:
        async with create_chat_connection(host, port) as (reader, writer):
            await authorise(settings.token, reader, writer)

    elif os.path.exists(auth_file_name):
        async with aiofiles.open(auth_file_name, 'r') as file:
            account_data = await file.read()

        account_data = json.loads(account_data)

        async with create_chat_connection(host, port) as (reader, writer):
            await authorise(account_data["account_hash"], reader, writer)

    else:
        async with create_chat_connection(host, port) as (reader, writer):
            account_data = await register(reader, writer)

        async with create_chat_connection(host, port) as (reader, writer):
            await authorise(account_data["account_hash"], reader, writer)


if __name__ == "__main__":
    load_dotenv()
    settings = get_settings()
    auth_file_name = "auth.json"

    logging.basicConfig(
        level=logging.DEBUG,
        format='%(levelname)s:sender:%(message)s',
    )
    asyncio.run(main())
