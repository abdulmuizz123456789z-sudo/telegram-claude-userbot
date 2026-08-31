import os
import asyncio
from telethon import TelegramClient, events
from telethon.sessions import StringSession
from google import genai

# Загружаем данные из переменных окружения Railway
api_id = int(os.environ.get("TELEGRAM_API_ID", 0))
api_hash = os.environ.get("TELEGRAM_API_HASH", "")
session_string = os.environ.get("SESSION_STRING", "")
gemini_api_key = os.environ.get("GEMINI_API_KEY", "")

# Инициализируем Gemini и Telegram
ai_client = genai.Client(api_key=gemini_api_key)
client = TelegramClient(StringSession(session_string), api_id, api_hash)

@client.on(events.NewMessage(incoming=True, func=lambda e: e.is_private))
async def handle_incoming_message(event):
    user_message = event.raw_text
    try:
        # Запрос к бесплатной модели Gemini Flash
        response = ai_client.models.generate_content(
            model='gemini-3.6-flash',
            contents=user_message,
        )
        await event.respond(response.text)
    except Exception as e:
        print(f"Ошибка: {e}")

async def main():
    print("Юзербот запущен!")
    await client.start()
    await client.run_until_disconnected()

with client:
    client.loop.run_until_complete(main())
