import os
from anthropic import Anthropic
from telethon import TelegramClient, events

# Получаем данные из переменных окружения Railway
API_ID = int(os.environ.get("TELEGRAM_API_ID", 0))
API_HASH = os.environ.get("TELEGRAM_API_HASH")
SESSION_STRING = os.environ.get(
    "TELEGRAM_SESSION_STRING"
)  # Строка сессии для авторизации
ANTHROPIC_API_KEY = os.environ.get("ANTHROPIC_API_KEY")

client = Anthropic(api_key=ANTHROPIC_API_KEY)

# Инициализация Telethon через строку сессии
tg_client = TelegramClient(
    Session(SESSION_STRING) if SESSION_STRING else "anon", API_ID, API_HASH
)


@tg_client.on(events.NewMessage(incoming=True, func=lambda e: e.is_private))
async def handle_incoming_message(event):
  user_message = event.raw_text
  sender = await event.get_sender()

  # Игнорируем ботов и самого себя
  if sender.bot or sender.megagroup:
    return

  try:
    # Запрос к Claude
    response = client.messages.create(
        model="claude-3-5-sonnet-20241022",
        max_tokens=1000,
        system=(
            "Ты действуешь как владелец этого аккаунта в Telegram. Отвечай"
            " вежливо, кратко и по делу от первого лица."
        ),
        messages=[{"role": "user", "content": user_message}],
    )

    reply_text = response.content[0].text
    await event.respond(reply_text)
  except Exception as e:
    print(f"Ошибка при обработке запроса: {e}")


if __name__ == "__main__":
  print("Юзербот запущен...")
  tg_client.start()
  tg_client.run_until_disconnected()
