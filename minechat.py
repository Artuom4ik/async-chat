import os
import argparse
import asyncio
import datetime
from contextlib import asynccontextmanager

import aiofiles
from dotenv import load_dotenv


def get_settings():
    load_dotenv()
    parser = argparse.ArgumentParser(
        description='This is async chat. You can see history of messages by your link',
    )

    parser.add_argument(
        "-ho",
        "--host",
        type=str,
        default=os.getenv("HOST"),
        help="Your host. For example: minechat.dvmn.org",
    )
    parser.add_argument(
        "-p",
        "--port",
        type=int,
        default=os.getenv("PORT"),
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


async def get_chat_messages(settings):
    async with create_chat_connection(settings.host, settings.port) as connection:
        reader, writer = connection

        while not reader.at_eof():
            try:
                message = await reader.readline()

                decode_message = f"{datetime.datetime.now().strftime('[%d.%m.%y %H:%M]')} {message.decode('utf-8').strip()}\n"

                async with aiofiles.open(settings.history_path, 'a') as file:
                    await file.write(decode_message)
                
                print(decode_message)
            
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
    settings = get_settings()
    await get_chat_messages(settings)


asyncio.run(main())