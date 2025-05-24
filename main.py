import asyncio
import logging
import time
import yfinance as yf
from aiogram import Bot, Dispatcher, types
from aiogram.enums import ParseMode
from aiogram.client.default import DefaultBotProperties
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from flask import Flask
import threading

API_TOKEN = "7923000946:AAGkHu782eQXxhLF4IU1yNCyJO5ruXZhUtc"
ALLOWED_USER_ID = 7469299312

# Setup logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Init bot
bot = Bot(token=API_TOKEN, default=DefaultBotProperties(parse_mode=ParseMode.HTML))
dp = Dispatcher()

# Track last activity time
last_check_time = time.time()

# Flask dummy server to keep port 8080 alive
app = Flask(__name__)
@app.route('/')
def home():
    return "Bot is alive"
def run_web():
    app.run(host="0.0.0.0", port=8080)
threading.Thread(target=run_web).start()

# Trading strategy check
def check_strategy(data):
    close = data["Close"]
    if len(close) < 5:
        return False
    return close[-1] > close[-2] and close[-2] > close[-3]

# Loop checker
async def loop_checker():
    global last_check_time
    try:
        logger.info(f"🔄 Checking market at {time.strftime('%Y-%m-%dT%H:%M:%S')}")
        symbol = "EURUSD=X"
        data = yf.download(symbol, period="7d", interval="1h")
        if data.empty:
            raise ValueError("No data fetched")
        if check_strategy(data):
            await bot.send_message(ALLOWED_USER_ID, f"📈 Signal detected for <b>{symbol}</b>")
        last_check_time = time.time()
    except Exception as e:
        logger.error(f"Error while checking {symbol}: {e}")

# /status command
@dp.message(lambda message: message.text == "/status" and message.from_user.id == ALLOWED_USER_ID)
async def status_handler(message: types.Message):
    delay = time.time() - last_check_time
    status = "✅ Everything is working fine." if delay < 120 else "⚠️ Warning: Loop may be frozen!"
    await message.answer(status)

# Start bot
async def main():
    await bot.delete_webhook(drop_pending_updates=True)
    logger.info("✅ Webhook cleared")

    scheduler = AsyncIOScheduler()
    scheduler.add_job(loop_checker, "interval", minutes=1)
    scheduler.start()

    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())
















