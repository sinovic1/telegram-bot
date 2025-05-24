import logging
import asyncio
import yfinance as yf
from aiogram import Bot, Dispatcher, types
from aiogram.enums import ParseMode
from aiogram.fsm.strategy import FSMStrategy
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from datetime import datetime
from flask import Flask
import threading

# 🔒 Your hard-coded credentials (safe only for testing, don’t expose in public!)
API_TOKEN = "7923000946:AAHMosNsaHU1Oz-qTihaWlMDYqCV2vhHT1E"
USER_ID = 7469299312  # Replace if different

# Initialize logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Setup bot
bot = Bot(token=API_TOKEN, parse_mode=ParseMode.HTML)
dp = Dispatcher(fsm_strategy=FSMStrategy.CHAT)

# Setup Flask app to keep Koyeb alive
app = Flask(__name__)

@app.route('/')
def home():
    return "Bot is alive!"

def run_flask():
    app.run(host='0.0.0.0', port=8080)

# Track last signal time for health check
last_signal_time = None

# Strategies (simplified example)
def check_signals():
    global last_signal_time
    try:
        df = yf.download("EURUSD=X", period="1d", interval="1m")
        if df.empty:
            return None

        close = df["Close"]
        ema = close.ewm(span=10).mean()
        rsi = 100 - (100 / (1 + (close.diff().clip(lower=0).rolling(14).mean() /
                                close.diff().clip(upper=0).abs().rolling(14).mean())))

        signal = []

        if rsi.iloc[-1] < 30 and close.iloc[-1] > ema.iloc[-1]:
            signal.append("BUY")

        if rsi.iloc[-1] > 70 and close.iloc[-1] < ema.iloc[-1]:
            signal.append("SELL")

        if len(signal) >= 2:
            last_signal_time = datetime.utcnow()
            entry = close.iloc[-1]
            tp1 = round(entry * 1.002, 5)
            tp2 = round(entry * 1.004, 5)
            tp3 = round(entry * 1.006, 5)
            sl = round(entry * 0.996, 5)
            return f"""
📈 <b>EUR/USD Signal</b>
Type: <b>{signal[0]}</b>
Entry: <b>{entry}</b>
TP1: <b>{tp1}</b>
TP2: <b>{tp2}</b>
TP3: <b>{tp3}</b>
SL: <b>{sl}</b>
"""
    except Exception as e:
        logger.error(f"Error while checking EURUSD=X: {e}")
    return None

# Status command
@dp.message(lambda msg: msg.text == "/status" and msg.from_user.id == USER_ID)
async def status_handler(message: types.Message):
    await message.answer("✅ Bot is running and monitoring the market.")

# Main loop
async def main():
    try:
        await bot.delete_webhook(drop_pending_updates=True)
        logger.info("✅ Webhook cleared")
    except Exception as e:
        logger.warning(f"Webhook clear failed: {e}")

    scheduler = AsyncIOScheduler()
    
    async def loop_checker():
        logger.info(f"🔄 Checking market at {datetime.utcnow().isoformat()}")
        signal = check_signals()
        if signal:
            await bot.send_message(USER_ID, signal, parse_mode=ParseMode.HTML)

    scheduler.add_job(loop_checker, "interval", minutes=1)
    scheduler.start()

    await dp.start_polling(bot)

# Start everything
if __name__ == "__main__":
    threading.Thread(target=run_flask).start()
    asyncio.run(main())











