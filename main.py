import asyncio
import datetime
from contextlib import asynccontextmanager

import aiofiles


async def get_chat_messages():
    async with create_chat_connection('minechat.dvmn.org', 5000) as connection:
        reader, writer = connection

        while not reader.at_eof():
            try:
                message = await reader.readline()

                decode_message = f"{datetime.datetime.now().strftime('[%d.%m.%y %H:%M]')} {message.decode('utf-8').strip()}\n"

                async with aiofiles.open('messages.txt', 'a') as file:
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


asyncio.run(get_chat_messages())