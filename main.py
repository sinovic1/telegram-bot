import os
import logging
import asyncio
import time
from datetime import datetime
from aiogram import Bot, Dispatcher, types
from aiogram.enums import ParseMode
from aiogram.filters import Command
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from flask import Flask
from threading import Thread

# === ENV VARS ===
API_TOKEN = os.getenv("API_TOKEN")
USER_ID = os.getenv("USER_ID")

if not API_TOKEN or not USER_ID:
    raise ValueError("API_TOKEN or USER_ID is missing in environment variables.")

USER_ID = int(USER_ID)

# === LOGGING ===
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# === BOT ===
bot = Bot(token=API_TOKEN, parse_mode=ParseMode.HTML)
dp = Dispatcher()

# === LOOP WATCHDOG ===
last_loop_time = time.time()

@dp.message(Command("status"))
async def status_handler(message: types.Message):
    if message.from_user.id == USER_ID:
        await message.answer("✅ Bot is running and market is being monitored.")

async def clear_webhook():
    await bot.delete_webhook(drop_pending_updates=True)
    logger.info("✅ Webhook cleared")

async def main_loop():
    global last_loop_time
    while True:
        try:
            logger.info(f"🔄 Checking market at {datetime.now().isoformat()}")
            last_loop_time = time.time()
            await asyncio.sleep(60)
        except Exception as e:
            logger.error(f"❌ Error in loop: {e}")

async def loop_checker():
    if time.time() - last_loop_time > 180:
        await bot.send_message(USER_ID, "⚠️ Bot loop may be stuck!")

# === DUMMY FLASK SERVER FOR KOYEB ===
app = Flask(__name__)

@app.route('/')
def home():
    return "✅ Bot server running (dummy web server for Koyeb)."

def run_flask():
    app.run(host="0.0.0.0", port=8080)

# === MAIN ENTRY ===
async def main():
    await clear_webhook()
    scheduler = AsyncIOScheduler()
    scheduler.add_job(loop_checker, "interval", seconds=60)
    scheduler.start()
    asyncio.create_task(main_loop())
    await dp.start_polling(bot)

if __name__ == "__main__":
    # Start fake web server in background thread
    Thread(target=run_flask).start()
    asyncio.run(main())












