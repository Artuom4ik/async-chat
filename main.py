import asyncio

async def get_chat_messages():
    reader, writer = await asyncio.open_connection(
        'minechat.dvmn.org', 5000)

    while True:
        message = await reader.readline()
        print(message.decode())

asyncio.run(get_chat_messages())