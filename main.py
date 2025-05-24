import asyncio
import logging
import time
import pandas as pd
from aiogram import Bot, Dispatcher, types
from aiogram.enums import ParseMode
from flask import Flask
import threading
import yfinance as yf

# ✅ Hardcoded Telegram bot info
API_TOKEN = "7923000946:AAEx8TZsaIl6GL7XUwPGEM6a6-mBNfKwUz8"
USER_ID = 7469299312

bot = Bot(token=API_TOKEN, parse_mode=ParseMode.HTML)
dp = Dispatcher()

# === FLASK SERVER ===
app = Flask(__name__)

@app.route('/')
def home():
    return 'Bot is running!'

# === STRATEGIES ===
def rsi_strategy(df):
    delta = df['Close'].diff()
    gain = delta.where(delta > 0, 0).rolling(window=14).mean()
    loss = -delta.where(delta < 0, 0).rolling(window=14).mean()
    rs = gain / loss
    df['RSI'] = 100 - (100 / (1 + rs))
    return df['RSI'].iloc[-1] < 30 or df['RSI'].iloc[-1] > 70

def macd_strategy(df):
    df['EMA12'] = df['Close'].ewm(span=12).mean()
    df['EMA26'] = df['Close'].ewm(span=26).mean()
    df['MACD'] = df['EMA12'] - df['EMA26']
    df['Signal'] = df['MACD'].ewm(span=9).mean()
    return df['MACD'].iloc[-1] > df['Signal'].iloc[-1]

def ema_strategy(df):
    df['EMA20'] = df['Close'].ewm(span=20).mean()
    return df['Close'].iloc[-1] > df['EMA20'].iloc[-1]

def bollinger_strategy(df):
    df['MA20'] = df['Close'].rolling(window=20).mean()
    std = df['Close'].rolling(window=20).std()
    df['UpperBB'] = df['MA20'] + (2 * std)
    df['LowerBB'] = df['MA20'] - (2 * std)
    return df['Close'].iloc[-1] < df['LowerBB'].iloc[-1] or df['Close'].iloc[-1] > df['UpperBB'].iloc[-1]

# === MAIN LOGIC ===
async def check_signals():
    pairs = ["EURUSD=X"]
    while True:
        for symbol in pairs:
            try:
                df = yf.download(symbol, interval="5m", period="1d")
                if df.empty or 'Close' not in df:
                    continue

                signals = []
                if rsi_strategy(df): signals.append("RSI")
                if macd_strategy(df): signals.append("MACD")
                if ema_strategy(df): signals.append("EMA")
                if bollinger_strategy(df): signals.append("BOLL")

                if len(signals) >= 2:
                    price = df['Close'].iloc[-1]
                    message = (
                        f"📊 <b>Signal for {symbol.replace('=X', '')}</b>\n\n"
                        f"📈 Entry: <b>{price:.4f}</b>\n"
                        f"🎯 Take Profit 1: <b>{price * 1.002:.4f}</b>\n"
                        f"🎯 Take Profit 2: <b>{price * 1.004:.4f}</b>\n"
                        f"🎯 Take Profit 3: <b>{price * 1.006:.4f}</b>\n"
                        f"🛑 Stop Loss: <b>{price * 0.998:.4f}</b>\n"
                        f"🧠 Strategies: {', '.join(signals)}"
                    )
                    await bot.send_message(chat_id=USER_ID, text=message)
            except Exception as e:
                print(f"Error while checking {symbol}: {e}")
        await asyncio.sleep(300)  # Wait 5 minutes

# === STATUS COMMAND ===
@dp.message()
async def handle_status(message: types.Message):
    if message.chat.id == USER_ID and message.text.lower() == "status":
        await message.answer("✅ Bot is running and monitoring the market.")

# === THREAD START ===
def start_flask():
    app.run(host="0.0.0.0", port=8080)

def start():
    threading.Thread(target=start_flask).start()
    asyncio.run(main())

async def main():
    await bot.delete_webhook(drop_pending_updates=True)
    asyncio.create_task(check_signals())
    await dp.start_polling(bot)

# === RUN ===
if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    start()









