import os
import traceback
import telebot
import google.generativeai as genai

# Ключи
TELEGRAM_TOKEN = os.environ.get("TELEGRAM_TOKEN")
GEMINI_KEY = os.environ.get("GEMINI_KEY")

# Сверхлегкая инструкция (чтобы не пробивать лимиты в Амстердаме)
SYSTEM_INSTRUCTION = """
Ты — куратор 3D-марафона «Молот Тора». Стиль: Журналист-вожатый (коротко, без воды, без приветствий).
Темы: Блокинг, Bevel, Apply Scale, Extrude, Auto Smooth, Материалы, Рендер.
Правило: Ответ до 3 предложений. В конце одна микрозадача: «Попробуй прямо сейчас: ...»
"""

genai.configure(api_key=GEMINI_KEY)
# Возвращаем проверенную 2.5-flash-lite
gemini_model = genai.GenerativeModel(
    model_name="models/gemini-2.5-flash-lite",
    system_instruction=SYSTEM_INSTRUCTION,
)

user_chats = {}

def reset_user(user_id):
    user_chats[user_id] = gemini_model.start_chat(history=[])

bot = telebot.TeleBot(TELEGRAM_TOKEN)

@bot.message_handler(commands=["start", "reset"])
def handle_reset(message):
    user_id = message.from_user.id
    reset_user(user_id)
    bot.reply_to(message, "🔨 **Кузница в строю!** Память очистил. Давай по делу.")

@bot.message_handler(func=lambda message: True)
def handle_message(message):
    user_id = message.from_user.id
    if user_id not in user_chats: reset_user(user_id)
    chat = user_chats[user_id]

    try:
        # Держим в истории только 4 сообщения (самый минимум)
        if len(chat.history) > 4:
            chat.history = chat.history[-4:]

        response = chat.send_message(message.text)
        bot.reply_to(message, response.text, parse_mode="Markdown")

    except Exception as e:
        traceback.print_exc()
        reset_user(user_id)
        bot.reply_to(message, "⚠️ Ошибка лимитов Google. Подожди минуту и напиши снова.")

if __name__ == "__main__":
    bot.infinity_polling(timeout=15, long_polling_timeout=10)
