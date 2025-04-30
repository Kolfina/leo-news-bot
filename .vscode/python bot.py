import asyncio
import json
import logging
import os
import requests
from bs4 import BeautifulSoup
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    ApplicationBuilder, ContextTypes, CommandHandler, CallbackQueryHandler
)
from apscheduler.schedulers.asyncio import AsyncIOScheduler
import nest_asyncio

# === НАСТРОЙКИ ===
TELEGRAM_TOKEN = '7353034334:AAHIBjJgdMdrqw_nE-DMX9ziM1mzgwG4jkk'  # ← замени на свой токен
SUBSCRIPTIONS_FILE = 'subscriptions.json'
ADMIN_ID = 6699601390  # ← замени на свой chat_id (временно можно распечатать update.effective_chat.id)

TOPICS = {
    'главное': 'https://lenta.ru/',
    'спорт': 'https://lenta.ru/rubrics/sport',
    'экономика': 'https://lenta.ru/rubrics/economics',
    'наука': 'https://lenta.ru/rubrics/science',
    'технологии': 'https://lenta.ru/rubrics/technology',
}

# === ЛОГИРОВАНИЕ ===
logging.basicConfig(
    filename='bot.log',
    filemode='a',
    format='%(asctime)s - %(levelname)s - %(message)s',
    level=logging.INFO
)

# === РАБОТА С ФАЙЛОМ ===
def load_subscriptions():
    if not os.path.exists(SUBSCRIPTIONS_FILE):
        return {}
    try:
        with open(SUBSCRIPTIONS_FILE, 'r') as f:
            data = json.load(f)
            if isinstance(data, dict):
                return data
            else:
                logging.warning("❗ subscriptions.json не словарь. Заменяю.")
                return {}
    except json.JSONDecodeError:
        logging.warning("❗ subscriptions.json повреждён. Заменяю.")
        return {}

def save_subscriptions(data):
    with open(SUBSCRIPTIONS_FILE, 'w') as f:
        json.dump(data, f, indent=2)

# === ПАРСИНГ НОВОСТЕЙ ===
def get_news_by_topic(topic_url):
    headers = {'User-Agent': 'Mozilla/5.0'}
    response = requests.get(topic_url, headers=headers)
    soup = BeautifulSoup(response.text, 'html.parser')
    news_list = []

    for link in soup.find_all('a', href=True):
        href = link['href']
        if href.startswith('/news') and link.text.strip():
            title = link.text.strip()
            full_url = 'https://lenta.ru' + href
            news_list.append(f'🔹 <a href="{full_url}">{title}</a>')
        if len(news_list) >= 5:
            break

    return '\n'.join(news_list) if news_list else 'Нет новостей по этой теме.'

# === КОМАНДЫ ===
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = str(update.effective_chat.id)
    username = update.effective_user.username or "без_ника"
    data = load_subscriptions()

    if user_id not in data:
        data[user_id] = {"username": username, "topics": []}
        save_subscriptions(data)
        logging.info(f"Новый пользователь: {user_id} (@{username})")
    else:
        if data[user_id].get("username") != username:
            data[user_id]["username"] = username
            save_subscriptions(data)

    await update.message.reply_text(
        "👋 Привет! Я бот новостей Lenta.ru.\n\n"
        "Ты можешь:\n"
        "• подписаться на темы → /topics\n"
        "• посмотреть свои подписки → /mytopics\n"
        "• получить свежие новости → /news"
    )

async def mytopics(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = str(update.effective_chat.id)
    data = load_subscriptions()
    topics = data.get(user_id, {}).get("topics", [])
    if topics:
        await update.message.reply_text("📌 Ты подписан на:\n" + '\n'.join(f"• {t}" for t in topics))
    else:
        await update.message.reply_text("❗Ты ещё не подписан ни на одну тему.\nПопробуй /topics")

async def news(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = str(update.effective_chat.id)
    data = load_subscriptions()
    topics = data.get(user_id, {}).get("topics", [])
    if not topics:
        await update.message.reply_text("❗Ты не подписан ни на одну тему. Используй /topics")
        return

    for topic in topics:
        news = get_news_by_topic(TOPICS[topic])
        await update.message.reply_text(
            f"<b>{topic.upper()}</b>\n{news}",
            parse_mode='HTML',
            disable_web_page_preview=True
        )

async def topics(update: Update, context: ContextTypes.DEFAULT_TYPE):
    keyboard = []
    for topic in TOPICS:
        buttons = [
            InlineKeyboardButton(f"✅ Подписаться: {topic}", callback_data=f"subscribe|{topic}"),
            InlineKeyboardButton(f"❌ Отписаться: {topic}", callback_data=f"unsubscribe|{topic}")
        ]
        keyboard.append(buttons)

    reply_markup = InlineKeyboardMarkup(keyboard)
    await update.message.reply_text("📚 Выберите тему и действие:", reply_markup=reply_markup)

async def handle_button(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    user_id = str(query.from_user.id)
    data = load_subscriptions()
    if user_id not in data:
        data[user_id] = {"username": query.from_user.username or "без_ника", "topics": []}

    action, topic = query.data.split('|')
    if topic not in TOPICS:
        await query.edit_message_text("❗ Ошибка: тема не найдена.")
        return

    if action == "subscribe":
        if topic not in data[user_id]["topics"]:
            data[user_id]["topics"].append(topic)
            save_subscriptions(data)
            logging.info(f"Подписка: {user_id} (@{data[user_id]['username']}) → {topic}")
            await query.edit_message_text(f"✅ Вы подписались на «{topic}»")
        else:
            await query.edit_message_text(f"⚠️ Уже подписаны на «{topic}»")
    elif action == "unsubscribe":
        if topic in data[user_id]["topics"]:
            data[user_id]["topics"].remove(topic)
            save_subscriptions(data)
            logging.info(f"Отписка: {user_id} (@{data[user_id]['username']}) → {topic}")
            await query.edit_message_text(f"❌ Вы отписались от «{topic}»")
        else:
            await query.edit_message_text(f"⚠️ Вы не подписаны на «{topic}»")

async def admin(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_chat.id != ADMIN_ID:
        await update.message.reply_text("🚫 Доступ запрещён.")
        return

    data = load_subscriptions()
    if not data:
        await update.message.reply_text("📭 Нет подписчиков.")
        return

    lines = []
    for uid, info in data.items():
        username = info.get("username", "без_ника")
        topics = ', '.join(info.get("topics", [])) or "—"
        lines.append(f"👤 @{username} ({uid})\n  📌 {topics}")

    await update.message.reply_text('\n\n'.join(lines))

# === РАССЫЛКА ===
async def send_daily_news(app):
    data = load_subscriptions()
    for user_id, info in data.items():
        for topic in info.get("topics", []):
            news = get_news_by_topic(TOPICS[topic])
            try:
                await app.bot.send_message(
                    chat_id=int(user_id),
                    text=f"<b>{topic.upper()}</b>\n{news}",
                    parse_mode='HTML',
                    disable_web_page_preview=True
                )
            except Exception as e:
                logging.warning(f"Ошибка отправки {user_id} (@{info['username']}): {e}")

# === ЗАПУСК ===
if __name__ == '__main__':
    nest_asyncio.apply()
    import asyncio

    app = ApplicationBuilder().token(TELEGRAM_TOKEN).build()

    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("topics", topics))
    app.add_handler(CommandHandler("mytopics", mytopics))
    app.add_handler(CommandHandler("news", news))
    app.add_handler(CommandHandler("admin", admin))
    app.add_handler(CallbackQueryHandler(handle_button))

    scheduler = AsyncIOScheduler(event_loop=asyncio.get_event_loop())
    scheduler.add_job(lambda: asyncio.create_task(send_daily_news(app)), 'cron', hour=9, minute=0)
    scheduler.start()

    logging.info("Бот запущен")
    print("Бот запущен.")
    app.run_polling()
