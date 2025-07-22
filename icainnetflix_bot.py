import os
import logging
import imaplib
import email
import re

from dotenv import load_dotenv
from telegram import Update
from telegram.ext import (
    ApplicationBuilder,
    CommandHandler,
    ContextTypes,
    MessageHandler,
    filters,
)
from apscheduler.schedulers.background import BackgroundScheduler
from telegram.constants import ParseMode

# Load .env
load_dotenv()

BOT_TOKEN = os.getenv("BOT_TOKEN")
ADMIN_ID = int(os.getenv("ADMIN_ID"))

# Logging
logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s", level=logging.INFO
)

# In-memory user tracking
pending_users = set()
approved_users = set()

# Load approved users from file
def load_approved_users():
    if os.path.exists("approved_users.txt"):
        with open("approved_users.txt", "r") as f:
            for line in f:
                approved_users.add(int(line.strip()))

def save_approved_user(user_id):
    with open("approved_users.txt", "a") as f:
        f.write(f"{user_id}\n")

# MarkdownV2 escape
def escape_markdown(text):
    escape_chars = r"_*[]()~`>#+-=|{}.!\\"
    return "".join("\\" + c if c in escape_chars else c for c in text)

# Start command
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    if user_id in approved_users:
        await context.bot.send_message(chat_id=user_id, text="✅ You are already approved.")
        return

    pending_users.add(user_id)
    username = update.effective_user.username or "unknown"
    msg = (
        f"⚠️ *New access request!*\n"
        f"👤 User: @{escape_markdown(username)} (`{user_id}`)\n\n"
        f"Use /approve {user_id} to grant access."
    )
    await context.bot.send_message(chat_id=ADMIN_ID, text=msg, parse_mode=ParseMode.MARKDOWN_V2)

    await context.bot.send_message(chat_id=user_id, text="⏳ Waiting for admin approval...")

# Approve command
async def approve(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id != ADMIN_ID:
        return

    if len(context.args) != 1 or not context.args[0].isdigit():
        await update.message.reply_text("Usage: /approve <user_id>")
        return

    user_id = int(context.args[0])
    approved_users.add(user_id)
    pending_users.discard(user_id)
    save_approved_user(user_id)

    await context.bot.send_message(chat_id=user_id, text="✅ Access granted!")
    await update.message.reply_text(f"User {user_id} has been approved.")

# Check access before commands
def require_approval(func):
    async def wrapper(update: Update, context: ContextTypes.DEFAULT_TYPE):
        user_id = update.effective_user.id
        if user_id not in approved_users:
            await update.message.reply_text("❌ Access denied. Use /start to request access.")
            return
        await func(update, context)
    return wrapper

# Gmail IMAP config
GMAIL_ACCOUNTS = [
    {
        "email": "colejxxne@gmail.com",
        "password": "gjyx otoh gbqo chlp",
    },
    {
        "email": "bayybaipo@gmail.com",
        "password": "bllx nusx tner jzpw",
    },
    {
        "email": "zachmuhs5@gmail.com",
        "password": "uczn rzqb tvty pyzv",
    },
    {
        "email": "sharinganieh@gmail.com",
        "password": "gzgp izfb gsuf yjqd",
    },
]

# Email search helper
def search_email(subject_keyword, extract_pattern):
    for account in GMAIL_ACCOUNTS:
        try:
            mail = imaplib.IMAP4_SSL("imap.gmail.com")
            mail.login(account["email"], account["password"])
            mail.select("inbox")
            result, data = mail.search(None, f'(SUBJECT "{subject_keyword}")')

            if result == "OK":
                for num in data[0].split()[::-1]:
                    result, msg_data = mail.fetch(num, "(RFC822)")
                    raw_email = msg_data[0][1]
                    msg = email.message_from_bytes(raw_email)
                    body = ""

                    if msg.is_multipart():
                        for part in msg.walk():
                            if part.get_content_type() == "text/plain":
                                body = part.get_payload(decode=True).decode()
                                break
                    else:
                        body = msg.get_payload(decode=True).decode()

                    match = re.search(extract_pattern, body)
                    if match:
                        mail.logout()
                        return match.group(1)
            mail.logout()
        except Exception as e:
            logging.error(f"Error checking {account['email']}: {e}")
    return None

# Commands
@require_approval
async def sicode(update: Update, context: ContextTypes.DEFAULT_TYPE):
    code = search_email("Your sign-in code", r"code is (\d{4})")
    msg = f"🔑 *Sign-in code:* `{code}`" if code else "❌ No sign-in code found."
    await update.message.reply_text(msg, parse_mode=ParseMode.MARKDOWN_V2)

@require_approval
async def tcode(update: Update, context: ContextTypes.DEFAULT_TYPE):
    code = search_email("Netflix temporary access code", r"code is (\d{4})")
    msg = f"🔑 *Temporary code:* `{code}`" if code else "❌ No temporary access code found."
    await update.message.reply_text(msg, parse_mode=ParseMode.MARKDOWN_V2)

@require_approval
async def reset(update: Update, context: ContextTypes.DEFAULT_TYPE):
    link = search_email("Complete your password reset request", r"(https://[^\s]+)")
    msg = f"🔗 *Reset link:* [Click here]({link})" if link else "❌ No reset link found."
    await update.message.reply_text(msg, parse_mode=ParseMode.MARKDOWN_V2)

@require_approval
async def rslink(update: Update, context: ContextTypes.DEFAULT_TYPE):
    link = search_email("Approve new sign in request", r"(https://[^\s]+)")
    msg = f"🔗 *Sign-in approval:* [Click here]({link})" if link else "❌ No sign-in approval link found."
    await update.message.reply_text(msg, parse_mode=ParseMode.MARKDOWN_V2)

@require_approval
async def hlink(update: Update, context: ContextTypes.DEFAULT_TYPE):
    link = search_email("How to Update your Netflix Household", r"(https://[^\s]+)")
    msg = f"🏠 *Household update:* [Click here]({link})" if link else "❌ No household update link found."
    await update.message.reply_text(msg, parse_mode=ParseMode.MARKDOWN_V2)

# Main
if __name__ == "__main__":
    load_approved_users()

    app = ApplicationBuilder().token(BOT_TOKEN).build()

    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("approve", approve))
    app.add_handler(CommandHandler("sicode", sicode))
    app.add_handler(CommandHandler("tcode", tcode))
    app.add_handler(CommandHandler("reset", reset))
    app.add_handler(CommandHandler("rslink", rslink))
    app.add_handler(CommandHandler("hlink", hlink))

    # Start background scheduler if needed
    scheduler = BackgroundScheduler()
    scheduler.start()

    print("✅ Bot is running...")
    app.run_polling()
