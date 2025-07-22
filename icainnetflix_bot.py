import os
import logging
import re
from telegram import Update
from telegram.ext import (
    ApplicationBuilder,
    CommandHandler,
    ContextTypes,
)
from apscheduler.schedulers.background import BackgroundScheduler

# Logging setup
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)

# Constants
BOT_TOKEN = os.getenv("BOT_TOKEN")
ADMIN_ID = 6658131120  # your admin Telegram user ID
APPROVED_USERS_FILE = "approved_users.txt"

# Utilities
def load_approved_users():
    if not os.path.exists(APPROVED_USERS_FILE):
        return set()
    with open(APPROVED_USERS_FILE, "r") as file:
        return set(map(str.strip, file.readlines()))

def save_approved_user(user_id):
    with open(APPROVED_USERS_FILE, "a") as file:
        file.write(f"{user_id}\n")

def escape_markdown(text: str) -> str:
    escape_chars = r'\_*[]()~`>#+-=|{}.!'
    return re.sub(f'([{re.escape(escape_chars)}])', r'\\\1', text)

# Command Handlers
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = str(update.effective_user.id)
    user_name = escape_markdown(update.effective_user.full_name)

    approved_users = load_approved_users()

    if user_id in approved_users:
        await context.bot.send_message(
            chat_id=update.effective_chat.id,
            text="✅ You are already approved. Welcome back!",
        )
        return

    await context.bot.send_message(
        chat_id=update.effective_chat.id,
        text="⏳ Access request sent to admin. Please wait for approval.",
    )

    await context.bot.send_message(
        chat_id=ADMIN_ID,
        text=(
            f"👤 New access request:\n"
            f"User: {user_name} (`{user_id}`)\n"
            f"Reply with /approve {user_id} to grant access."
        ),
        parse_mode="MarkdownV2"
    )

async def approve(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if str(update.effective_user.id) != str(ADMIN_ID):
        await context.bot.send_message(
            chat_id=update.effective_chat.id,
            text="❌ You are not authorized to approve users.",
        )
        return

    if not context.args:
        await context.bot.send_message(
            chat_id=update.effective_chat.id,
            text="⚠️ Please specify the user ID to approve.\nExample: /approve 123456789",
        )
        return

    user_id = context.args[0]
    approved_users = load_approved_users()

    if user_id in approved_users:
        await context.bot.send_message(
            chat_id=update.effective_chat.id,
            text=f"ℹ️ User {user_id} is already approved.",
        )
        return

    save_approved_user(user_id)

    await context.bot.send_message(
        chat_id=user_id,
        text="✅ Your access has been approved! You may now use the bot.",
    )

    await context.bot.send_message(
        chat_id=update.effective_chat.id,
        text=f"✅ User {user_id} approved successfully.",
    )

# Main
if __name__ == "__main__":
    app = ApplicationBuilder().token(BOT_TOKEN).build()

    # Register command handlers
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("approve", approve))

    # Scheduler (optional if you have periodic tasks)
    scheduler = BackgroundScheduler()
    scheduler.start()

    print("🤖 Bot is running...")
    app.run_polling()
