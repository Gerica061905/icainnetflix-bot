import os
import logging
from dotenv import load_dotenv
from telegram import Update, ParseMode
from telegram.ext import Updater, CommandHandler, CallbackContext
from datetime import datetime
load_dotenv()

TOKEN = os.getenv("BOT_TOKEN")
ADMIN_ID = int(os.getenv("ADMIN_ID"))


# Logging
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)

logger = logging.getLogger(__name__)
approved_users = set()

# --- COMMAND HANDLERS ---

def start(update: Update, context: CallbackContext):
    user_id = update.effective_user.id
    print("🧾 Approved Users:", approved_users)
    print("👤 Current User ID:", user_id)

    if user_id in approved_users:
        update.message.reply_text("✅ You’re already approved. Use /help to get started.")
        return

    # Send approval request to admin
    context.bot.send_message(
        chat_id=ADMIN_ID,
        text=f"🆕 Approval request from [{update.effective_user.full_name}](tg://user?id={user_id}) (`{user_id}`).\n\nReply with /approve {user_id} or /deny {user_id}.",
        parse_mode=ParseMode.MARKDOWN
    )

    update.message.reply_text("⏳ Waiting for admin approval...")

def approve(update: Update, context: CallbackContext):
    if update.effective_user.id != ADMIN_ID:
        return

    try:
        user_id = int(context.args[0])
    except (IndexError, ValueError):
        update.message.reply_text("❌ Usage: /approve <user_id>")
        return

    approved_users.add(user_id)
    context.bot.send_message(chat_id=user_id, text="✅ You have been approved to use this bot.")
    update.message.reply_text(f"✅ Approved user {user_id}.")

def deny(update: Update, context: CallbackContext):
    if update.effective_user.id != ADMIN_ID:
        return

    try:
        user_id = int(context.args[0])
    except (IndexError, ValueError):
        update.message.reply_text("❌ Usage: /deny <user_id>")
        return

    context.bot.send_message(chat_id=user_id, text="❌ Your access to the bot was denied.")
    update.message.reply_text(f"🚫 Denied user {user_id}.")

def remove_me(update: Update, context: CallbackContext):
    user_id = update.effective_user.id
    if user_id in approved_users:
        approved_users.remove(user_id)
        update.message.reply_text("❌ You’ve been removed from the approved list.")
    else:
        update.message.reply_text("You weren’t approved anyway.")

def help_command(update: Update, context: CallbackContext):
    update.message.reply_text("ℹ️ Available commands:\n/reset, /sicode, /tcode, /rslink, /hlink")

# --- MAIN ---

def main():
    updater = Updater(token=BOT_TOKEN, use_context=True)
    dispatcher = updater.dispatcher

    # Register handlers
    dispatcher.add_handler(CommandHandler("start", start))
    dispatcher.add_handler(CommandHandler("approve", approve))
    dispatcher.add_handler(CommandHandler("deny", deny))
    dispatcher.add_handler(CommandHandler("remove_me", remove_me))
    dispatcher.add_handler(CommandHandler("help", help_command))

    # Start polling
    updater.start_polling()
    logger.info("Bot started.")
    updater.idle()

if __name__ == "__main__":
    main()
