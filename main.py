import logging
import asyncio
from aiogram import Bot, Dispatcher, types
from aiogram.enums import ParseMode
from aiogram.types import Message
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from datetime import datetime
import yfinance as yf
import os

# 🔐 Forced bot token
API_TOKEN = "7923000946:AAGkHu782eQXxhLF4IU1yNCyJO5ruXZhUtc"

# Only allow this Telegram user ID to interact
ALLOWED_USER_ID = 7469299312

# 📊 Strategy functions
def get_signals(data):
    signals = []

    # EMA Strategy
    data["EMA20"] = data["Close"].ewm(span=20, adjust=False).mean()
    ema_signal = "buy" if data["Close"].iloc[-1] > data["EMA20"].iloc[-1] else "sell"

    # RSI Strategy
    delta = data["Close"].diff()
    gain = delta.clip(lower=0)
    loss = -delta.clip(upper=0)
    avg_gain = gain.rolling(window=14).mean()
    avg_loss = loss.rolling(window=14).mean()
    rs = avg_gain / avg_loss
    data["RSI"] = 100 - (100 / (1 + rs))
    rsi_signal = "buy" if data["RSI"].iloc[-1] < 30 else "sell" if data["RSI"].iloc[-1] > 70 else "hold"

    # MACD
    exp1 = data["Close"].ewm(span=12, adjust=False).mean()
    exp2 = data["Close"].ewm(span=26, adjust=False).mean()
    macd = exp1 - exp2
    signal = macd.ewm(span=9, adjust=False).mean()
    macd_signal = "buy" if macd.iloc[-1] > signal.iloc[-1] else "sell"

    # Bollinger Bands
    data["SMA20"] = data["Close"].rolling(window=20).mean()
    data["Upper"] = data["SMA20"] + 2 * data["Close"].rolling(window=20).std()
    data["Lower"] = data["SMA20"] - 2 * data["Close"].rolling(window=20).std()
    boll_signal = "buy" if data["Close"].iloc[-1] < data["Lower"].iloc[-1] else "sell" if data["Close"].iloc[-1] > data["Upper"].iloc[-1] else "hold"

    for sig in [ema_signal, rsi_signal, macd_signal, boll_signal]:
        if sig in ["buy", "sell"]:
            signals.append(sig)

    if signals.count("buy") >= 2:
        return "BUY"
    elif signals.count("sell") >= 2:
        return "SELL"
    else:
        return None

# 📤 Send signal to Telegram
async def send_signal(bot, action, price):
    tp1 = round(price * (1.01 if action == "BUY" else 0.99), 5)
    tp2 = round(price * (1.02 if action == "BUY" else 0.98), 5)
    tp3 = round(price * (1.03 if action == "BUY" else 0.97), 5)
    sl = round(price * (0.99 if action == "BUY" else 1.01), 5)

    msg = (
        f"📈 <b>Signal:</b> <code>{action}</code>\n"
        f"💰 <b>Entry:</b> {price:.5f}\n"
        f"🎯 <b>TP1:</b> {tp1}\n"
        f"🎯 <b>TP2:</b> {tp2}\n"
        f"🎯 <b>TP3:</b> {tp3}\n"
        f"⛔ <b>SL:</b> {sl}"
    )
    await bot.send_message(ALLOWED_USER_ID, msg, parse_mode=ParseMode.HTML)

# 🔄 Periodic loop
async def loop_checker():
    try:
        now = datetime.utcnow().isoformat()
        print(f"🔄 Checking market at {now}")

        data = yf.download("EURUSD=X", period="30m", interval="1m", progress=False, auto_adjust=True)
        if data.empty:
            return

        signal = get_signals(data)
        if signal:
            await send_signal(bot, signal, data["Close"].iloc[-1])
    except Exception as e:
        logging.error(f"Error while checking EURUSD=X: {e}")

# ✅ /status command
async def status_handler(message: Message):
    if message.from_user.id != ALLOWED_USER_ID:
        return
    await message.answer("✅ Bot is running and checking signals!")

# 🧠 Setup
logging.basicConfig(level=logging.INFO)
bot = Bot(token=API_TOKEN, parse_mode=ParseMode.HTML)
dp = Dispatcher()

dp.message.register(status_handler, commands={"status"})

scheduler = AsyncIOScheduler()
scheduler.add_job(loop_checker, "interval", minutes=1)
scheduler.start()

# 🚀 Start polling
async def main():
    print("✅ Webhook cleared")
    await bot.delete_webhook(drop_pending_updates=True)
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())














