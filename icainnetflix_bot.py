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

# Fail early if the token is missing
if not BOT_TOKEN:
    raise ValueError("BOT_TOKEN is not set or loaded from .env")

# Set up logging
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)

# Example /start command handler
# inside your bot code (replace the existing /start handler)
def start(update: Update, context: CallbackContext):
    user_id = update.effective_user.id
    admin_id = 6658131120

    # Check if user is already approved
    if str(user_id) in get_approved_users():
        update.message.reply_text("✅ Access granted. Use /sicode, /tcode, /reset, etc.")
        return

    # If user is the admin, grant access automatically
    if user_id == admin_id:
        add_approved_user(user_id)
        update.message.reply_text("👑 Hello Admin! You now have access.")
        return

    # Send approval request to admin
    context.bot.send_message(
        chat_id=admin_id,
        text=f"👤 New access request:\nUser: {update.effective_user.full_name} (`{user_id}`)\nReply with `/approve {user_id}` to grant access.",
        parse_mode=ParseMode.MARKDOWN
    )

    update.message.reply_text("🕒 Request sent for approval. Please wait for admin confirmation.")


# Define main loop
def main():
    logging.info("Bot is starting...")
    
    # Create updater and dispatcher inside main
    updater = Updater(BOT_TOKEN, use_context=True)
    dispatcher = updater.dispatcher

    # Register handlers
    dispatcher.add_handler(CommandHandler("start", start))

    # Start polling
    updater.start_polling()
    updater.idle()

# Run the bot
if __name__ == "__main__":
    main()
