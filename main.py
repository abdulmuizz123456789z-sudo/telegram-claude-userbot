import os
import asyncio
from telethon import TelegramClient, events
from telethon.sessions import StringSession
from openai import OpenAI
from pypdf import PdfReader

API_ID = os.getenv("TELEGRAM_API_ID")
API_HASH = os.getenv("TELEGRAM_API_HASH")
GROQ_API_KEY = os.getenv("GROQ_API_KEY")
SESSION_STRING = os.getenv("SESSION_STRING")

if not API_ID or not API_HASH or not GROQ_API_KEY or not SESSION_STRING:
    raise ValueError("Не заданы обязательные переменные окружения на Railway!")

client_ai = OpenAI(
    api_key=GROQ_API_KEY,
    base_url="https://api.groq.com/openai/v1"
)

STATIONS_DIR = "stations"

def load_full_knowledge():
    """Сканирует 5 станций и возвращает контекст знаний и индекс медиафайлов"""
    knowledge_text = ""
    media_files = []

    if not os.path.exists(STATIONS_DIR):
        return knowledge_text, media_files

    for root, dirs, files in os.walk(STATIONS_DIR):
        for filename in files:
            file_path = os.path.join(root, filename)
            
            # 1. Чтение текстовых регламентов (.txt)
            if filename.endswith(".txt"):
                try:
                    with open(file_path, "r", encoding="utf-8") as f:
                        knowledge_text += f"\n--- Инструкция: {filename} (Путь: {file_path}) ---\n" + f.read()
                except Exception as e:
                    print(f"⚠️ Ошибка чтения TXT {filename}: {e}")

            # 2. Извлечение текста из PDF и индексация документа
            elif filename.endswith(".pdf"):
                media_files.append({"name": filename, "path": file_path, "type": "pdf"})
                try:
                    reader = PdfReader(file_path)
                    pdf_text = ""
                    for page in reader.pages:
                        extracted = page.extract_text()
                        if extracted:
                            pdf_text += extracted + "\n"
                    knowledge_text += f"\n--- PDF Регламент: {filename} ---\n" + pdf_text
                except Exception as e:
                    print(f"⚠️ Ошибка чтения PDF {filename}: {e}")

            # 3. Индексация видеофайлов (.mp4, .mov)
            elif filename.endswith(".mp4") or filename.endswith(".mov"):
                media_files.append({"name": filename, "path": file_path, "type": "video"})

    return knowledge_text, media_files

client = TelegramClient(StringSession(SESSION_STRING), int(API_ID), API_HASH)

def get_active_groq_models():
    """Динамически получает список активных моделей от Groq API"""
    try:
        models_data = client_ai.models.list()
        return [m.id for m in models_data.data if getattr(m, 'active', True)]
    except Exception as e:
        print(f"⚠️ Не удалось получить список моделей через API: {e}")
        return []

@client.on(events.NewMessage(incoming=True))
async def handle_incoming_message(event):
    if not event.is_private:
        return

    user_message = event.raw_text
    print(f"📥 Получено сообщение: {user_message}")

    knowledge_text, media_files = load_full_knowledge()

    if not knowledge_text.strip():
        await event.reply("База знаний пока пуста.")
        return

    system_prompt = f"""Ты — корпоративный помощник и эксперт по стандартам KFC. 
Используй следующую базу знаний (включая стандарты станций: Kitchen, Panera, Service, Lobby, Wash):

{knowledge_text}

Дай четкий, профессиональный и исчерпывающий ответ на основе стандартов KFC."""

    available_models = get_active_groq_models()
    if not available_models:
        await event.reply("Ошибка: Не удалось загрузить доступные модели Groq.")
        return

    response_text = None
    last_error = None

    for model_name in available_models:
        if "whisper" in model_name or "safetensors" in model_name:
            continue
            
        try:
            print(f"🔄 Пробуем модель: {model_name}...")
            response = client_ai.chat.completions.create(
                model=model_name,
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_message}
                ],
                stream=False
            )
            response_text = response.choices[0].message.content
            if response_text:
                print(f"✅ Успешно ответила модель: {model_name}")
                break
        except Exception as e:
            print(f"⚠️ Модель {model_name} не ответила: {e}")
            last_error = e

    # Отправка текстового ответа
    if response_text:
        await event.reply(response_text)
        print("📤 Текстовый ответ отправлен!")
    else:
        print(f"❌ Ошибка ответа ИИ: {last_error}")
        await event.reply("Произошла ошибка при обработке запроса к ИИ.")
        return

    # Поиск и отправка прикрепленных медиафайлов (PDF / Видео)
    keywords = [word.lower() for word in user_message.split() if len(word) > 2]
    
    for media in media_files:
        media_name_lower = media["name"].lower()
        if any(kw in media_name_lower for kw in keywords):
            if os.path.exists(media["path"]):
                try:
                    caption = f"📄 Документ стандарта: {media['name']}" if media["type"] == "pdf" else f"🎥 Видеоурок: {media['name']}"
                    print(f"📤 Отправка файла: {media['path']}")
                    await client.send_file(event.chat_id, media["path"], caption=caption)
                except Exception as e:
                    print(f"⚠️ Ошибка отправки медиафайла {media['name']}: {e}")

async def main_async():
    print("🚀 Telegram Userbot (5-station RAG) успешно запущен!")
    await client.connect()
    if not await client.is_user_authorized():
        raise RuntimeError("Ошибка авторизации: SESSION_STRING недействителен!")
    await client.run_until_disconnected()

def main():
    asyncio.run(main_async())

if __name__ == "__main__":
    main()
