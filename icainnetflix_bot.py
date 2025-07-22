import os
import logging
from dotenv import load_dotenv
from telegram import Update, ParseMode
from telegram.ext import Updater, CommandHandler, CallbackContext
from datetime import datetime

# Load environment variables from .env file
load_dotenv()

# Get the BOT_TOKEN from .env
BOT_TOKEN = os.getenv("BOT_TOKEN")
ADMIN_ID = int(os.getenv("ADMIN_ID", "0"))

# Debug print (optional)
print("BOT_TOKEN:", BOT_TOKEN)

# Fail early if the token is missing
if not BOT_TOKEN:
    raise ValueError("BOT_TOKEN is not set or loaded from .env")

# Initialize the updater
updater = Updater(BOT_TOKEN, use_context=True)
dispatcher = updater.dispatcher

# Set up logging
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)

# Example /start command handler
def start(update: Update, context: CallbackContext):
    user_id = update.effective_user.id
    if user_id != ADMIN_ID:
        update.message.reply_text("Access denied. You're not authorized.")
        return
    update.message.reply_text("Welcome, admin!")

# Add command handlers
dispatcher.add_handler(CommandHandler("start", start))

# Define main loop
def main():
    logging.info("Bot is starting...")
    updater = Updater(BOT_TOKEN, use_context=True)  # Use BOT_TOKEN, not TOKEN
    dispatcher = updater.dispatcher

    # Example handler
    dispatcher.add_handler(CommandHandler("start", start))

    updater.start_polling()
    updater.idle()

# Run the bot
if __name__ == "__main__":
    main()
