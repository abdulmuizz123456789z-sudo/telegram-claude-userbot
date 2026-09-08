import os
import sys
from pathlib import Path
from telethon import TelegramClient, events
from telethon.sessions import StringSession
from groq import Groq

# ------------------------------------------------------------------------------
# 1. ОБЪЯВЛЕНИЕ ПУТЕЙ К ФАЙЛАМ (СТРОГО В САМОМ НАЧАЛЕ)
# ------------------------------------------------------------------------------
BASE_DIR = Path(__file__).resolve().parent
STATIONS_DIR = BASE_DIR / "stations"

# ------------------------------------------------------------------------------
# 2. ПРОВЕРКА ПЕРЕМЕННЫХ ОКРУЖЕНИЯ И ИНИЦИАЛИЗАЦИЯ
# ------------------------------------------------------------------------------
API_ID = os.environ.get("API_ID")
API_HASH = os.environ.get("API_HASH")
SESSION_STRING = os.environ.get("SESSION_STRING")
GROQ_API_KEY = os.environ.get("GROQ_API_KEY")

if not all([API_ID, API_HASH, SESSION_STRING, GROQ_API_KEY]):
    print("❌ Ошибка: Не все переменные окружения (API_ID, API_HASH, SESSION_STRING, GROQ_API_KEY) заданы!")
    sys.exit(1)

try:
    API_ID = int(API_ID)
except ValueError:
    print("❌ Ошибка: API_ID должен быть числом!")
    sys.exit(1)

# Инициализация клиентов
client = TelegramClient(StringSession(SESSION_STRING.strip()), API_ID, API_HASH)
groq_client = Groq(api_key=GROQ_API_KEY.strip())

# ------------------------------------------------------------------------------
# 3. СИСТЕМНЫЙ ПРОМПТ И КАРТА МЕДИАФАЙЛОВ
# ------------------------------------------------------------------------------
SYSTEM_PROMPT = """
Ты — эксперт по стандартам KFC. У тебя есть доступ к PDF-инструкциям и регламентам станций:
1. Панировка (panirovka.pdf)
2. Жарка / Фрикассе (frikasse.pdf)
3. Касса (kassa.pdf)
4. Упаковка (upakovka.pdf)
5. Санитария (sanitariya.pdf)

Если пользователь спрашивает про наличие PDF-файлов или стандартов, подтверждай, что материалы по этим 5 станциям есть в системе и будут автоматически отправлены вместе с ответом при запросе конкретной станции. Отвечай вежливо, четко и по делу.
"""

MEDIA_MAP = {
    "панировка": STATIONS_DIR / "panirovka.pdf",
    "панировки": STATIONS_DIR / "panirovka.pdf",
    "жарка": STATIONS_DIR / "frikasse.pdf",
    "жарки": STATIONS_DIR / "frikasse.pdf",
    "фрикассе": STATIONS_DIR / "frikasse.pdf",
    "касса": STATIONS_DIR / "kassa.pdf",
    "кассы": STATIONS_DIR / "kassa.pdf",
    "упаковка": STATIONS_DIR / "upakovka.pdf",
    "упаковки": STATIONS_DIR / "upakovka.pdf",
    "санитария": STATIONS_DIR / "sanitariya.pdf",
    "санитарии": STATIONS_DIR / "sanitariya.pdf",
    "чистка": STATIONS_DIR / "sanitariya.pdf",
}

FALLBACK_MODELS = [
    "llama-3.3-70b-versatile",
    "llama-3.1-8b-instant"
]

def get_active_groq_models():
    """Динамический запрос активных моделей Groq"""
    try:
        models_data = groq_client.models.list()
        active_models = [m.id for m in models_data.data if getattr(m, 'active', True)]
        chat_models = [m for m in active_models if not any(x in m for x in ['whisper', 'guard', 'prompt-guard'])]
        if chat_models:
            return chat_models
    except Exception as e:
        print(f"⚠️ Не удалось загрузить список моделей через API: {e}")
    
    return FALLBACK_MODELS

# ------------------------------------------------------------------------------
# 4. ОБРАБОТКА СООБЩЕНИЙ TELEGRAM
# ------------------------------------------------------------------------------
@client.on(events.NewMessage(incoming=True))
async def handle_message(event):
    if not event.text or event.is_group:
        return

    user_text = event.text.strip().lower()

    # Поиск соответствующего медиафайла
    matched_file = None
    for key, file_path in MEDIA_MAP.items():
        if key in user_text:
            matched_file = file_path
            break

    bot_answer = None
    last_error = None

    available_models = get_active_groq_models()

    for model_name in available_models:
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
            last_error = str(e)
            print(f"⚠️ Ошибка при вызове модели {model_name}: {e}")
            continue

    try:
        if bot_answer:
            await event.reply(bot_answer)
            if matched_file and matched_file.exists():
                await event.reply(file=matched_file)
        else:
            await event.reply(f"⚠️ Ошибка Groq API:\n`{last_error}`")

    except Exception as e:
        print(f"❌ Ошибка отправки сообщения в Telegram: {e}")

# ------------------------------------------------------------------------------
# 5. ЗАПУСК КЛИЕНТА TELETHON
# ------------------------------------------------------------------------------
async def main_async():
    print("🚀 Юзербот успешно запущен и готов к работе...")
    await client.start()
    await client.run_until_disconnected()

if __name__ == "__main__":
    import asyncio
    asyncio.run(main_async())
