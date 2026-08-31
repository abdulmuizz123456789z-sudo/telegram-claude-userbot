import os
import asyncio
from telethon import TelegramClient, events
from telethon.sessions import StringSession
from google import genai
from gtts import gTTS

# Загружаем настройки из окружения
api_id = int(os.environ.get("TELEGRAM_API_ID", 0))
api_hash = os.environ.get("TELEGRAM_API_HASH", "")
session_string = os.environ.get("SESSION_STRING", "")
gemini_api_key = os.environ.get("GEMINI_API_KEY", "")

# Ваш числовой Telegram ID владельца
MY_TELEGRAM_ID = 7393851495  # <-- Убедитесь, что здесь ваш реальный ID

ai_client = genai.Client(api_key=gemini_api_key)
client = TelegramClient(StringSession(session_string), api_id, api_hash)

# Глобальная база знаний (файлы и текст)
uploaded_knowledge_files = []

KFC_SYSTEM_PROMPT = (
    "Ты — вежливый виртуальный ассистент службы поддержки KFC. "
    "Используй загруженные администратором файлы и инструкции "
    "для точных ответов клиентам по вопросам меню, работы ресторанов, заказов и доставки. "
    "Отвечай вежливо, профессионально и строго на основе предоставленной базы знаний. "
    "Старайся отвечать относительно кратко, так как ответ будет озвучен голосом."
)

@client.on(events.NewMessage(incoming=True, func=lambda e: e.is_private))
async def handle_incoming_message(event):
    sender = await event.get_sender()
    sender_id = sender.id if sender else 0
    user_message = event.raw_text or ""
    
    try:
        # 1. ЕСЛИ СООБЩЕНИЕ ОТ ВАС (Администратора)
        if sender_id == MY_TELEGRAM_ID:
            # Обработка медиа (картинки, PDF, а также ваши ГОЛОСОВЫЕ сообщения)
            if event.media:
                path = await event.download_media()
                
                # Если вы прислали голосовое сообщение
                if event.voice or event.audio:
                    uploaded_file = ai_client.files.upload(file=path)
                    response = ai_client.models.generate_content(
                        model='gemini-3.6-flash',
                        contents=[uploaded_file, "Прослушай это голосовое сообщение и переведи его в текстовую инструкцию/правило для работы ассистента KFC."]
                    )
                    uploaded_knowledge_files.append(response.text)
                    await event.respond(f"✅ Голосовое успешно расшифровано и добавлено в базу знаний!\n\n**Текст:** {response.text}")
                    return
                
                # Если обычный файл или картинка
                file_ref = ai_client.files.upload(file=path)
                uploaded_knowledge_files.append(file_ref)
                await event.respond(f"✅ Файл добавлен в базу знаний KFC! Всего элементов в базе: {len(uploaded_knowledge_files)}")
                return
            
            # Текстовая команда от вас
            if user_message:
                uploaded_knowledge_files.append(fИнструкция от админа: {user_message}")
                await event.respond(f"✅ Текстовая инструкция сохранена в базу знаний. Всего элементов: {len(uploaded_knowledge_files)}")
                return
            return

        # 2. ЕСЛИ СООБЩЕНИЕ ОТ КЛИЕНТА (Отвечаем голосом)
        else:
            # Собираем всю базу знаний + вопрос клиента
            contents = list(uploaded_knowledge_files) + [f"Вопрос клиента: {user_message}"]
            
            # Получаем текстовый ответ от Gemini
            ai_response = ai_client.models.generate_content(
                model='gemini-3.6-flash',
                contents=contents,
                config=genai.types.GenerateContentConfig(
                    system_instruction=KFC_SYSTEM_PROMPT,
                )
            )
            reply_text = ai_response.text

            # Превращаем текст ответа в голосовое сообщение (.ogg)
            voice_path = "response_voice.ogg"
            tts = gTTS(text=reply_text, lang='ru', slow=False)
            tts.save(voice_path)

            # Отправляем клиенту голосовое сообщение
            await client.send_file(
                event.chat_id,
                voice_path,
                voice_note=True, # Отправляет как круглое/голосовое в Telegram
                caption=None
            )
            
            # Удаляем временный файл с диска
            if os.path.exists(voice_path):
                os.remove(voice_path)

    except Exception as e:
        print(f"Ошибка: {e}")
        await event.respond("Извините, возникла техническая ошибка при обработке.")

async def main():
    print("Юзербот-ассистент KFC (с поддержкой голосовых) запущен!")
    await client.start()
    await client.run_until_disconnected()

with client:
    client.loop.run_until_complete(main())
