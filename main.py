import os
import logging
import asyncio
import time
from datetime import datetime
from aiogram import Bot, Dispatcher, types
from aiogram.enums import ParseMode
from aiogram.filters import Command
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from aiogram.exceptions import TelegramAPIError

# Load environment variables
API_TOKEN = os.getenv("API_TOKEN")
USER_ID = os.getenv("USER_ID")

if not API_TOKEN or not USER_ID:
    raise ValueError("API_TOKEN or USER_ID is missing in environment variables.")

USER_ID = int(USER_ID)

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Initialize bot and dispatcher
bot = Bot(token=API_TOKEN, parse_mode=ParseMode.HTML)
dp = Dispatcher()

# Store the last loop time to detect if the bot stops
last_loop_time = time.time()


# Clear any existing webhook (to avoid conflict)
async def clear_webhook():
    await bot.delete_webhook(drop_pending_updates=True)
    logger.info("✅ Webhook cleared")


# Status command handler
@dp.message(Command("status"))
async def status_handler(message: types.Message):
    if message.from_user.id != USER_ID:
        return
    await message.answer("✅ Bot is working and monitoring the market.")


# Example placeholder task (your trading logic goes here)
async def main_loop():
    global last_loop_time
    while True:
        try:
            logger.info("🔄 Checking market at %s", datetime.now().isoformat())
            last_loop_time = time.time()
            await asyncio.sleep(60)  # Run every minute
        except Exception as e:
            logger.error("❌ Error in main loop: %s", e)


# Watchdog job to monitor if main loop is frozen
async def loop_checker():
    global last_loop_time
    if time.time() - last_loop_time > 180:  # 3 minutes
        try:
            await bot.send_message(USER_ID, "⚠️ Bot may be stuck or delayed. Please check it.")
        except TelegramAPIError as e:
            logger.error("❌ Failed to send warning: %s", e)


async def main():
    await clear_webhook()
    scheduler = AsyncIOScheduler()
    scheduler.add_job(loop_checker, "interval", seconds=60)
    scheduler.start()
    asyncio.create_task(main_loop())
    await dp.start_polling(bot)


if __name__ == "__main__":
    asyncio.run(main())












