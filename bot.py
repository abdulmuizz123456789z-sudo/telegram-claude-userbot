import os
import glob
import logging
from telegram import Update
from telegram.constants import ChatAction, ParseMode
from telegram.ext import (
    ApplicationBuilder,
    CommandHandler,
    MessageHandler,
    ContextTypes,
    filters,
)
import google.generativeai as genai

# ---------------------------------------------------------------------------
# 1. Настройки и Логирование
# ---------------------------------------------------------------------------
logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    level=logging.INFO
)

TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")

# Инициализация Gemini API
genai.configure(api_key=GEMINI_API_KEY)
model = genai.GenerativeModel('gemini-1.5-flash')


# ---------------------------------------------------------------------------
# 2. Вспомогательная функция загрузки стандартов
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
            logging.error(f"Файл {file_path} оқишда хатолик: {e}")
            
    return combined_knowledge


# ---------------------------------------------------------------------------
# 3. Системные команды (/start, /help)
# ---------------------------------------------------------------------------
async def start_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    welcome_text = (
        "👋 **Assalomu alaykum! / Здравствуйте!**\n\n"
        "Men KFC filiallaridagi stansiyalar (Кухня, Панировка, Обслуживание, Мойка, Зал) "
        "bo'yicha aqlli yordamchiman.\n\n"
        "💡 **Har qanday savolingizni bering** (O'zbek, Русский, English):\n"
        "— *Moyka stansiyasida dezinfeksiya qanday qilinadi?*\n"
        "— *Как часто нужно менять раствор на мойке?*"
    )
    await update.message.reply_text(welcome_text, parse_mode=ParseMode.MARKDOWN)


# ---------------------------------------------------------------------------
# 4. Обработчик вопросов сотрудников (Основной ИИ-модуль)
# ---------------------------------------------------------------------------
async def handle_user_query(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_text = update.message.text.strip()
    if not user_text:
        return

    # Индикатор "печатает..." в Telegram
    await context.bot.send_chat_action(
        chat_id=update.effective_chat.id, 
        action=ChatAction.TYPING
    )

    # Читаем свежие стандарты из файлов
    knowledge_base = get_all_standards()

    # Системные правила для ИИ
    system_prompt = f"""
Ты — профессиональный ИИ-ассистент и инструктор сети ресторанов KFC.
Твоя задача — давать ИСКЛЮЧИТЕЛЬНО ТОЧНЫЕ и КРАТКИЕ ответы по конкретным деталям, о которых спрашивает сотрудник.

Официальная база знаний (написана на узбекском языке):
{knowledge_base}

СТРОГИЕ ПРАВИЛА ИНСТРУКЦИИ:
1. **Точность детали:** Не отправляй весь документ целиком! Выдели ТОЛЬКО ту конкретную деталь, процедуру или шаг, о котором спросил сотрудник.
2. **Мультиязычность:**
   - Определи язык, на котором был задан вопрос сотрудником (узбекский, русский, английский и др.).
   - База знаний составлена на узбекском языке. Если вопрос задан на русском или английском, АВТОМАТИЧЕСКИ ПЕРЕВЕДИ найденную конкретную информацию и ответь на языке вопроса.
3. **Форматирование:** Используй списки, жирный текст и четкие шаги. Ответ должен быть легким для чтения на экране смартфона.
4. **Отсутствие галлюцинаций:** Если в базе знаний нет ответа на данный конкретный вопрос, вежливо ответь на языке пользователя, что информация по этой детали отсутствует в инструкциях.

Вопрос сотрудника: {user_text}
"""

    try:
        # Запрос к Gemini
        response = model.generate_content(system_prompt)
        answer_text = response.text.strip()

        # Отправка ответа
        await update.message.reply_text(answer_text, parse_mode=ParseMode.MARKDOWN)

    except Exception as e:
        logging.error(f"Gemini API Error: {e}")
        await update.message.reply_text(
            "⚠️ Xatolik yuz berdi. Tizim администраторига мурожаат қилинг.\n"
            "⚠️ Произошла ошибка при обработке запроса."
        )


# ---------------------------------------------------------------------------
# 5. Запуск Telegram бота
# ---------------------------------------------------------------------------
def main():
    if not TELEGRAM_BOT_TOKEN or not GEMINI_API_KEY:
        print("ОШИБКА: Проверьте переменные окружения TELEGRAM_BOT_TOKEN и GEMINI_API_KEY!")
        return

    app = ApplicationBuilder().token(TELEGRAM_BOT_TOKEN).build()

    # Регистрация хэндлеров
    app.add_handler(CommandHandler("start", start_command))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_user_query))

    print("🤖 KFC AI-Assistant успешно запущен и готов к работе...")
    app.run_polling()


if __name__ == '__main__':
    main()
