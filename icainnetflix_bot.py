import os
import logging
import imaplib
import email
import re
from datetime import datetime, timedelta
from dotenv import load_dotenv
from telegram import Update, ParseMode
from telegram.ext import Updater, CommandHandler, CallbackContext

# Load environment variables
load_dotenv()

# Bot token and admin ID
BOT_TOKEN = os.getenv("BOT_TOKEN")
ADMIN_ID = int(os.getenv("ADMIN_ID"))

# Gmail credentials
GMAIL_ACCOUNTS = [
    (os.getenv("GMAIL_1_EMAIL"), os.getenv("GMAIL_1_APP_PASSWORD")),
    (os.getenv("GMAIL_2_EMAIL"), os.getenv("GMAIL_2_APP_PASSWORD")),
    (os.getenv("GMAIL_3_EMAIL"), os.getenv("GMAIL_3_APP_PASSWORD")),
    (os.getenv("GMAIL_4_EMAIL"), os.getenv("GMAIL_4_APP_PASSWORD")),
]

# Logging
logging.basicConfig(format='%(asctime)s - %(name)s - %(levelname)s - %(message)s', level=logging.INFO)

# Approved users memory
approved_users = set()

# --- Email Utilities ---

def search_email(subject_filter: str, is_link=False):
    for email_address, app_password in GMAIL_ACCOUNTS:
        try:
            mail = imaplib.IMAP4_SSL("imap.gmail.com")
            mail.login(email_address, app_password)
            mail.select("inbox")

            result, data = mail.search(None, '(UNSEEN SUBJECT "{}")'.format(subject_filter))
            if result == "OK":
                email_ids = data[0].split()
                for e_id in reversed(email_ids):
                    result, msg_data = mail.fetch(e_id, "(RFC822)")
                    if result != "OK":
                        continue
                    raw_email = msg_data[0][1]
                    msg = email.message_from_bytes(raw_email)
                    body = ""

                    if msg.is_multipart():
                        for part in msg.walk():
                            if part.get_content_type() == "text/plain":
                                body += part.get_payload(decode=True).decode()
                    else:
                        body = msg.get_payload(decode=True).decode()

                    if is_link:
                        urls = re.findall(r"https?://\S+", body)
                        if urls:
                            return urls[0]
                    else:
                        code_match = re.search(r"\b\d{4}\b", body)
                        if code_match:
                            return code_match.group()
            mail.logout()
        except Exception as e:
            print(f"Error reading {email_address}: {e}")
    return None

# --- Command Handlers ---

def start(update: Update, context: CallbackContext):
    user_id = update.effective_user.id
    if user_id in approved_users or user_id == ADMIN_ID:
        context.bot.send_message(chat_id=update.effective_chat.id, text="✅ You are already approved.")
    else:
        context.bot.send_message(chat_id=ADMIN_ID, text=f"👤 User ID `{user_id}` wants to access the bot.\n\nApprove using:\n`/approve {user_id}`", parse_mode=ParseMode.MARKDOWN)
        context.bot.send_message(chat_id=user_id, text="⏳ Waiting for admin approval...")

def approve(update: Update, context: CallbackContext):
    if update.effective_user.id != ADMIN_ID:
        return
    try:
        user_id = int(context.args[0])
        approved_users.add(user_id)
        context.bot.send_message(chat_id=user_id, text="✅ Access granted by admin.")
        context.bot.send_message(chat_id=ADMIN_ID, text=f"👍 User `{user_id}` has been approved.", parse_mode=ParseMode.MARKDOWN)
    except:
        context.bot.send_message(chat_id=update.effective_chat.id, text="⚠️ Usage: /approve <user_id>")

def require_approval(func):
    def wrapper(update: Update, context: CallbackContext):
        user_id = update.effective_user.id
        if user_id in approved_users or user_id == ADMIN_ID:
            return func(update, context)
        else:
            context.bot.send_message(chat_id=user_id, text="⛔ You are not approved yet.")
    return wrapper

@require_approval
def sicode(update: Update, context: CallbackContext):
    code = search_email("Your sign-in code")
    msg = f"🔐 *Sign-in Code:* `{code}`" if code else "❌ Code not found."
    context.bot.send_message(chat_id=update.effective_chat.id, text=msg, parse_mode=ParseMode.MARKDOWN)

@require_approval
def tcode(update: Update, context: CallbackContext):
    code = search_email("Netflix temporary access code")
    msg = f"🎟️ *Temporary Access Code:* `{code}`" if code else "❌ Code not found."
    context.bot.send_message(chat_id=update.effective_chat.id, text=msg, parse_mode=ParseMode.MARKDOWN)

@require_approval
def reset(update: Update, context: CallbackContext):
    link = search_email("Complete your password reset request", is_link=True)
    msg = f"[🔗 Reset Password Link]({link})" if link else "❌ Reset link not found."
    context.bot.send_message(chat_id=update.effective_chat.id, text=msg, parse_mode=ParseMode.MARKDOWN)

@require_approval
def rslink(update: Update, context: CallbackContext):
    link = search_email("Approve new sign in request", is_link=True)
    msg = f"[🔐 Approve Sign-in Link]({link})" if link else "❌ Sign-in link not found."
    context.bot.send_message(chat_id=update.effective_chat.id, text=msg, parse_mode=ParseMode.MARKDOWN)

@require_approval
def hlink(update: Update, context: CallbackContext):
    link = search_email("How to Update your Netflix Household", is_link=True)
    msg = f"[🏠 Household Update Link]({link})" if link else "❌ Household link not found."
    context.bot.send_message(chat_id=update.effective_chat.id, text=msg, parse_mode=ParseMode.MARKDOWN)

def main():
    updater = Updater(token=BOT_TOKEN, use_context=True)
    dp = updater.dispatcher

    dp.add_handler(CommandHandler("start", start))
    dp.add_handler(CommandHandler("approve", approve))
    dp.add_handler(CommandHandler("sicode", sicode))
    dp.add_handler(CommandHandler("tcode", tcode))
    dp.add_handler(CommandHandler("reset", reset))
    dp.add_handler(CommandHandler("rslink", rslink))
    dp.add_handler(CommandHandler("hlink", hlink))

    updater.start_polling()
    updater.idle()

if __name__ == "__main__":
    main()
