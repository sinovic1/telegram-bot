import os
import logging
import asyncio
from aiogram import Bot, Dispatcher, types
from aiogram.types import ParseMode
from aiogram.utils import executor
from aiogram.utils.exceptions import TelegramAPIError
from flask import Flask
from threading import Thread
import yfinance as yf

# Enable logging
logging.basicConfig(level=logging.INFO)

# Environment variables
API_TOKEN = os.getenv("API_TOKEN")
USER_ID = int(os.getenv("USER_ID"))

# Bot and dispatcher setup
bot = Bot(token=API_TOKEN, parse_mode=ParseMode.HTML)
dp = Dispatcher(bot)

# Flask app to keep Koyeb instance alive
app = Flask(__name__)
@app.route("/")
def index():
    return "Bot is running!"
def run_flask():
    app.run(host="0.0.0.0", port=8080)

# Status command
@dp.message_handler(commands=['status'])
async def status_handler(message: types.Message):
    if message.from_user.id != USER_ID:
        return
    await message.reply("✅ Bot is still running and monitoring the market.")

# Background task for signals
async def check_signals():
    await bot.delete_webhook(drop_pending_updates=True)
    while True:
        try:
            data = yf.download("EURUSD=X", period="1d", interval="15m")
            if data.empty:
                logging.warning("No data received for EURUSD=X.")
            else:
                last_price = data["Close"].iloc[-1]
                avg_price = data["Close"].mean()
                if last_price > avg_price:
                    await bot.send_message(USER_ID, "📈 Signal: Buy EUR/USD")
                else:
                    await bot.send_message(USER_ID, "📉 Signal: Sell EUR/USD")
        except Exception as e:
            logging.error(f"Error while checking EURUSD=X: {e}")
        await asyncio.sleep(300)

# Start everything
async def on_startup(dp):
    loop = asyncio.get_event_loop()
    loop.create_task(check_signals())
    Thread(target=run_flask).start()

if __name__ == '__main__':
    executor.start_polling(dp, skip_updates=True, on_startup=on_startup)











