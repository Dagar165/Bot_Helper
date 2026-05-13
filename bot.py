import os
import traceback
import telebot
import google.generativeai as genai

# Твои ключи
TELEGRAM_TOKEN = os.environ.get("TELEGRAM_TOKEN")
GEMINI_KEY = os.environ.get("GEMINI_KEY")

SYSTEM_INSTRUCTION = """
Ты — куратор 3D-марафона «Молот Тора». Марафон в Blender (Eevee).
Твой стиль: Журналист-вожатый. Без иерархии, коротко (3 предложения), без воды.
В конце — всегда одна микрозадача: «Попробуй прямо сейчас: ...»
"""

genai.configure(api_key=GEMINI_KEY)
# Используем 2.5 Flash-Lite, раз она у тебя работала
model = genai.GenerativeModel(
    model_name="models/gemini-2.5-flash-lite",
    system_instruction=SYSTEM_INSTRUCTION
)

user_chats = {}

def get_chat(user_id):
    if user_id not in user_chats:
        user_chats[user_id] = model.start_chat(history=[])
    return user_chats[user_id]

bot = telebot.TeleBot(TELEGRAM_TOKEN)

@bot.message_handler(commands=["start", "reset"])
def handle_start(message):
    user_id = message.from_user.id
    if user_id in user_chats: del user_chats[user_id]
    bot.reply_to(message, "🔨 Память очищена. Давай заново по молоту!")

# ГОЛОС: Слушаем отдельно, в историю чата НЕ КЛАДЕМ
@bot.message_handler(content_types=['voice'])
def handle_voice(message):
    user_id = message.from_user.id
    chat = get_chat(user_id)
    try:
        file_info = bot.get_file(message.voice.file_id)
        downloaded_file = bot.download_file(file_info.file_path)
        
        # Прямая передача байтов (без сохранения в историю)
        audio_payload = {"mime_type": "audio/ogg", "data": downloaded_file}
        
        # Просим модель просто понять суть и ответить
        response = model.generate_content([audio_payload, "Слушай аудио. Это вопрос по 3D марафону. Ответь по инструкции."])
        
        # Добавляем в историю только ТЕКСТОВУЮ пометку, чтобы не раздувать память
        chat.history.append({"role": "user", "parts": ["(Был задан вопрос голосовым сообщением)"]})
        chat.history.append({"role": "model", "parts": [response.text]})
        
        bot.reply_to(message, response.text, parse_mode="Markdown")
    except Exception as e:
        # Если ошибка "429/Limit 0", пишем честно
        if "429" in str(e) or "limit" in str(e).lower():
            bot.reply_to(message, "Гугл временно заблокировал лимиты из-за Амстердама. Подожди 5 минут.")
        else:
            bot.reply_to(message, "Не расслышал. Давай текстом?")

# ТЕКСТ
@bot.message_handler(func=lambda message: True)
def handle_message(message):
    user_id = message.from_user.id
    chat = get_chat(user_id)
    try:
        if not message.text: return
        response = chat.send_message(message.text)
        bot.reply_to(message, response.text, parse_mode="Markdown")
    except Exception as e:
        traceback.print_exc()
        if user_id in user_chats: del user_chats[user_id]
        bot.reply_to(message, "Ошибка на линии! Маякни Сергею Владимировичу или попробуй через 5 минут.")

if __name__ == "__main__":
    bot.infinity_polling(timeout=20, long_polling_timeout=15)
