import os
import asyncio
from telethon import TelegramClient
from telethon.sessions import StringSession

api_id = 35518790
api_hash = "54d4594451c44d3cfa8252e755dc1c07"
session_string = os.environ.get("SESSION_STRING", "")

client = TelegramClient(StringSession(session_string), api_id, api_hash)

async def main():
    async with client:
        print("Юзербот запущен!")
        await client.run_until_disconnected()

asyncio.run(main())
