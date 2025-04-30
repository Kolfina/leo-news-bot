import logging
from telegram import Update
from telegram.ext import ApplicationBuilder, CommandHandler, ContextTypes

TELEGRAM_TOKEN = '7353034334:AAHIBjJgdMdrqw_nE-DMX9ziM1mzgwG4jkk'

# Логирование
logging.basicConfig(
    filename='bot.log',
    filemode='a',
    format='%(asctime)s - %(levelname)s - %(message)s',
    level=logging.INFO
)

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_chat.id
    username = update.effective_user.username
    logging.info(f"/start от {user_id} (@{username})")
    await update.message.reply_text("Бот работает! ✅")

if __name__ == '__main__':
    app = ApplicationBuilder().token(TELEGRAM_TOKEN).build()
    app.add_handler(CommandHandler("start", start))

    logging.info("Мини-бот запущен")
    print("Мини-бот запущен")
    app.run_polling()
