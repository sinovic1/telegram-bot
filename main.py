import os
import asyncio
import logging
import yfinance as yf
from aiogram import Bot, Dispatcher, Router, F
from aiogram.types import Message, BotCommand
from aiogram.enums import ParseMode
from aiogram.exceptions import TelegramConflictError

API_TOKEN = "7923000946:AAEx8TZsaIl6GL7XUwPGEM6a6-mBNfKwUz8"
USER_ID = 7469299312

bot = Bot(token=API_TOKEN, parse_mode=ParseMode.HTML)
dp = Dispatcher()
router = Router()
dp.include_router(router)

async def clear_webhook():
    try:
        await bot.delete_webhook(drop_pending_updates=True)
        print("✅ Webhook cleared successfully")
    except Exception as e:
        print(f"❌ Failed to clear webhook: {e}")

@router.message(F.text == "/status")
async def status_command(message: Message):
    if message.chat.id == USER_ID:
        await message.answer("✅ Bot is running and monitoring the market.")

def get_signal():
    try:
        data = yf.download("EURUSD=X", period="1d", interval="15m")
        if data.empty:
            return None
        latest = data.iloc[-1]
        return f"<b>EUR/USD Signal</b>\nClose: {latest['Close']:.5f}"
    except Exception as e:
        logging.error(f"Error while checking EURUSD=X: {e}")
        return None

async def send_alert():
    signal = get_signal()
    if signal:
        await bot.send_message(chat_id=USER_ID, text=signal)

async def monitor():
    while True:
        try:
            await send_alert()
            await asyncio.sleep(900)
        except Exception as e:
            logging.error(f"Monitoring error: {e}")
            await asyncio.sleep(30)

async def main():
    logging.basicConfig(level=logging.INFO)
    await clear_webhook()
    await bot.set_my_commands([BotCommand(command="status", description="Check bot status")])
    asyncio.create_task(monitor())
    try:
        await dp.start_polling(bot)
    except TelegramConflictError:
        logging.error("❗ Another instance of the bot is already polling Telegram.")

if __name__ == '__main__':
    asyncio.run(main())










