import asyncio
import logging
from aiogram import Bot, Dispatcher, F
from aiogram.enums import ParseMode
from aiogram.types import Message
from aiogram.client.default import DefaultBotProperties
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.interval import IntervalTrigger
import yfinance as yf
from flask import Flask
import threading

API_TOKEN = "7923000946:AAGkHu782eQXxhLF4IU1yNCyJO5ruXZhUtc"
AUTHORIZED_USER_ID = 7469299312  # Your Telegram user ID

# Logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Bot setup
bot = Bot(token=API_TOKEN, default=DefaultBotProperties(parse_mode=ParseMode.HTML))
dp = Dispatcher()

# Flask app for UptimeRobot ping
app = Flask(__name__)

@app.route('/')
def home():
    return "✅ Bot is alive"

def run_flask():
    app.run(host="0.0.0.0", port=8080)

# Status command
@dp.message(F.text == "/status")
async def status_handler(message: Message):
    if message.from_user.id == AUTHORIZED_USER_ID:
        await message.answer("✅ Bot is running and healthy.")
    else:
        await message.answer("⛔ Unauthorized.")

# Strategy checking (simplified placeholder)
async def check_strategies():
    logger.info("🔄 Checking market...")
    try:
        data = yf.download("EURUSD=X", period="1d", interval="1m")
        if data.empty:
            logger.error("No data received.")
            return
        # Implement your signal logic here
        logger.info("✅ Market checked successfully.")
    except Exception as e:
        logger.error(f"Error while checking EURUSD=X: {e}")

# APScheduler setup
scheduler = AsyncIOScheduler()

async def loop_checker():
    await check_strategies()

async def start_bot():
    scheduler.add_job(lambda: asyncio.create_task(loop_checker()), trigger=IntervalTrigger(minutes=1))
    scheduler.start()
    logger.info("✅ Scheduler started.")
    await dp.start_polling(bot)

if __name__ == "__main__":
    threading.Thread(target=run_flask).start()
    asyncio.run(start_bot())


















