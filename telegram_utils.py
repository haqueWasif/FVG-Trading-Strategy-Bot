# telegram_utils.py
from telegram import Bot
from telegram.error import TelegramError
import logging
from config import TELEGRAM_BOT_TOKEN, TELEGRAM_CHAT_ID

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# Initialize Telegram bot
bot = Bot(token=TELEGRAM_BOT_TOKEN)

async def send_telegram_message(message):
    """Send a message via Telegram."""
    try:
        await bot.send_message(chat_id=TELEGRAM_CHAT_ID, text=message)
        logger.info(f"Sent Telegram message: {message}")
    except TelegramError as e:
        logger.error(f"Failed to send Telegram message: {e}")