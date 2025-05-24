import logging
import asyncio
from datetime import datetime
import yfinance as yf
from aiogram import Bot, Dispatcher, types
from aiogram.enums import ParseMode
from aiogram.fsm.storage.memory import MemoryStorage
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.interval import IntervalTrigger
from flask import Flask
from threading import Thread

API_TOKEN = "7923000946:AAGkHu782eQXxhLF4IU1yNCyJO5ruXZhUtc"
ALLOWED_USER_ID = 7469299312  # Hassan's Telegram ID

logging.basicConfig(level=logging.INFO)

app = Flask(__name__)

@app.route("/")
def home():
    return "✅ Bot is running", 200

bot = Bot(token=API_TOKEN, parse_mode=ParseMode.HTML)
dp = Dispatcher(storage=MemoryStorage())
scheduler = AsyncIOScheduler()

# Simple status command
@dp.message(lambda msg: msg.text == "/status" and msg.from_user.id == ALLOWED_USER_ID)
async def status_handler(message: types.Message):
    await message.answer("✅ Bot is running fine!")

# Your trading logic here
def check_strategies():
    pair = "EURUSD=X"
    try:
        logging.info(f"🔄 Checking market at {datetime.utcnow().isoformat()}")
        df = yf.download(pair, period="1d", interval="1m")
        if df.empty:
            raise ValueError("Empty data")
        # Placeholder: Replace with real strategy logic
        print("✅ Market checked successfully.")
    except Exception as e:
        logging.error(f"Error while checking {pair}: {e}")

def loop_checker():
    asyncio.run(check_strategies())

scheduler.add_job(loop_checker, IntervalTrigger(minutes=1))

async def start_bot():
    scheduler.start()
    await bot.delete_webhook(drop_pending_updates=True)
    await dp.start_polling(bot)

def start_flask():
    app.run(host="0.0.0.0", port=8080)

if __name__ == "__main__":
    flask_thread = Thread(target=start_flask)
    flask_thread.start()
    asyncio.run(start_bot())

















