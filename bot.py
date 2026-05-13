import os
import time
import traceback
import telebot
import google.generativeai as genai

# Получаем ключи из среды
TELEGRAM_TOKEN = os.environ.get("TELEGRAM_TOKEN")
GEMINI_KEY = os.environ.get("GEMINI_KEY")

SYSTEM_INSTRUCTION = """
Ты — куратор 3D-марафона «Молот Тора» для детей и подростков. Марафон проходит в Blender (движок Eevee), упор на препродакшн и мудборды.

## ТВОЙ СТИЛЬ
- Журналист-вожатый: общайся на равных, без иерархии и бюрократии.
- Короткие ответы — максимум 3 предложения по существу. Без воды.
- Никогда не начинай ответ с «Отличный вопрос!», «Понимаю», «Конечно!», «Привет!» и других пустых вводных фраз. Сразу — суть.
- Не уговаривай и не убеждай. Если человек не хочет делать фаски — скажи зачем они нужны в одном предложении и дай задачу. Не разворачивай лекцию.
- Форматируй ответ для Telegram Markdown: горячие клавиши — в `backticks`, важные слова — **жирным**. Не используй заголовки (#) и длинные списки.
- В конце каждого ответа — одна конкретная микрозадача: «Попробуй прямо сейчас: ...»
- Если спрашивают не про 3D, не про Blender и не про марафон — мягко возвращай в контекст: «Это не по теме марафона — давай вернёмся к молоту!»
"""

# Инициализация Gemini
genai.configure(api_key=GEMINI_KEY)
gemini_model = genai.GenerativeModel(
    model_name="models/gemini-2.5-flash-lite",
    system_instruction=SYSTEM_INSTRUCTION,
)

user_chats = {}
user_message_counts = {}
MESSAGE_LIMIT = 50

# Инициализация Telegram Бота
bot = telebot.TeleBot(TELEGRAM_TOKEN)

def reset_user(user_id):
    user_chats[user_id] = gemini_model.start_chat(history=[])
    user_message_counts[user_id] = 0

@bot.message_handler(commands=["start"])
def handle_start(message):
    user_id = message.from_user.id
    reset_user(user_id)
    name = message.from_user.first_name or "друг"
    bot.reply_to(
        message,
        f"Привет, {name}! Я куратор марафона «Молот Тора» в Blender. Я теперь еще и голосовые понимаю, так что спрашивай как удобно! 🔨",
        parse_mode="Markdown"
    )

@bot.message_handler(commands=["reset"])
def handle_reset(message):
    user_id = message.from_user.id
    reset_user(user_id)
    bot.reply_to(message, "История очищена. Начинаем с чистого листа!", parse_mode="Markdown")

# Обработка ГОЛОСОВЫХ сообщений
@bot.message_handler(content_types=['voice'])
def handle_voice(message):
    user_id = message.from_user.id
    if user_id not in user_chats:
        reset_user(user_id)

    try:
        # 1. Скачиваем аудио
        file_info = bot.get_file(message.voice.file_id)
        downloaded_file = bot.download_file(file_info.file_path)
        
        file_path = f"voice_{user_id}.ogg"
        with open(file_path, 'wb') as f:
            f.write(downloaded_file)

        # 2. Загружаем и ЖДЕМ обработки
        audio_file = genai.upload_file(path=file_path)
        
        # Цикл ожидания готовности файла
        while audio_file.state.name == "PROCESSING":
            time.sleep(1)
            audio_file = genai.get_file(audio_file.name)
            
        if audio_file.state.name == "FAILED":
            raise Exception("Файл не обработался")

        # 3. Отправляем в Gemini
        chat = user_chats[user_id]
        response = chat.send_message([audio_file, "Слушай внимательно это голосовое. Это вопрос по марафону 3D. Ответь коротко по инструкции."])
        
        bot.reply_to(message, response.text, parse_mode="Markdown")
        
        # 4. Чистим за собой
        os.remove(file_path)
        genai.delete_file(audio_file.name) # Удаляем файл и из облака Google

    except Exception as e:
        traceback.print_exc()
        bot.reply_to(message, "Что-то в микрофоне зашуршало... Не разобрал. Повтори или напиши текстом?")

# Обработка ТЕКСТОВЫХ сообщений
@bot.message_handler(func=lambda message: True)
def handle_message(message):
    user_id = message.from_user.id

    if user_id not in user_chats:
        reset_user(user_id)

    count = user_message_counts.get(user_id, 0)
    if count >= MESSAGE_LIMIT:
        reset_user(user_id)
        count = 0 

    chat = user_chats[user_id]

    try:
        if not message.text:
            return

        response = chat.send_message(message.text)
        user_message_counts[user_id] = count + 1
        bot.reply_to(message, response.text, parse_mode="Markdown")

    except Exception as e:
        traceback.print_exc()
        bot.reply_to(message, "Ошибка на линии! Маякните Сергею Владимировичу.")

if __name__ == "__main__":
    print("Бот запущен и готов слушать голоса...")
    bot.infinity_polling(timeout=10, long_polling_timeout=5)
