import logging
import asyncio
import yfinance as yf
import pandas as pd
from aiogram import Bot, Dispatcher, types
from aiogram.utils import executor
from keep_alive import keep_alive
import os
from datetime import datetime, timedelta

# ========== CONFIG ==========
TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
USER_ID = int(os.getenv("TELEGRAM_USER_ID"))
PAIRS = [("EURUSD=X", "Yggdrag")]
CHECK_INTERVAL = 60  # seconds
WARNING_THRESHOLD = 5  # minutes
# ============================

logging.basicConfig(level=logging.INFO)
bot = Bot(token=TOKEN)
dp = Dispatcher(bot)
last_activity_time = datetime.utcnow()

keep_alive()

def fetch_data(symbol):
    df = yf.download(symbol, period="2d", interval="5m")
    if df.empty or "Close" not in df:
        raise ValueError("No data found.")
    close = df["Close"]
    df["EMA20"] = close.ewm(span=20, adjust=False).mean()
    delta = close.diff()
    gain = delta.clip(lower=0)
    loss = -delta.clip(upper=0)
    rs = gain.rolling(14).mean() / loss.rolling(14).mean()
    df["RSI"] = 100 - (100 / (1 + rs))
    std = close.rolling(20).std()
    df["UpperBB"] = df["EMA20"] + 2 * std
    df["LowerBB"] = df["EMA20"] - 2 * std
    df["MACD"] = close.ewm(span=12).mean() - close.ewm(span=26).mean()
    df["Signal"] = df["MACD"].ewm(span=9).mean()
    df.dropna(inplace=True)
    return df

def analyze(df):
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

async def send_signal(pair_info):
    global last_activity_time
    symbol, name = pair_info
    try:
        df = fetch_data(symbol)
        signals, price = analyze(df)
        buy_signals = [s for s in signals if "Buy" in s]
        sell_signals = [s for s in signals if "Sell" in s]
        signal_type = None
        if len(buy_signals) >= 2:
            signal_type = "Buy"
        elif len(sell_signals) >= 2:
            signal_type = "Sell"
        if signal_type:
            agreed = len(buy_signals if signal_type == "Buy" else sell_signals)
            tp1 = round(price + 0.0020, 5) if signal_type == "Buy" else round(price - 0.0020, 5)
            tp2 = round(price + 0.0040, 5) if signal_type == "Buy" else round(price - 0.0040, 5)
            tp3 = round(price + 0.0060, 5) if signal_type == "Buy" else round(price - 0.0060, 5)
            sl = round(price - 0.0020, 5) if signal_type == "Buy" else round(price + 0.0020, 5)
            message = (
                f"📊 <b>{name} Signal</b>\n"
                f"<b>Type:</b> {signal_type}\n"
                f"<b>Entry:</b> {price}\n"
                f"<b>TP1:</b> {tp1}\n"
                f"<b>TP2:</b> {tp2}\n"
                f"<b>TP3:</b> {tp3}\n"
                f"<b>SL:</b> {sl}\n"
                f"<b>Agreed Strategies:</b> {agreed}/4"
            )
            await bot.send_message(chat_id=USER_ID, text=message, parse_mode="HTML")
        last_activity_time = datetime.utcnow()
    except Exception as e:
        logging.error(f"{symbol} Error: {e}")

async def monitor_loop():
    global last_activity_time
    while True:
        if datetime.utcnow() - last_activity_time > timedelta(minutes=WARNING_THRESHOLD):
            await bot.send_message(chat_id=USER_ID, text=⚠️ Warning: Bot seems to be stuck or delayed!")
        await asyncio.sleep(60)

async def check_loop():
    while True:
        for pair in PAIRS:
            await send_signal(pair)
        await asyncio.sleep(CHECK_INTERVAL)

@dp.message_handler(commands=["status"])
async def status_command(message: types.Message):
    if message.from_user.id == USER_ID:
        await message.answer("✅ Bot is still running and monitoring the market.")

async def on_startup(_):
    asyncio.create_task(check_loop())
    asyncio.create_task(monitor_loop())

if __name__ == "__main__":
    executor.start_polling(dp, on_startup=on_startup)


