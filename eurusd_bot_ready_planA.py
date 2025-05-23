import logging
import asyncio
import yfinance as yf
import pandas as pd
from aiogram import Bot, Dispatcher, F
from aiogram.enums import ParseMode
from aiogram.types import Message
from aiogram.filters import Command
from datetime import datetime, timedelta
from keep_alive import keep_alive
import os

keep_alive()

bot = Bot(token=os.getenv("TELEGRAM_BOT_TOKEN"), parse_mode=ParseMode.HTML)
dp = Dispatcher()
TELEGRAM_USER_ID = int(os.getenv("TELEGRAM_USER_ID"))

PAIRS = [("EURUSD=X", "Yggdrag")]
CHECK_EVERY_SECONDS = 60
WARNING_THRESHOLD_MINUTES = 5
last_activity_time = datetime.utcnow()

async def send_signal(pair_info):
    global last_activity_time
    symbol, name = pair_info
    try:
        df = yf.download(symbol, period="2d", interval="5m")
        if df.empty or "Close" not in df:
            return
        close = df["Close"]
        ema20 = close.ewm(span=20, adjust=False).mean()
        delta = close.diff()
        gain = delta.clip(lower=0)
        loss = -delta.clip(upper=0)
        rs = gain.rolling(14).mean() / loss.rolling(14).mean()
        rsi = 100 - (100 / (1 + rs))
        std = close.rolling(window=20).std()
        upper_bb = ema20 + 2 * std
        lower_bb = ema20 - 2 * std
        macd = close.ewm(span=12).mean() - close.ewm(span=26).mean()
        signal = macd.ewm(span=9).mean()

        df = pd.concat([close, ema20, rsi, upper_bb, lower_bb, macd, signal], axis=1)
        df.columns = ["Close", "EMA20", "RSI", "UpperBB", "LowerBB", "MACD", "Signal"]
        df.dropna(inplace=True)
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
        price = round(last["Close"], 5)
        signal_type = None
        if len([s for s in signals if "Buy" in s]) >= 2:
            signal_type = "Buy"
        elif len([s for s in signals if "Sell" in s]) >= 2:
            signal_type = "Sell"
        if signal_type:
            agreed = len([s for s in signals if signal_type in s])
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
            await bot.send_message(chat_id=TELEGRAM_USER_ID, text=message)
        last_activity_time = datetime.utcnow()
    except Exception as e:
        logging.error(f"Error for {symbol}: {e}")

async def check_loop():
    while True:
        for pair in PAIRS:
            await send_signal(pair)
        await asyncio.sleep(CHECK_EVERY_SECONDS)

async def monitor_loop():
    global last_activity_time
    while True:
        now = datetime.utcnow()
        if now - last_activity_time > timedelta(minutes=WARNING_THRESHOLD_MINUTES):
            await bot.send_message(chat_id=TELEGRAM_USER_ID, text=⚠️ Warning: Bot seems to be stuck or delayed!")
        await asyncio.sleep(60)

@dp.message(Command("status"))
async def handle_status(message: Message):
    if message.from_user.id == TELEGRAM_USER_ID:
        await message.answer("✅ Bot is still running and monitoring the market.")

async def main():
    asyncio.create_task(check_loop())
    asyncio.create_task(monitor_loop())
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())

