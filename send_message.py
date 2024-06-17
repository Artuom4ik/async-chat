import os
import asyncio
from contextlib import asynccontextmanager

from dotenv import load_dotenv


async def send_messages(message):
    load_dotenv()
    account_hash = os.getenv("ACCOUNT_HASH")

    async with create_chat_connection("minechat.dvmn.org", 5050) as connection:
        try:
            reader, writer = connection

            writer.write((account_hash + "\n").encode())
            writer.write((message + "\n\n").encode())

            print('Close the connection')
            writer.close()

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


asyncio.run(send_messages("Я снова тестирую чатик. Это третье сообщение."))