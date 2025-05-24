import logging
import asyncio
from aiogram import Bot, Dispatcher, types
from aiogram.enums import ParseMode
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.interval import IntervalTrigger
import yfinance as yf
from datetime import datetime
import time

# Hardcoded user ID and token
API_TOKEN = '7923000946:AAHMosNsaHU1Oz-qTihaWlMDYqCV2vhHT1E'
USER_ID = 7469299312

# Enable logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Initialize bot and dispatcher
bot = Bot(token=API_TOKEN, parse_mode=ParseMode.HTML)
dp = Dispatcher()

# Status command handler
@dp.message(lambda message: message.text == "/status")
async def status_handler(message: types.Message):
    if message.from_user.id == USER_ID:
        await message.answer("✅ Bot is running and monitoring the market.")
    else:
        await message.answer("❌ Unauthorized access.")

# Dummy market checking function (you can replace with real logic)
async def check_market():
    now = datetime.utcnow().isoformat()
    logger.info(f"🔄 Checking market at {now}")
    # Simulate logic
    try:
        data = yf.download("EURUSD=X", period="1d", interval="1m")
        if not data.empty:
            logger.info("✅ Market data fetched.")
        else:
            logger.warning("⚠️ Market data is empty.")
    except Exception as e:
        logger.error(f"Error fetching market data: {e}")

# Check if polling is running by sending a message every X minutes
last_check = time.time()

async def loop_checker():
    global last_check
    if time.time() - last_check > 180:  # 3 minutes without activity
        try:
            await bot.send_message(USER_ID, "⚠️ Bot might be stuck or delayed!")
        except Exception as e:
            logger.error(f"Failed to send warning: {e}")
    else:
        logger.info("🟢 Bot is alive.")
    last_check = time.time()

async def main():
    # Clear webhook to avoid conflict
    try:
        await bot.delete_webhook(drop_pending_updates=True)
        logger.info("✅ Webhook cleared")
    except Exception as e:
        logger.warning(f"Failed to clear webhook: {e}")

    # Start polling
    scheduler = AsyncIOScheduler()
    scheduler.add_job(check_market, IntervalTrigger(minutes=1))
    scheduler.add_job(loop_checker, IntervalTrigger(minutes=1))
    scheduler.start()

    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())











