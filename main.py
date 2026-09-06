import os
import asyncio
from telethon import TelegramClient, events
from telethon.sessions import StringSession
from openai import OpenAI
from pypdf import PdfReader

# 1. Проверка и получение переменных окружения из Railway
API_ID = os.getenv("TELEGRAM_API_ID")
API_HASH = os.getenv("TELEGRAM_API_HASH")
GROQ_API_KEY = os.getenv("GROQ_API_KEY")
SESSION_STRING = os.getenv("SESSION_STRING")

if not API_ID or not API_HASH or not GROQ_API_KEY or not SESSION_STRING:
    raise ValueError("⚠️ Не заданы обязательные переменные окружения на Railway (TELEGRAM_API_ID, TELEGRAM_API_HASH, GROQ_API_KEY, SESSION_STRING)!")

# 2. Инициализация клиента Groq API (через OpenAI SDK)
client_ai = OpenAI(
    api_key=GROQ_API_KEY,
    base_url="https://api.groq.com/openai/v1"
)

STATIONS_DIR = "stations"

def load_full_knowledge():
    """
    Рекурсивно сканирует директорию stations (все 5 станций: kitchen, panera, service, lobby, wash).
    Собирает текстовые данные из .txt и .pdf для ИИ, а также индексирует PDF и медиафайлы для отправки.
    """
    knowledge_text = ""
    media_files = []

    if not os.path.exists(STATIONS_DIR):
        return knowledge_text, media_files

    for root, dirs, files in os.walk(STATIONS_DIR):
        for filename in files:
            file_path = os.path.join(root, filename)
            
            # 1. Обработка текстовых файлов (.txt)
            if filename.endswith(".txt"):
                try:
                    with open(file_path, "r", encoding="utf-8") as f:
                        knowledge_text += f"\n--- Инструкция ({filename}): {file_path} ---\n" + f.read()
                except Exception as e:
                    print(f"⚠️ Ошибка чтения TXT {filename}: {e}")

            # 2. Извлечение текста из PDF и сохранение ссылки на файл для отправки
            elif filename.endswith(".pdf"):
                media_files.append({"name": filename, "path": file_path, "type": "pdf"})
                try:
                    reader = PdfReader(file_path)
                    pdf_text = ""
                    for page in reader.pages:
                        extracted = page.extract_text()
                        if extracted:
                            pdf_text += extracted + "\n"
                    knowledge_text += f"\n--- PDF Стандарт ({filename}): {file_path} ---\n" + pdf_text
                except Exception as e:
                    print(f"⚠️ Ошибка чтения PDF {filename}: {e}")

            # 3. Сохранение ссылок на видеофайлы (.mp4, .mov)
            elif filename.endswith(".mp4") or filename.endswith(".mov"):
                media_files.append({"name": filename, "path": file_path, "type": "video"})

    return knowledge_text, media_files

# 3. Инициализация клиента Telethon из StringSession
client = TelegramClient(StringSession(SESSION_STRING), int(API_ID), API_HASH)

def get_active_groq_models():
    """Динамически запрашивает у Groq список активных доступных моделей"""
    try:
        models_data = client_ai.models.list()
        return [m.id for m in models_data.data if getattr(m, 'active', True)]
    except Exception as e:
        print(f"⚠️ Не удалось получить список моделей через API Groq: {e}")
        return []

@client.on(events.NewMessage(incoming=True))
async def handle_incoming_message(event):
    # Работаем только в личных сообщениях
    if not event.is_private:
        return

    user_message = event.raw_text
    print(f"📥 Получено сообщение от пользователя: {user_message}")

    knowledge_text, media_files = load_full_knowledge()

    if not knowledge_text.strip():
        await event.reply("База знаний пока пуста. Загрузите стандарты в папку stations.")
        return

    system_prompt = f"""Ты — эксперт и корпоративный помощник ресторана KFC.
Твоя задача — дать максимально точный, исчерпывающий и подробный ответ по стандартам KFC на основе предоставленной базы знаний.

База знаний (включает 5 станций: Kitchen, Panera, Service, Lobby, Wash):
{knowledge_text}

Отвечай вежливо, структурированно и профессионально."""

    available_models = get_active_groq_models()
    if not available_models:
        await event.reply("Ошибка: Не удалось найти активные модели Groq.")
        return

    response_text = None
    last_error = None

    # Перебор доступных моделей
    for model_name in available_models:
        if "whisper" in model_name or "safetensors" in model_name:
            continue
            
        try:
            print(f"🔄 Обращение к модели: {model_name}...")
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
                print(f"✅ Успешный ответ от модели: {model_name}")
                break
        except Exception as e:
            print(f"⚠️ Ошибка вызова модели {model_name}: {e}")
            last_error = e

    # 1. Отправляем текстовый ответ ИИ
    if response_text:
        await event.reply(response_text)
        print("📤 Текстовый ответ успешно отправлен!")
    else:
        print(f"❌ Ошибка получения ответа от Groq API: {last_error}")
        await event.reply("Произошла ошибка при обращении к ИИ.")
        return

    # 2. Поиск и отправка релевантных PDF-документов и Видеофайлов
    keywords = [word.lower() for word in user_message.split() if len(word) > 2]
    
    for media in media_files:
        media_name_lower = media["name"].lower()
        # Проверяем, есть ли хотя бы одно ключевое слово из запроса в названии файла
        if any(kw in media_name_lower for kw in keywords):
            if os.path.exists(media["path"]):
                try:
                    caption = (
                        f"📄 Документ стандарта: {media['name']}"
                        if media["type"] == "pdf"
                        else f"🎥 Видеоурок: {media['name']}"
                    )
                    print(f"📤 Отправка файла пользователю: {media['path']}")
                    await client.send_file(event.chat_id, media["path"], caption=caption)
                except Exception as e:
                    print(f"⚠️ Ошибка отправки файла {media['name']}: {e}")

async def main_async():
    print("🚀 Telegram Userbot (5-station RAG + File Delivery) успешно запущен!")
    await client.connect()
    if not await client.is_user_authorized():
        raise RuntimeError("Ошибка авторизации: SESSION_STRING недействителен или аннулирован!")
    await client.run_until_disconnected()

def main():
    asyncio.run(main_async())

if __name__ == "__main__":
    main()
