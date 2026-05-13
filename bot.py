import os
import traceback
import telebot
import google.generativeai as genai
from google.api_core.exceptions import ResourceExhausted

TELEGRAM_TOKEN = os.environ.get("TELEGRAM_TOKEN")
GEMINI_KEY = os.environ.get("GEMINI_KEY")

SYSTEM_INSTRUCTION = """
Ты — куратор 3D-марафона «Молот Тора». Стиль: Журналист-вожатый (коротко, без воды, без приветствий).
Темы: Блокинг, Bevel, Apply Scale, Extrude, Auto Smooth, Материалы, Рендер.
Правило: Ответ до 3 предложений. В конце одна микрозадача: «Попробуй прямо сейчас: ...»
"""

genai.configure(api_key=GEMINI_KEY)
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
    reset_user(message.from_user.id)
    bot.reply_to(message, "🔨 **Кузница в строю!** Память очистил. Давай по делу.")

# 1. ЖЕСТКИЙ ФИЛЬТР: Отсекаем всё, кроме текста. Экономим токены и нервы.
@bot.message_handler(content_types=['voice', 'audio', 'video', 'video_note', 'photo', 'document', 'sticker'])
def handle_media(message):
    bot.reply_to(message, "Слушать и смотреть некогда. Пиши текстом, если хочешь получить аппрув по задаче.")

# 2. Обработка только текста
@bot.message_handler(content_types=['text'])
def handle_message(message):
    user_id = message.from_user.id
    if user_id not in user_chats:
        reset_user(user_id)
    
    chat = user_chats[user_id]

    # Безопасная обрезка: проверяем длину и сбрасываем, если перебор,
    # чтобы не нарушить чередование User/Model
    if len(chat.history) >= 6: 
        # Сохраняем последнее сообщение юзера и сбрасываем сессию, 
        # чтобы бот не забыл текущий вопрос при очистке
        reset_user(user_id)
        chat = user_chats[user_id]

    try:
        response = chat.send_message(message.text)
        bot.reply_to(message, response.text, parse_mode="Markdown")

    except ResourceExhausted:
        # Конкретный перехват 429 ошибки
        bot.reply_to(message, "⚠️ Сервер перегружен. Делаем вдох-выдох и повторяем запрос через 15 секунд.")
    except Exception as e:
        traceback.print_exc()
        bot.reply_to(message, "⚠️ Техническая заминка. Повтори позже или пиши Диме с Максом.")
        reset_user(user_id)

if __name__ == "__main__":
    bot.infinity_polling(timeout=15, long_polling_timeout=10)
