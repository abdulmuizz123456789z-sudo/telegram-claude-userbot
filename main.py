import os
import re
from pathlib import Path
from telethon import TelegramClient, events
from telethon.sessions import StringSession
from groq import Groq

# ------------------------------------------------------------------------------
# 1. КОНФИГУРАЦИЯ И ПЕРЕМЕННЫЕ ОКРУЖЕНИЯ
# ------------------------------------------------------------------------------
API_ID = os.getenv("API_ID")
API_HASH = os.getenv("API_HASH")
SESSION_STRING = os.getenv("SESSION_STRING")
GROQ_API_KEY = os.getenv("GROQ_API_KEY")

if not all([API_ID, API_HASH, SESSION_STRING, GROQ_API_KEY]):
    raise ValueError("❌ Ошибка: Не все переменные окружения (API_ID, API_HASH, SESSION_STRING, GROQ_API_KEY) заданы!")

# Очистка SESSION_STRING от возможных кавычек и пробелов
CLEAN_SESSION = SESSION_STRING.strip().strip('"').strip("'")

# Инициализация клиентов
groq_client = Groq(api_key=GROQ_API_KEY)
client = TelegramClient(StringSession(CLEAN_SESSION), int(API_ID), API_HASH)

BASE_DIR = Path(__file__).parent / "stations"

# ------------------------------------------------------------------------------
# 2. RAG & МЕДИА БАЗА (5 СТАНЦИЙ KFC)
# ------------------------------------------------------------------------------
def get_station_context_and_files():
    """Сканирует директорию stations/ и собирает текст и медиафайлы."""
    context_text = ""
    media_files = {}

    if not BASE_DIR.exists():
        return context_text, media_files

    for station_folder in sorted(BASE_DIR.iterdir()):
        if station_folder.is_dir():
            station_name = station_folder.name
            
            # Чтение текстовых стандартов
            text_dir = station_folder / "text"
            if text_dir.exists():
                for txt_file in text_dir.glob("*.txt"):
                    try:
                        content = txt_file.read_text(encoding="utf-8")
                        context_text += f"\n--- СТАНЦИЯ: {station_name} ({txt_file.name}) ---\n{content}\n"
                    except Exception:
                        pass

            # Индексация PDF и Video
            for media_type in ["pdf", "video"]:
                media_dir = station_folder / media_type
                if media_dir.exists():
                    for file in media_dir.iterdir():
                        if file.is_file() and not file.name.startswith("."):
                            key = file.stem.lower()
                            media_files[key] = file

    return context_text, media_files

KNOWLEDGE_BASE, MEDIA_MAP = get_station_context_and_files()

SYSTEM_PROMPT = f"""
Ты — эксперт и инструктор по стандартам KFC. Твоя задача — давать точные, чёткие и профессиональные ответы сотрудникам на основе регламентов.

База знаний станций:
{KNOWLEDGE_BASE}

Инструкции:
1. Отвечай строго по существу стандарта.
2. Если пользователь просит регламент, схему или видеоинструкцию, отвечай кратко и упоминай название файла.
"""

# ------------------------------------------------------------------------------
# 3. ОБРАБОТКА СООБЩЕНИЙ TELEGRAM
# ------------------------------------------------------------------------------
@client.on(events.NewMessage(incoming=True))
async def handle_message(event):
    if not event.text or event.is_group:
        return

    user_text = event.text.strip().lower()

    # Поиск соответствующего медиафайла (PDF/Video)
    matched_file = None
    for key, file_path in MEDIA_MAP.items():
        if key in user_text or any(word in user_text for word in key.split("_")):
            matched_file = file_path
            break

    try:
        # Генерация ответа через Groq API
        response = groq_client.chat.completions.create(
            model="llama-3.3-70b-versatile",
            messages=[
                {"role": "system", "content": SYSTEM_PROMPT},
                {"role": "user", "content": event.text}
            ],
            temperature=0.3,
            max_tokens=1000
        )
        bot_answer = response.choices[0].message.content

        # Отправка текстового ответа
        await event.reply(bot_answer)

        # Отправка файла, если найден релевантный
        if matched_file and matched_file.exists():
            await event.reply(file=matched_file)

    except Exception as e:
        await event.reply("⚠️ Произошла ошибка при обработке запроса. Попробуйте позже.")

# ------------------------------------------------------------------------------
# 4. ТОЧКА ВХОДА И ЗАПУСК
# ------------------------------------------------------------------------------
async def main_async():
    # client.start() автоматически выполняет подключение и авторизацию по сессии
    await client.start()
    await client.run_until_disconnected()

if __name__ == "__main__":
    import asyncio
    asyncio.run(main_async())
