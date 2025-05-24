import asyncio
import logging
import pandas as pd
import yfinance as yf
from aiogram import Bot, Dispatcher, types
from aiogram.enums import ParseMode
from flask import Flask
import threading
import time
import os

API_TOKEN = os.getenv("BOT_TOKEN")
USER_ID = int(os.getenv("USER_ID"))

bot = Bot(token=API_TOKEN, parse_mode=ParseMode.HTML)
dp = Dispatcher()

app = Flask(__name__)

# Health check route
@app.route('/')
def index():
    return 'Bot is running!'

def run_flask():
    app.run(host='0.0.0.0', port=8080)

# Start Flask server in another thread
threading.Thread(target=run_flask).start()

# Initialize timestamp to check if bot is stuck
last_signal_time = time.time()

def update_last_signal_time():
    global last_signal_time
    last_signal_time = time.time()

async def send_warning_if_stuck():
    while True:
        await asyncio.sleep(300)  # Check every 5 minutes
        if time.time() - last_signal_time > 360:
            try:
                await bot.send_message(chat_id=USER_ID, text="⚠️ Warning: Bot seems to be stuck or delayed!")
            except Exception as e:
                logging.error(f"Failed to send stuck warning: {e}")

# Signal logic here
def analyze_signal(symbol):
    try:
        df = yf.download(symbol, period='1d', interval='5m')
        if df.empty:
            raise ValueError("No data received")

        # Bollinger Bands
        df["MiddleBB"] = df["Close"].rolling(window=20).mean()
        df["UpperBB"] = df["MiddleBB"] + 2 * df["Close"].rolling(window=20).std()
        df["LowerBB"] = df["MiddleBB"] - 2 * df["Close"].rolling(window=20).std()

        last_close = df["Close"].iloc[-1]
        upper = df["UpperBB"].iloc[-1]
        lower = df["LowerBB"].iloc[-1]

        signal = None
        if last_close < lower:
            signal = "🔵 BUY signal!"
        elif last_close > upper:
            signal = "🔴 SELL signal!"

        if signal:
            update_last_signal_time()
            return f"📈 <b>{symbol}</b>\n{signal}\nPrice: {last_close:.5f}"
    except Exception as e:
        logging.error(f"{symbol} Error: {e}")
    return None

@dp.message()
async def handle_message(message: types.Message):
    if message.chat.id != USER_ID:
        return
    if message.text.lower() == "/status":
        await message.reply("✅ Bot is running and monitoring the market.")

async def check_market_loop():
    pairs = ["EURUSD=X"]
    while True:
        for symbol in pairs:
            signal = analyze_signal(symbol)
            if signal:
                try:
                    await bot.send_message(chat_id=USER_ID, text=signal)
                except Exception as e:
                    logging.error(f"Failed to send message: {e}")
        await asyncio.sleep(300)

async def main():
    logging.basicConfig(level=logging.INFO)
    asyncio.create_task(send_warning_if_stuck())
    asyncio.create_task(check_market_loop())
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())







