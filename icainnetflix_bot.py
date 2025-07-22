import os
import logging
from dotenv import load_dotenv
from telegram import Update, ParseMode
from telegram.ext import Updater, CommandHandler, CallbackContext
from datetime import datetime

# Load environment variables from .env file
load_dotenv()

# Get the BOT_TOKEN and ADMIN_ID
BOT_TOKEN = os.getenv("BOT_TOKEN")
ADMIN_ID = int(os.getenv("ADMIN_ID", "6658131120"))

if not BOT_TOKEN:
    raise ValueError("BOT_TOKEN is not set or loaded from .env")

# Approved users will be stored in a file
APPROVED_USERS_FILE = "approved_users.txt"

def get_approved_users():
    if not os.path.exists(APPROVED_USERS_FILE):
        return set()
    with open(APPROVED_USERS_FILE, "r") as f:
        return set(line.strip() for line in f if line.strip())

def add_approved_user(user_id):
    approved = get_approved_users()
    if str(user_id) not in approved:
        with open(APPROVED_USERS_FILE, "a") as f:
            f.write(f"{user_id}\n")

def remove_approved_user(user_id):
    approved = get_approved_users()
    if str(user_id) in approved:
        approved.remove(str(user_id))
        with open(APPROVED_USERS_FILE, "w") as f:
            for uid in approved:
                f.write(f"{uid}\n")

def is_user_approved(user_id):
    return str(user_id) in get_approved_users()

# /start command
def start(update: Update, context: CallbackContext):
    user_id = update.effective_user.id
    username = update.effective_user.username or update.effective_user.full_name

    if is_user_approved(user_id):
        update.message.reply_text("✅ Access granted. Use /sicode, /tcode, /reset, etc.")
    elif user_id == ADMIN_ID:
        add_approved_user(user_id)
        update.message.reply_text("👑 Hello Admin! You have full access.")
    else:
        context.bot.send_message(
            chat_id=ADMIN_ID,
            text=f"🔐 *Access request*\nUser: @{username}\nID: `{user_id}`\nReply with /approve {user_id} to grant access.",
            parse_mode=ParseMode.MARKDOWN
        )
        update.message.reply_text("🕒 Access request sent to admin. Please wait for approval.")

# /approve command (admin only)
def approve(update: Update, context: CallbackContext):
    user_id = update.effective_user.id
    if user_id != ADMIN_ID:
        update.message.reply_text("❌ You are not authorized to approve users.")
        return

    if not context.args:
        update.message.reply_text("⚠️ Usage: /approve <user_id>")
        return

    target_id = context.args[0]
    add_approved_user(target_id)
    update.message.reply_text(f"✅ Approved user `{target_id}`.", parse_mode=ParseMode.MARKDOWN)
    context.bot.send_message(chat_id=int(target_id), text="✅ You have been approved to use the bot!")

# /remove command (admin only)
def remove(update: Update, context: CallbackContext):
    user_id = update.effective_user.id
    if user_id != ADMIN_ID:
        update.message.reply_text("❌ You are not authorized to remove users.")
        return

    if not context.args:
        update.message.reply_text("⚠️ Usage: /remove <user_id>")
        return

    target_id = context.args[0]
    remove_approved_user(target_id)
    update.message.reply_text(f"❌ Removed user `{target_id}`.", parse_mode=ParseMode.MARKDOWN)

# Replace this with your command handlers like /sicode, etc.
def protected_command(update: Update, context: CallbackContext):
    user_id = update.effective_user.id
    if user_id != ADMIN_ID and not is_user_approved(user_id):
        update.message.reply_text("❌ Access denied. Please wait for admin approval.")
        return
    update.message.reply_text("✅ You are authorized to use this command.")

def main():
    logging.basicConfig(format='%(asctime)s - %(name)s - %(levelname)s - %(message)s', level=logging.INFO)
    updater = Updater(BOT_TOKEN, use_context=True)
    dispatcher = updater.dispatcher

    dispatcher.add_handler(CommandHandler("start", start))
    dispatcher.add_handler(CommandHandler("approve", approve))
    dispatcher.add_handler(CommandHandler("remove", remove))

    # Placeholder for protected commands (e.g., /sicode)
    dispatcher.add_handler(CommandHandler("protected", protected_command))

    updater.start_polling()
    updater.idle()

if __name__ == "__main__":
    main()
