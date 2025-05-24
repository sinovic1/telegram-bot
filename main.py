import logging
import asyncio
from aiogram import Bot, Dispatcher, F
from aiogram.enums import ParseMode
from aiogram.types import Message
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from datetime import datetime
import yfinance as yf

# === Hardcoded BOT settings ===
API_TOKEN = "7923000946:AAHMosNsaHU1Oz-qTihaWlMDYqCV2vhHT1E"
AUTHORIZED_USER_ID = 7469299312

bot = Bot(token=API_TOKEN, parse_mode=ParseMode.HTML)
dp = Dispatcher()
scheduler = AsyncIOScheduler()

last_loop_time = datetime.utcnow()

# === Trading check function ===
async def loop_checker():
    global last_loop_time
    last_loop_time = datetime.utcnow()
    print(f"🔄 Checking market at {last_loop_time.isoformat()}")

    try:
        df = yf.download("EURUSD=X", period="1d", interval="5m")
        if df.empty:
            return

        close = df["Close"]
        ema = close.ewm(span=20, adjust=False).mean()
        rsi = 100 - (100 / (1 + (close.diff().clip(lower=0).rolling(14).mean() /
                                close.diff().clip(upper=0).abs().rolling(14).mean())))
        macd_line = close.ewm(span=12).mean() - close.ewm(span=26).mean()
        signal_line = macd_line.ewm(span=9).mean()
        upper_band = close.rolling(20).mean() + 2 * close.rolling(20).std()
        lower_band = close.rolling(20).mean() - 2 * close.rolling(20).std()

        signals = []

        if rsi.iloc[-1] < 30 and close.iloc[-1] > ema.iloc[-1]:
            signals.append("📈 RSI & EMA indicate BUY")
        if macd_line.iloc[-1] > signal_line.iloc[-1] and rsi.iloc[-1] < 50:
            signals.append("📈 MACD & RSI indicate BUY")
        if close.iloc[-1] < lower_band.iloc[-1]:
            signals.append("📈 Bollinger Bands suggest BUY")
        if rsi.iloc[-1] > 70 and close.iloc[-1] < ema.iloc[-1]:
            signals.append("📉 RSI & EMA indicate SELL")
        if macd_line.iloc[-1] < signal_line.iloc[-1] and rsi.iloc[-1] > 50:
            signals.append("📉 MACD & RSI indicate SELL")
        if close.iloc[-1] > upper_band.iloc[-1]:
            signals.append("📉 Bollinger Bands suggest SELL")

        if len(signals) >= 2:
            msg = "📊 <b>New Forex Signal - EUR/USD</b>\n\n"
            msg += "\n".join(signals[:3])
            msg += "\n\n<b>Entry:</b> {:.5f}".format(close.iloc[-1])
            msg += "\n<b>TP1:</b> {:.5f}".format(close.iloc[-1] * 1.001)
            msg += "\n<b>TP2:</b> {:.5f}".format(close.iloc[-1] * 1.002)
            msg += "\n<b>TP3:</b> {:.5f}".format(close.iloc[-1] * 1.003)
            msg += "\n<b>SL:</b> {:.5f}".format(close.iloc[-1] * 0.998)

            await bot.send_message(chat_id=AUTHORIZED_USER_ID, text=msg, parse_mode=ParseMode.HTML)

    except Exception as e:
        logging.error(f"Error while checking EURUSD=X: {e}")

# === /status command ===
@dp.message(F.text == "/status")
async def status(message: Message):
    if message.from_user.id != AUTHORIZED_USER_ID:
        return
    now = datetime.utcnow()
    delay = (now - last_loop_time).total_seconds()
    if delay > 180:
        await message.answer("⚠️ Warning: Bot loop seems delayed or frozen!")
    else:
        await message.answer("✅ Bot is running and monitoring the market.")

# === Startup function ===
async def main():
    logging.basicConfig(level=logging.INFO)
    scheduler.add_job(loop_checker, trigger="interval", minutes=1)
    scheduler.start()
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())












