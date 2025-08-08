import os
import logging
import nest_asyncio
nest_asyncio.apply()

from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    ApplicationBuilder,
    CommandHandler,
    CallbackQueryHandler,
    ContextTypes,
)
import requests
from datetime import time

# Логирование
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s', level=logging.INFO
)
logger = logging.getLogger(__name__)

TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
if not TOKEN:
    logger.error("Переменная окружения TELEGRAM_BOT_TOKEN не установлена!")
    raise ValueError("Не найден TELEGRAM_BOT_TOKEN в переменных окружения")

logger.info("Токен бота успешно загружен.")


def get_quote():
    url = "https://zenquotes.io/api/random"
    try:
        response = requests.get(url, timeout=5)
        response.raise_for_status()
        data = response.json()
        if data and isinstance(data, list):
            quote = data[0].get("q")
            author = data[0].get("a")
            return f"\"{quote}\"\n— {author}"
        else:
            return "Не удалось получить цитату."
    except Exception as e:
        logger.error(f"Ошибка при получении цитаты: {e}")
        return "Не удалось получить цитату."


async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    keyboard = [
        [InlineKeyboardButton("Цитата дня", callback_data="quote_day")]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    await update.message.reply_text(
        "Привет! Я мотивационный бот.\n"
        "Я буду отправлять тебе мотивационные цитаты утром, днем и вечером.\n"
        "Нажми кнопку ниже, чтобы получить цитату дня.",
        reply_markup=reply_markup,
    )


async def button_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()

    if query.data == "quote_day":
        quote = get_quote()
        await query.edit_message_text(text=quote)


async def send_quote(context: ContextTypes.DEFAULT_TYPE):
    chat_id = context.job.chat_id
    quote = get_quote()
    await context.bot.send_message(chat_id=chat_id, text=quote)


async def subscribe(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat_id = update.effective_chat.id

    # Удаляем старые задания для этого чата
    for job in context.job_queue.get_jobs_by_name(str(chat_id)):
        job.schedule_removal()

    # Добавляем расписание (UTC время, при необходимости скорректируйте согласно часовому поясу)
    context.job_queue.run_daily(send_quote, time=time(7, 0), chat_id=chat_id, name=str(chat_id) + "_morning")
    context.job_queue.run_daily(send_quote, time=time(13, 0), chat_id=chat_id, name=str(chat_id) + "_afternoon")
    context.job_queue.run_daily(send_quote, time=time(19, 0), chat_id=chat_id, name=str(chat_id) + "_evening")

    await update.message.reply_text("Вы успешно подписались на мотивационные цитаты утром, днем и вечером.")


async def main():
    try:
        app = ApplicationBuilder().token(TOKEN).build()
        app.add_handler(CommandHandler("start", start))
        app.add_handler(CommandHandler("subscribe", subscribe))
        app.add_handler(CallbackQueryHandler(button_handler))
        logger.info("Запускаю бота...")
        await app.run_polling()
    except Exception as e:
        logger.error(f"Ошибка при запуске бота: {e}")


if __name__ == "__main__":
    import asyncio

    try:
        asyncio.get_event_loop().run_until_complete(main())
    except RuntimeError as e:
        if "already running" in str(e):
            # В некоторых окружениях (например, Jupyter или Render) loop уже запущен
            asyncio.run(main())
        else:
            raise
