import logging
import asyncio
import time
from aiogram import Bot, Dispatcher, F
from aiogram.enums import ParseMode
from aiogram.types import Message
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from datetime import datetime
import yfinance as yf

# === CONFIG ===
API_TOKEN = "7923000946:AAHMosNsaHU1Oz-qTihaWlMDYqCV2vhHT1E"
AUTHORIZED_USER_ID = 7469299312

bot = Bot(token=API_TOKEN, parse_mode=ParseMode.HTML)
dp = Dispatcher()
scheduler = AsyncIOScheduler()
last_loop_time = datetime.utcnow()

# === CHECK MARKET ===
async def loop_checker():
    global last_loop_time
    last_loop_time = datetime.utcnow()
    print(f"🔄 Checking market at {last_loop_time.isoformat()}")

    try:
        df = yf.download("EURUSD=X", period="1d", interval="5m", progress=False)
        if df.empty or len(df) < 30:
            return

        close = df["Close"]
        if close.isnull().iloc[-1]:
            return

        ema = close.ewm(span=20, adjust=False).mean()
        delta = close.diff()
        gain = delta.clip(lower=0).rolling(14).mean()
        loss = (-delta.clip(upper=0)).rolling(14).mean()
        rs = gain / loss
        rsi = 100 - (100 / (1 + rs))

        macd_line = close.ewm(span=12).mean() - close.ewm(span=26).mean()
        signal_line = macd_line.ewm(span=9).mean()

        mean = close.rolling(window=20).mean()
        std = close.rolling(window=20).std()
        upper_band = mean + 2 * std
        lower_band = mean - 2 * std

        signals = []
        price = close.iloc[-1]

        if rsi.iloc[-1] < 30 and price > ema.iloc[-1]:
            signals.append("📈 RSI & EMA agree (BUY)")
        if macd_line.iloc[-1] > signal_line.iloc[-1] and rsi.iloc[-1] < 50:
            signals.append("📈 MACD & RSI agree (BUY)")
        if price < lower_band.iloc[-1]:
            signals.append("📈 Price below Bollinger Band (BUY)")

        if rsi.iloc[-1] > 70 and price < ema.iloc[-1]:
            signals.append("📉 RSI & EMA agree (SELL)")
        if macd_line.iloc[-1] < signal_line.iloc[-1] and rsi.iloc[-1] > 50:
            signals.append("📉 MACD & RSI agree (SELL)")
        if price > upper_band.iloc[-1]:
            signals.append("📉 Price above Bollinger Band (SELL)")

        if len(signals) >= 2:
            msg = f"📊 <b>New Signal: EUR/USD</b>\n\n"
            msg += "\n".join(signals[:3])
            msg += f"\n\n<b>Entry:</b> {price:.5f}"
            msg += f"\n<b>TP1:</b> {price * 1.001:.5f}"
            msg += f"\n<b>TP2:</b> {price * 1.002:.5f}"
            msg += f"\n<b>TP3:</b> {price * 1.003:.5f}"
            msg += f"\n<b>SL:</b> {price * 0.998:.5f}"

            await bot.send_message(chat_id=AUTHORIZED_USER_ID, text=msg)

    except Exception as e:
        logging.error(f"Error while checking EURUSD=X: {e}")

# === STATUS COMMAND ===
@dp.message(F.text == "/status")
async def status(message: Message):
    if message.from_user.id != AUTHORIZED_USER_ID:
        return
    delay = (datetime.utcnow() - last_loop_time).total_seconds()
    if delay > 180:
        await message.answer("⚠️ Bot may be frozen (last check >3 mins ago).")
    else:
        await message.answer("✅ Bot is alive and working normally.")

# === MAIN FUNCTION ===
async def main():
    logging.basicConfig(level=logging.INFO)

    # 🧹 Force webhook clearing
    await bot.delete_webhook(drop_pending_updates=True)
    print("✅ Webhook cleared")
    await asyncio.sleep(3)  # ⏳ wait to ensure old polling stops

    scheduler.add_job(loop_checker, trigger="interval", minutes=1)
    scheduler.start()

    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())













