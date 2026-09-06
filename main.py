import os
import sys
from pathlib import Path
from telethon import TelegramClient, events
from groq import Groq

# ------------------------------------------------------------------------------
# 1. ПРОВЕРКА ПЕРЕМЕННЫХ ОКРУЖЕНИЯ И ИНИЦИАЛИЗАЦИЯ
# ------------------------------------------------------------------------------
API_ID = os.environ.get("API_ID")
API_HASH = os.environ.get("API_HASH")
SESSION_STRING = os.environ.get("SESSION_STRING")
GROQ_API_KEY = os.environ.get("GROQ_API_KEY")

if not all([API_ID, API_HASH, SESSION_STRING, GROQ_API_KEY]):
    print("❌ Ошибка: Не все переменные окружения (API_ID, API_HASH, SESSION_STRING, GROQ_API_KEY) заданы!")
    sys.exit(1)

# Преобразование API_ID в int
try:
    API_ID = int(API_ID)
except ValueError:
    print("❌ Ошибка: API_ID должен быть числом!")
    sys.exit(1)

# Инициализация клиентов
from telethon.sessions import StringSession

client = TelegramClient(StringSession(SESSION_STRING), API_ID, API_HASH)
groq_client = Groq(api_key=GROQ_API_KEY)

# ------------------------------------------------------------------------------
# 2. СИСТЕМНЫЙ ПРОМПТ И КАРТА МЕДИАФАЙЛОВ СТАНЦИЙ
# ------------------------------------------------------------------------------
SYSTEM_PROMPT = """
Ты — эксперт по стандартам KFC. Твоя задача — давать точные, вежливые и профессиональные ответы
по правилам приготовления, технике безопасности, стандартам станций и санитарным нормам KFC.
Отвечай структурированно, четко и по делу.
"""

# Путь к директории с медиафайлами станций
BASE_DIR = Path(__file__).parent
STATIONS_DIR = BASE_DIR / "stations"

# Карта ключевых слов к файлам станций
MEDIA_MAP = {
    "панировка": STATIONS_DIR / "panirovka.pdf",
    "жарка": STATIONS_DIR / "frikasse.pdf",
    "касса": STATIONS_DIR / "kassa.pdf",
    "упаковка": STATIONS_DIR / "upakovka.pdf",
    "санитария": STATIONS_DIR / "sanitariya.pdf",
}

# Приоритетный список моделей Groq для резервного переключения (fallback)
GROQ_MODELS = [
    "llama-3.3-70b-versatile",
    "llama-3.1-8b-instant",
    "mixtral-8x7b-32768",
    "gemma2-9b-it"
]

# ------------------------------------------------------------------------------
# 3. ОБРАБОТКА СООБЩЕНИЙ TELEGRAM
# ------------------------------------------------------------------------------
@client.on(events.NewMessage(incoming=True))
async def handle_message(event):
    if not event.text or event.is_group:
        return

    user_text = event.text.strip().lower()

    # Поиск соответствующего медиафайла
    matched_file = None
    for key, file_path in MEDIA_MAP.items():
        if key in user_text or any(word in user_text for word in key.split("_")):
            matched_file = file_path
            break

    bot_answer = None

    # Поочередная попытка вызова моделей Groq
    for model_name in GROQ_MODELS:
        try:
            response = groq_client.chat.completions.create(
                model=model_name,
                messages=[
                    {"role": "system", "content": SYSTEM_PROMPT},
                    {"role": "user", "content": event.text}
                ],
                temperature=0.3,
                max_tokens=1000
            )
            bot_answer = response.choices[0].message.content
            print(f"✅ Успешный ответ от модели: {model_name}")
            break
        except Exception as e:
            print(f"⚠️ Ошибка при вызове модели {model_name}: {e}")
            continue

    try:
        if bot_answer:
            # Отправка текстового ответа
            await event.reply(bot_answer)

            # Отправка файла станции, если найден релевантный
            if matched_file and matched_file.exists():
                await event.reply(file=matched_file)
        else:
            await event.reply("⚠️ Ни одна из моделей LLM недоступна в данный момент. Попробуйте позже.")

    except Exception as e:
        print(f"❌ Ошибка отправки сообщения в Telegram: {e}")

# ------------------------------------------------------------------------------
# 4. ЗАПУСК КЛИЕНТА TELETHON
# ------------------------------------------------------------------------------
async def main_async():
    print("🚀 Юзербот успешно запущен и готов к работе...")
    await client.start()
    await client.run_until_disconnected()

if __name__ == "__main__":
    import asyncio
    asyncio.run(main_async())
