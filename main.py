import os
import asyncio
from telethon import TelegramClient, events
from telethon.sessions import StringSession
from openai import OpenAI

API_ID = os.getenv("TELEGRAM_API_ID")
API_HASH = os.getenv("TELEGRAM_API_HASH")
DEEPSEEK_API_KEY = os.getenv("DEEPSEEK_API_KEY")
SESSION_STRING = os.getenv("SESSION_STRING")

if not API_ID or not API_HASH or not DEEPSEEK_API_KEY or not SESSION_STRING:
    raise ValueError("Не заданы обязательные переменные окружения на Railway!")

# Инициализация клиента DeepSeek (через OpenAI SDK с базовым URL DeepSeek)
client_ai = OpenAI(
    api_key=DEEPSEEK_API_KEY,
    base_url="https://api.deepseek.com"
)

# Загрузка базы знаний из папки stations
kfc_knowledge = ""
stations_dir = "stations"
if os.path.exists(stations_dir):
    for filename in os.listdir(stations_dir):
        if filename.endswith(".txt"):
            file_path = os.path.join(stations_dir, filename)
            with open(file_path, "r", encoding="utf-8") as f:
                kfc_knowledge += f"\n--- {filename} ---\n" + f.read()

client = TelegramClient(StringSession(SESSION_STRING), int(API_ID), API_HASH)

@client.on(events.NewMessage(incoming=True))
async def handle_incoming_message(event):
    if not event.is_private:
        return

    user_message = event.raw_text
    print(f"📥 Получено сообщение: {user_message}")

    cleaned_knowledge = kfc_knowledge.strip()

    if not cleaned_knowledge:
        await event.reply("База пустая, информации нет.")
        return

    system_prompt = f"""Ты — корпоративный помощник и эксперт по стандартам ресторанов KFC. 
Используй следующую базу знаний для ответов на вопросы сотрудников:

{cleaned_knowledge}

Дай четкий, профессиональный и точный ответ на основе стандартов KFC."""

    try:
        response = client_ai.chat.completions.create(
            model="deepseek-chat",
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_message}
            ],
            stream=False
        )
        reply_text = response.choices[0].message.content
        if reply_text:
            await event.reply(reply_text)
            print("📤 Ответ успешно отправлен!")
        else:
            await event.reply("Не удалось получить ответ от модели.")
    except Exception as e:
        print(f"❌ Ошибка при обращении к DeepSeek: {e}")
        await event.reply("Произошла ошибка при обработке запроса к ИИ.")

async def main_async():
    print("🚀 Telegram Userbot с ИИ DeepSeek успешно запущен!")
    await client.connect()
    
    if not await client.is_user_authorized():
        raise RuntimeError("Ошибка авторизации: SESSION_STRING недействителен или устарел!")
        
    await client.run_until_disconnected()

def main():
    asyncio.run(main_async())

if __name__ == "__main__":
    main()
