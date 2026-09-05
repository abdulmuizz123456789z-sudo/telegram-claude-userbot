import os
import glob
import logging
from telethon import TelegramClient, events
import google.generativeai as genai

# ---------------------------------------------------------------------------
# 1. Настройка авторизации Telegram (Userbot) и Gemini
# ---------------------------------------------------------------------------
# Эти данные берутся с сайта my.telegram.org
API_ID = int(os.getenv("TELEGRAM_API_ID", "35518790"))  # Ваш API ID
API_HASH = os.getenv("TELEGRAM_API_HASH", "54d4594451c44d3cfa8252e755dc1c07")  # Ваш API Hash

# Бесплатный ключ Gemini из Google AI Studio
GEMINI_API_KEY = os.getenv("54d4594451c44d3cfa8252e755dc1c07")

genai.configure(api_key=GEMINI_API_KEY)
model = genai.GenerativeModel('gemini-1.5-flash')

# Инициализируем клиент Telethon
client = TelegramClient('userbot_session', API_ID, API_HASH)

logging.basicConfig(level=logging.INFO)

# ---------------------------------------------------------------------------
# 2. Функция чтение всех стандартов станций
# ---------------------------------------------------------------------------
def get_all_standards() -> str:
    """Загружает текст всех регламентов из папки stations/."""
    combined_knowledge = ""
    files = glob.glob("stations/*.txt")
    
    for file_path in files:
        file_name = os.path.basename(file_path)
        try:
            with open(file_path, "r", encoding="utf-8") as f:
                content = f.read().strip()
                combined_knowledge += f"\n\n=== STANSIYA STANDARTI ({file_name}) ===\n{content}"
        except Exception as e:
            logging.error(f"Хатолик: {e}")
            
    return combined_knowledge

# ---------------------------------------------------------------------------
# 3. Обработчик входящих личных сообщений
# ---------------------------------------------------------------------------
@client.on(events.NewMessage(incoming=True, func=lambda e: e.is_private))
async def handle_new_message(event):
    user_text = event.message.text.strip()
    if not user_text:
        return

    # Читаем стандарты станций из папки
    knowledge_base = get_all_standards()

    # Промпт для ИИ
    system_prompt = f"""
Ты — автоматический ИИ-помощник сети ресторанов KFC, встроенный в этот аккаунт.
Твоя задача — давать ИСКЛЮЧИТЕЛЬНО ТОЧНЫЕ и КРАТКИЕ ответы по конкретным деталям, о которых спрашивает сотрудник.

Официальная база знаний (на узбекском языке):
{knowledge_base}

СТРОГИЕ ПРАВИЛА:
1. Выдели ТОЛЬКО ту конкретную деталь или шаг, о котором спросил сотрудник. Не отправляй весь документ целиком!
2. Определи язык вопроса (узбекский, русский, английский и т.д.).
3. База знаний на узбекском. Если вопрос на русском — АВТОМАТИЧЕСКИ ПЕРЕВЕДИ нужную деталь и ответь на русском.
4. Отвечай обычным понятным текстом.
5. Если информации по этой конкретной детали нет в базе, ответь: «К сожалению, у меня нет информации по этой детали в инструкциях / Афсуски, ушбу детал бўйича маълумот йўқ».

Вопрос сотрудника: {user_text}
"""

    try:
        # Показываем статус "печатает..." в чате
        async with client.action(event.chat_id, 'typing'):
            # Запрос к Gemini
            response = model.generate_content(system_prompt)
            answer_text = response.text.strip()
            
            # Отвечаем прямо в чат от имени аккаунта
            await event.reply(answer_text)

    except Exception as e:
        logging.error(f"Gemini/Telethon Error: {e}")

# ---------------------------------------------------------------------------
# 4. Запуск аккаунта
# ---------------------------------------------------------------------------
print("🚀 Telegram Userbot с ИИ Gemini успешно запущен!")
client.start()
client.run_until_disconnected()
