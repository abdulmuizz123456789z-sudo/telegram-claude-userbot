import os
import asyncio
from telethon import TelegramClient, events
from telethon.sessions import StringSession
from google import genai

# Получаем данные из переменных окружения
api_id = int(os.environ.get("TELEGRAM_API_ID", 0))
api_hash = os.environ.get("TELEGRAM_API_HASH", "")
session_string = os.environ.get("SESSION_STRING", "")
gemini_api_key = os.environ.get("GEMINI_API_KEY", "")

# ВАШ ТЕКСТОВЫЙ ID (замените на ваш числовой ID в Telegram)
MY_TELEGRAM_ID = 7393851495  # или ваш реальный ID владельца

ai_client = genai.Client(api_key=gemini_api_key)
client = TelegramClient(StringSession(session_string), api_id, api_hash)

# Системная инструкция для общения с остальными клиентами
KFC_SYSTEM_PROMPT = (
    "Ты — вежливый виртуальный ассистент службы поддержки KFC. "
    "Помогай клиентам по вопросам меню, работы ресторанов, заказов и доставки. "
    "Отвечай вежливо, профессионально и только по делу."
)

@client.on(events.NewMessage(incoming=True, func=lambda e: e.is_private))
async def handle_incoming_message(event):
    sender = await event.get_sender()
    sender_id = sender.id if sender else 0
    user_message = event.raw_text or ""
    
    try:
        # УСЛОВИЕ 1: Если сообщение от ВАС (владельца)
        if sender_id == MY_TELEGRAM_ID:
            # Здесь можно настроить обработку файлов, PDF и картинок, 
            # которые вы отправляете боту для обучения или загрузки меню.
            if event.media:
                # Скачиваем файл/картинку, которую вы прислали
                path = await event.download_media()
                # Загружаем файл в Gemini для анализа
                uploaded_file = ai_client.files.upload(file=path)
                response = ai_client.models.generate_content(
                    model='gemini-3.6-flash',
                    contents=[uploaded_file, "Проанализируй этот файл/документ и запомни информацию для работы KFC."]
                )
                await event.respond(f"✅ Файл принят и усвоен ассистентом:\n{response.text}")
                return
            
            # Если вы написали текстом — бот может выполнять команды или просто подтверждать
            response = ai_client.models.generate_content(
                model='gemini-3.6-flash',
                contents=f"Ты мой личный помощник. Принято указание: {user_message}",
            )
            await event.respond(response.text)
            return

        # УСЛОВИЕ 2: Если сообщение от ДРУГОГО пользователя (клиента)
        else:
            # Общаемся строго в рамках роли ассистента KFC
            response = ai_client.models.generate_content(
                model='gemini-3.6-flash',
                contents=user_message,
                config=genai.types.GenerateContentConfig(
                    system_instruction=KFC_SYSTEM_PROMPT,
                )
            )
            await event.respond(response.text)

    except Exception as e:
        print(f"Ошибка: {e}")

async def main():
    print("Юзербот-ассистент KFC запущен!")
    await client.start()
    await client.run_until_disconnected()

with client:
    client.loop.run_until_complete(main())
