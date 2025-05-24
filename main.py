import asyncio
import os
import logging
import traceback
import pandas as pd
import yfinance as yf

from aiogram import Bot, Dispatcher, types
from aiogram.enums import ParseMode
from aiogram.types import Message
from aiogram.client.session.aiohttp import AiohttpSession
from aiogram.fsm.storage.memory import MemoryStorage
from datetime import datetime
from apscheduler.schedulers.asyncio import AsyncIOScheduler

# Load from environment variables
API_TOKEN = os.getenv("API_TOKEN")
USER_ID = int(os.getenv("USER_ID"))

# Bot setup
bot = Bot(token=API_TOKEN, session=AiohttpSession(), parse_mode=ParseMode.HTML)
dp = Dispatcher(storage=MemoryStorage())

# Logger
logging.basicConfig(level=logging.INFO)

# Strategy thresholds
RSI_OVERSOLD = 30
RSI_OVERBOUGHT = 70

# Forex pairs
PAIRS = ["EURUSD=X", "GBPUSD=X", "USDJPY=X", "USDCHF=X", "AUDUSD=X", "USDCAD=X"]

# ---- Strategy Calculation ----

def analyze_data(df):
    signals = {}

    # EMA
    df['EMA20'] = df['Close'].ewm(span=20).mean()

    # MACD
    df['EMA12'] = df['Close'].ewm(span=12).mean()
    df['EMA26'] = df['Close'].ewm(span=26).mean()
    df['MACD'] = df['EMA12'] - df['EMA26']
    df['Signal'] = df['MACD'].ewm(span=9).mean()

    # Bollinger Bands
    df['MiddleBB'] = df['Close'].rolling(window=20).mean()
    df['StdDev'] = df['Close'].rolling(window=20).std()
    df['UpperBB'] = df['MiddleBB'] + (df['StdDev'] * 2)
    df['LowerBB'] = df['MiddleBB'] - (df['StdDev'] * 2)

    # RSI
    delta = df['Close'].diff()
    gain = (delta.where(delta > 0, 0)).rolling(14).mean()
    loss = (-delta.where(delta < 0, 0)).rolling(14).mean()
    rs = gain / loss
    df['RSI'] = 100 - (100 / (1 + rs))

    # Take last row
    row = df.iloc[-1]
    price = row['Close']

    # Strategy agreement counter
    agreement = []

    if row['RSI'] < RSI_OVERSOLD:
        agreement.append("RSI")

    if row['MACD'] > row['Signal']:
        agreement.append("MACD")

    if price > row['EMA20']:
        agreement.append("EMA")

    if price < row['LowerBB']:
        agreement.append("Bollinger")

    if len(agreement) >= 2:
        sl = round(price - (price * 0.005), 5)
        tp1 = round(price + (price * 0.005), 5)
        tp2 = round(price + (price * 0.010), 5)
        tp3 = round(price + (price * 0.015), 5)

        return {
            "price": round(price, 5),
            "tp": [tp1, tp2, tp3],
            "sl": sl,
            "strategies": agreement
        }

    return None

# ---- Telegram Tasks ----

async def send_signal():
    for pair in PAIRS:
        try:
            df = yf.download(pair, period="7d", interval="15m", progress=False)
            signal = analyze_data(df)
            if signal:
                msg = (
                    f"📈 <b>Signal for {pair.replace('=X', '')}</b>\n"
                    f"💰 Entry: <code>{signal['price']}</code>\n"
                    f"🎯 Take Profits:\n"
                    f"  • TP1: <code>{signal['tp'][0]}</code>\n"
                    f"  • TP2: <code>{signal['tp'][1]}</code>\n"
                    f"  • TP3: <code>{signal['tp'][2]}</code>\n"
                    f"🛡️ Stop Loss: <code>{signal['sl']}</code>\n"
                    f"📊 Strategies: {', '.join(signal['strategies'])}"
                )
                await bot.send_message(USER_ID, msg)
        except Exception as e:
            logging.error(f"{pair} Error: {e}")

# ---- Safety Monitoring ----

async def loop_checker():
    try:
        await send_signal()
    except Exception as e:
        logging.error(f"Loop crashed: {traceback.format_exc()}")
        await bot.send_message(USER_ID, f"⚠️ Bot crashed:\n<pre>{e}</pre>")

# ---- Commands ----

@dp.message()
async def handle_status(msg: Message):
    if msg.from_user.id == USER_ID and msg.text.lower() == "status":
        await msg.answer("✅ Bot is running and monitoring the market.")

# ---- Start Bot ----

async def main():
    scheduler = AsyncIOScheduler()
    scheduler.add_job(loop_checker, "interval", minutes=15)
    scheduler.start()

    await bot.delete_webhook(drop_pending_updates=True)
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())












