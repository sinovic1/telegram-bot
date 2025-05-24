import logging
import asyncio
import yfinance as yf
import pandas as pd
from aiogram import Bot, Dispatcher, types
from aiogram.types import ParseMode
from aiogram.utils import executor
from aiogram.dispatcher.filters import Command
from aiogram.dispatcher import Dispatcher
from datetime import datetime, timedelta
from flask import Flask
import threading

# ========== CONFIG ==========
TOKEN = "7923000946:AAEx8TZsaIl6GL7XUwPGEM6a6-mBNfKwUz8"
USER_ID = 7469299312
PAIRS = ["EURUSD=X"]
INTERVAL = "5m"
PERIOD = "2d"
CHECK_EVERY_SECONDS = 300
WARNING_THRESHOLD_MINUTES = 10
# ============================

bot = Bot(token=TOKEN, parse_mode=ParseMode.HTML)
dp = Dispatcher(bot)
app = Flask(__name__)
last_activity_time = datetime.utcnow()


def fetch_data(pair):
    df = yf.download(pair, period=PERIOD, interval=INTERVAL)
    if df.empty or "Close" not in df:
        raise ValueError(f"No data for {pair}")

    df["EMA20"] = df["Close"].ewm(span=20, adjust=False).mean()
    delta = df["Close"].diff()
    gain = delta.clip(lower=0)
    loss = -delta.clip(upper=0)
    avg_gain = gain.rolling(14).mean()
    avg_loss = loss.rolling(14).mean()
    rs = avg_gain / avg_loss
    df["RSI"] = 100 - (100 / (1 + rs))
    std = df["Close"].rolling(window=20).std()
    df["UpperBB"] = df["EMA20"] + 2 * std
    df["LowerBB"] = df["EMA20"] - 2 * std

    macd_fast = df["Close"].ewm(span=12, adjust=False).mean()
    macd_slow = df["Close"].ewm(span=26, adjust=False).mean()
    df["MACD"] = macd_fast - macd_slow
    df["Signal"] = df["MACD"].ewm(span=9, adjust=False).mean()

    return df.dropna()


def evaluate_strategies(df):
    last = df.iloc[-1]
    signals = []

    if last["Close"] > last["EMA20"] and last["RSI"] < 30:
        signals.append("RSI & EMA Buy")
    if last["Close"] < last["EMA20"] and last["RSI"] > 70:
        signals.append("RSI & EMA Sell")
    if last["MACD"] > last["Signal"]:
        signals.append("MACD Buy")
    if last["MACD"] < last["Signal"]:
        signals.append("MACD Sell")
    if last["Close"] < last["LowerBB"]:
        signals.append("Bollinger Buy")
    if last["Close"] > last["UpperBB"]:
        signals.append("Bollinger Sell")

    return signals, round(last["Close"], 5)


async def send_signal(pair):
    global last_activity_time
    try:
        df = fetch_data(pair)
        signals, price = evaluate_strategies(df)

        signal_type = None
        if len([s for s in signals if "Buy" in s]) >= 2:
            signal_type = "Buy"
        elif len([s for s in signals if "Sell" in s]) >= 2:
            signal_type = "Sell"

        if signal_type:
            tp1 = round(price + 0.0020, 5) if signal_type == "Buy" else round(price - 0.0020, 5)
            tp2 = round(price + 0.0040, 5) if signal_type == "Buy" else round(price - 0.0040, 5)
            tp3 = round(price + 0.0060, 5) if signal_type == "Buy" else round(price - 0.0060, 5)
            sl = round(price - 0.0020, 5) if signal_type == "Buy" else round(price + 0.0020, 5)
            agreed = len([s for s in signals if signal_type in s])

            msg = (
                f"📊 <b>{pair.replace('=X', '')} Signal</b>\n"
                f"<b>Type:</b> {signal_type}\n"
                f"<b>Entry:</b> {price}\n"
                f"<b>TP1:</b> {tp1}\n"
                f"<b>TP2:</b> {tp2}\n"
                f"<b>TP3:</b> {tp3}\n"
                f"<b>SL:</b> {sl}\n"
                f"<b>Agreed Strategies:</b> {agreed}/4"
            )
            await bot.send_message(chat_id=USER_ID, text=msg)

        last_activity_time = datetime.utcnow()

    except Exception as e:
        logging.error(f"{pair} Error: {e}")


async def check_loop():
    while True:
        for pair in PAIRS:
            await send_signal(pair)
        await asyncio.sleep(CHECK_EVERY_SECONDS)


async def monitor_loop():
    global last_activity_time
    while True:
        if datetime.utcnow() - last_activity_time > timedelta(minutes=WARNING_THRESHOLD_MINUTES):
            await bot.send_message(chat_id=USER_ID, text="⚠️ Warning: Bot seems to be stuck or delayed!")
        await asyncio.sleep(60)


@dp.message_handler(commands=["status"])
async def handle_status(message: types.Message):
    if message.from_user.id == USER_ID:
        await message.answer("✅ Bot is still running and monitoring the market.")


def run_web():
    @app.route("/")
    def home():
        return "Bot is running."
    app.run(host="0.0.0.0", port=8080)


async def main():
    threading.Thread(target=run_web).start()
    asyncio.create_task(check_loop())
    asyncio.create_task(monitor_loop())


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    executor.start_polling(dp, on_startup=main)






