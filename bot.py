import os
import traceback
import telebot
import google.generativeai as genai

# Ключи
TELEGRAM_TOKEN = os.environ.get("TELEGRAM_TOKEN")
GEMINI_KEY = os.environ.get("GEMINI_KEY")

# ОБЛЕГЧЕННАЯ ИНСТРУКЦИЯ (меньше токенов = меньше ошибок)
SYSTEM_INSTRUCTION = """
Ты — куратор 3D-марафона «Молот Тора» в Blender. Твой стиль: Журналист-вожатый (без воды, коротко, без приветствий).
ОТВЕЧАЙ ТОЛЬКО ПРО: Блокинг, Bevel, Apply Scale (Ctrl A), Extrude, Auto Smooth, Материалы, Рендер Eevee.
ПРАВИЛО: Максимум 3 предложения. В конце — одна микрозадача: «Попробуй прямо сейчас: ...»
Если вопрос не про 3D или марафон — мягко возвращай к молоту.
"""

genai.configure(api_key=GEMINI_KEY)
gemini_model = genai.GenerativeModel(
    model_name="models/gemini-1.5-flash", # Эта модель сейчас самая стабильная
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
    bot.reply_to(message, "🔨 **Кузница готова!** Я максимально облегчил свои мозги, чтобы связь не рвалась. Спрашивай по молоту!")

@bot.message_handler(func=lambda message: True)
def handle_message(message):
    user_id = message.from_user.id
    if user_id not in user_chats: reset_user(user_id)
    chat = user_chats[user_id]

    try:
        # Оставляем в памяти только последние 4 сообщения (самый минимум для стабильности)
        if len(chat.history) > 4:
            chat.history = chat.history[-4:]

        response = chat.send_message(message.text)
        bot.reply_to(message, response.text, parse_mode="Markdown")

    except Exception as e:
        traceback.print_exc()
        reset_user(user_id)
        bot.reply_to(message, "Ошибка связи! Гугл в Амстердаме капризничает. Попробуй еще раз через минуту или напиши короче.")

if __name__ == "__main__":
    bot.infinity_polling(timeout=20, long_polling_timeout=15)
