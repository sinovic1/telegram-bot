import os
import logging
import asyncio
from aiogram import Bot, Dispatcher, types
from aiogram.enums import ParseMode
from aiogram.fsm.storage.memory import MemoryStorage
from aiogram.client.default import DefaultBotProperties
from apscheduler.schedulers.asyncio import AsyncIOScheduler
import yfinance as yf
from flask import Flask
from threading import Thread

# ====== CONFIG ======
API_TOKEN = "7923000946:AAHMosNsaHU1Oz-qTihaWlMDYqCV2vhHT1E"
ALLOWED_USER_ID = 7469299312  # Your Telegram ID
# =====================

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Setup Bot & Dispatcher
bot = Bot(token=API_TOKEN, default=DefaultBotProperties(parse_mode=ParseMode.HTML))
dp = Dispatcher(storage=MemoryStorage())

# Flask App to keep service alive
app = Flask(__name__)

@app.route('/')
def index():
    return "Bot is running."

def run_web():
    app.run(host='0.0.0.0', port=8080)

# /status command
@dp.message()
async def status_handler(message: types.Message):
    if message.text.lower() == "status" and message.from_user.id == ALLOWED_USER_ID:
        await message.answer("✅ Bot is active and running.")

# Forex Signal Logic
def get_signals():
    try:
        df = yf.download("EURUSD=X", period="1d", interval="1m")
        if df.empty:
            return None
        close = df["Close"]
        if len(close) < 26:
            return None
        ema_fast = close.ewm(span=12, adjust=False).mean()
        ema_slow = close.ewm(span=26, adjust=False).mean()
        macd = ema_fast - ema_slow
        rsi = 100 - (100 / (1 + close.pct_change().dropna().rolling(window=14).mean()))
        last_macd = macd.iloc[-1]
        last_rsi = rsi.iloc[-1]
        last_price = close.iloc[-1]

        signals = []

        if last_macd > 0:
            signals.append("MACD")
        if last_rsi < 30:
            signals.append("RSI")

        if len(signals) >= 2:
            tp1 = round(last_price + 0.0020, 5)
            tp2 = round(last_price + 0.0040, 5)
            tp3 = round(last_price + 0.0060, 5)
            sl = round(last_price - 0.0020, 5)
            return f"📈 <b>BUY EUR/USD</b>\nEntry: {last_price:.5f}\nTP1: {tp1}\nTP2: {tp2}\nTP3: {tp3}\nSL: {sl}\nIndicators: {', '.join(signals)}"
        return None

    except Exception as e:
        logger.error(f"Error while checking EURUSD=X: {e}")
        return None

# Auto checker
async def loop_checker():
    logger.info("🔄 Checking market...")
    signal = get_signals()
    if signal:
        try:
            await bot.send_message(chat_id=ALLOWED_USER_ID, text=signal)
        except Exception as e:
            logger.error(f"❌ Failed to send signal: {e}")

# Background scheduler
scheduler = AsyncIOScheduler()
scheduler.add_job(loop_checker, "interval", minutes=1)

# Start everything
async def main():
    await bot.delete_webhook(drop_pending_updates=True)
    scheduler.start()
    Thread(target=run_web).start()
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())













