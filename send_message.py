import os
import json
import asyncio
import logging
from contextlib import asynccontextmanager

from dotenv import load_dotenv


async def send_messages(message):
    load_dotenv()
    account_hash = os.getenv("ACCOUNT_HASH")

    async with create_chat_connection("minechat.dvmn.org", 5050) as connection:
        try:
            reader, writer = connection

            data = await reader.read(100)

            logging.debug(msg=data.decode(), extra={"type": "sender"})

            writer.write(("287e6fd8-288e-11ef-abed-0242ac11000" + "\n").encode())

            data = await reader.read(100)

            if not json.loads(data.decode().split("\n")[0]):
                logging.debug("Неизвестный токен. Проверьте его или зарегистрируйте заново.", extra={"type": "sender"})

            else:
                logging.debug(msg=data.decode(), extra={"type": "sender"})

                writer.write((message + "\n\n").encode())
                logging.debug(msg=message, extra={"type": "send"})

            logging.debug("Закрытие соединения", extra={"type": "sender"})
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


if __name__ == "__main__":
    logging.basicConfig(
        level=logging.DEBUG,
        format='%(levelname)s:%(type)s:%(message)s',
    )
    asyncio.run(send_messages("Я снова тестирую чатик. Это третье сообщение."))