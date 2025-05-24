import logging
import asyncio
import yfinance as yf
import pandas as pd
from aiogram import Bot, Dispatcher, types
from aiogram.enums import ParseMode
from aiogram.client.default import DefaultBotProperties
from aiogram.filters import Command
from aiogram.types import Message
from datetime import datetime, timedelta
from flask import Flask

# ========== CONFIG ==========
TOKEN = "7923000946:AAEx8TZsaIl6GL7XUwPGEM6a6-mBNfKwUz8"
USER_ID = 7469299312
PAIRS = ["EURUSD=X"]
INTERVAL = "5m"
PERIOD = "2d"
CHECK_INTERVAL = 300
WARNING_AFTER = 10
# ============================

bot = Bot(token=TOKEN, default=DefaultBotProperties(parse_mode=ParseMode.HTML))
dp = Dispatcher()
last_ping = datetime.utcnow()

app = Flask(__name__)

@app.route("/")
def home():
    return "Bot is running!"

def fetch_data(pair):
    data = yf.download(pair, period=PERIOD, interval=INTERVAL, progress=False)
    if data.empty:
        raise Exception("No data")
    close = data["Close"]
    data["EMA20"] = close.ewm(span=20).mean()
    delta = close.diff()
    gain = delta.clip(lower=0)
    loss = -delta.clip(upper=0)
    avg_gain = gain.rolling(14).mean()
    avg_loss = loss.rolling(14).mean()
    rs = avg_gain / avg_loss
    data["RSI"] = 100 - (100 / (1 + rs))
    std = close.rolling(window=20).std()
    data["UpperBB"] = data["EMA20"] + 2 * std
    data["LowerBB"] = data["EMA20"] - 2 * std
    macd_fast = close.ewm(span=12).mean()
    macd_slow = close.ewm(span=26).mean()
    data["MACD"] = macd_fast - macd_slow
    data["Signal"] = data["MACD"].ewm(span=9).mean()
    data.dropna(inplace=True)
    return data

def evaluate(df):
    last = df.iloc[-1]
    signals = []
    if last["Close"] > last["EMA20"] and last["RSI"] < 30:
        signals.append("RSI+EMA Buy")
    if last["Close"] < last["EMA20"] and last["RSI"] > 70:
        signals.append("RSI+EMA Sell")
    if last["MACD"] > last["Signal"]:
        signals.append("MACD Buy")
    if last["MACD"] < last["Signal"]:
        signals.append("MACD Sell")
    if last["Close"] < last["LowerBB"]:
        signals.append("Bollinger Buy")
    if last["Close"] > last["UpperBB"]:
        signals.append("Bollinger Sell")
    return signals, round(last["Close"], 5)

async def send_alert(pair):
    global last_ping
    try:
        df = fetch_data(pair)
        signals, price = evaluate(df)
        buy_signals = [s for s in signals if "Buy" in s]
        sell_signals = [s for s in signals if "Sell" in s]
        signal_type = None
        if len(buy_signals) >= 2:
            signal_type = "Buy"
        elif len(sell_signals) >= 2:
            signal_type = "Sell"
        if signal_type:
            tp1 = round(price + 0.0020, 5) if signal_type == "Buy" else round(price - 0.0020, 5)
            tp2 = round(price + 0.0040, 5) if signal_type == "Buy" else round(price - 0.0040, 5)
            tp3 = round(price + 0.0060, 5) if signal_type == "Buy" else round(price - 0.0060, 5)
            sl = round(price - 0.0020, 5) if signal_type == "Buy" else round(price + 0.0020, 5)
            text = (
                f"📊 <b>{pair.replace('=X', '')} Signal</b>\n"
                f"<b>Type:</b> {signal_type}\n"
                f"<b>Entry:</b> {price}\n"
                f"<b>TP1:</b> {tp1}\n"
                f"<b>TP2:</b> {tp2}\n"
                f"<b>TP3:</b> {tp3}\n"
                f"<b>SL:</b> {sl}\n"
                f"<b>Agreed Strategies:</b> {len(signals)}"
            )
            await bot.send_message(USER_ID, text)
        last_ping = datetime.utcnow()
    except Exception as e:
        logging.error(f"{pair} Error: {e}")

async def check_loop():
    while True:
        for pair in PAIRS:
            await send_alert(pair)
        await asyncio.sleep(CHECK_INTERVAL)

async def warning_loop():
    global last_ping
    while True:
        if datetime.utcnow() - last_ping > timedelta(minutes=WARNING_AFTER):
            await bot.send_message(USER_ID, "⚠ Warning: Bot seems stuck or delayed.")
        await asyncio.sleep(60)

@dp.message(Command("status"))
async def status_handler(message: Message):
    if message.from_user.id == USER_ID:
        await message.answer("✅ Bot is still running and monitoring the market.")

async def main():
    asyncio.create_task(check_loop())
    asyncio.create_task(warning_loop())
    while True:
        await asyncio.sleep(3600)

if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    asyncio.run(dp.start_polling(bot, startup=main))





