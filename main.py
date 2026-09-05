import os
import asyncio
from telethon import TelegramClient, events
from telethon.sessions import StringSession
import google.generativeai as genai

# Загрузка переменных окружения
API_ID = os.getenv("TELEGRAM_API_ID")
API_HASH = os.getenv("TELEGRAM_API_HASH")
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")
SESSION_STRING = os.getenv("SESSION_STRING")

# Проверка наличия обязательных ключей
if not API_ID or not API_HASH or not GEMINI_API_KEY or not SESSION_STRING:
    raise ValueError("Не заданы обязательные переменные окружения на Railway!")

# Инициализация Gemini
genai.configure(api_key=GEMINI_API_KEY)
generation_config = {
    "temperature": 0.3,
    "max_output_tokens": 800,
}
model = genai.GenerativeModel(
    model_name="gemini-1.5-flash",
    generation_config=generation_config
)

# Загрузка базы знаний из папки stations, если она есть
kfc_knowledge = ""
stations_dir = "stations"
if os.path.exists(stations_dir):
    for filename in os.listdir(stations_dir):
        if filename.endswith(".txt"):
            file_path = os.path.join(stations_dir, filename)
            with open(file_path, "r", encoding="utf-8") as f:
                kfc_knowledge += f"\n--- {filename} ---\n" + f.read()

# Инициализация клиента Telethon через StringSession для Railway
client = TelegramClient(StringSession(SESSION_STRING), int(API_ID), API_HASH)

@client.on(events.NewMessage(incoming=True))
async def handle_incoming_message(event):
    # Отвечаем только в личных сообщениях
    if not event.is_private:
        return

    user_message = event.raw_text
    
    # Формируем промпт для Gemini с учетом базы знаний
    prompt = f"""
Ты — корпоративный помощник и эксперт по стандартам ресторанов KFC. 
Используй следующую базу знаний для ответов на вопросы сотрудников:

{kfc_knowledge}

Вопрос сотрудника: {user_message}
Дай четкий, профессиональный и точный ответ на основе стандартов KFC. Если информации нет в базе, отвечай опираясь на общие регламенты сети.
"""

    try:
        response = model.generate_content(prompt)
        reply_text = response.text
        await event.reply(reply_text)
    except Exception as e:
        print(f"Ошибка при обращении к Gemini: {e}")

async def main_async():
    print("🚀 Telegram Userbot с ИИ Gemini успешно запущен!")
    await client.connect()
    
    if not await client.is_user_authorized():
        raise RuntimeError("Ошибка авторизации: SESSION_STRING недействителен или устарел!")
        
    await client.run_until_disconnected()

def main():
    asyncio.run(main_async())

if __name__ == "__main__":
    main()
    
