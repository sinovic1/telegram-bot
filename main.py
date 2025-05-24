import os
import logging
import asyncio
from aiogram import Bot, Dispatcher, types
from aiogram.enums import ParseMode
from aiogram.types import Message
from aiogram.client.default import DefaultBotProperties
from aiogram.exceptions import TelegramConflictError
import yfinance as yf
import pandas as pd
from flask import Flask
from threading import Thread

# Setup logging
logging.basicConfig(level=logging.INFO)

# Environment variables
API_TOKEN = os.getenv("API_TOKEN")
USER_ID = int(os.getenv("USER_ID"))

# Bot setup
bot = Bot(token=API_TOKEN, default=DefaultBotProperties(parse_mode=ParseMode.HTML))
dp = Dispatcher()

# Status command
@dp.message(lambda message: message.text == "/status")
async def status_handler(message: Message):
    if message.from_user.id != USER_ID:
        return
    await message.answer("✅ Bot is still running and monitoring the market.")

# Background Flask app to keep instance alive
app = Flask(__name__)
@app.route("/")
def home():
    return "Bot is running!"
def run_flask():
    app.run(host="0.0.0.0", port=8080)

# Example signal-checking logic
async def check_signals():
    while True:
        try:
            ticker = yf.download("EURUSD=X", period="1d", interval="15m")
            if ticker.empty:
                logging.error("EURUSD=X Error: No data")
                await asyncio.sleep(60)
                continue

            # Example basic strategy
            close = ticker["Close"]
            if close.iloc[-1] > close.mean():
                await bot.send_message(USER_ID, "📈 Signal: Buy EUR/USD")
            else:
                await bot.send_message(USER_ID, "📉 Signal: Sell EUR/USD")

        except Exception as e:
            logging.error(f"Error while checking EURUSD=X: {e}")

        await asyncio.sleep(300)

# Main bot loop
async def main():
    try:
        await bot.delete_webhook(drop_pending_updates=True)
        logging.info("✅ Webhook cleared successfully")

        flask_thread = Thread(target=run_flask)
        flask_thread.start()

        signal_task = asyncio.create_task(check_signals())
        await dp.start_polling(bot)
        await signal_task
    except TelegramConflictError:
        logging.error("❌ Another bot instance is running. Stop it before starting a new one.")
    except Exception as e:
        logging.error(f"Unexpected error: {e}")

if __name__ == "__main__":
    asyncio.run(main())











