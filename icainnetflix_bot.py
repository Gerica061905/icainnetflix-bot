import os
import imaplib
import email
import re
import logging
from datetime import datetime, timedelta
from dotenv import load_dotenv
from telegram import Update, ParseMode
from telegram.ext import Updater, CommandHandler, CallbackContext

# Load environment variables
load_dotenv()

BOT_TOKEN = os.getenv("BOT_TOKEN")
ADMIN_ID = int(os.getenv("ADMIN_ID"))

# Gmail accounts and app passwords
GMAIL_ACCOUNTS = [
    (os.getenv("GMAIL_1_EMAIL"), os.getenv("GMAIL_1_PASS")),
    (os.getenv("GMAIL_2_EMAIL"), os.getenv("GMAIL_2_PASS")),
    (os.getenv("GMAIL_3_EMAIL"), os.getenv("GMAIL_3_PASS")),
    (os.getenv("GMAIL_4_EMAIL"), os.getenv("GMAIL_4_PASS")),
]

# Approved users cache
approved_users = set()
pending_requests = {}

# Enable logging
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s', level=logging.INFO
)
logger = logging.getLogger(__name__)

def require_approval(func):
    def wrapper(update: Update, context: CallbackContext):
        user_id = update.effective_user.id
        if user_id == ADMIN_ID or user_id in approved_users:
            return func(update, context)
        else:
            context.bot.send_message(
                chat_id=ADMIN_ID,
                text=f"⚠️ New user access request:\nName: {update.effective_user.full_name}\nID: `{user_id}`",
                parse_mode=ParseMode.MARKDOWN,
            )
            pending_requests[user_id] = datetime.now()
            update.message.reply_text("⏳ Awaiting admin approval...")
    return wrapper

def approve(update: Update, context: CallbackContext):
    if update.effective_user.id != ADMIN_ID:
        return
    if not context.args:
        update.message.reply_text("Usage: /approve <user_id>")
        return
    user_id = int(context.args[0])
    approved_users.add(user_id)
    context.bot.send_message(chat_id=user_id, text="✅ You are now approved!")
    update.message.reply_text(f"Approved user {user_id}.")

@require_approval
def start(update: Update, context: CallbackContext):
    user_id = update.effective_user.id
    msg = (
        "🌸 *Welcome to @ic4in Netflix Bot!* 🌸\n\n"
        "To request something, use the command *plus your email*.\n"
        "_Example:_ `/sicode your@email.com`\n\n"
        "💖 *Available Commands:* 💖\n"
        "`/sicode` – Sign in code\n"
        "`/tcode` – Tempo code\n"
        "`/reset` – Reset password link\n"
        "`/hlink` – Household link\n"
        "`/rslink` – Request sign-in link\n\n"
        "⚠️ Access is required. Wait for admin approval if this is your first time.\n"
        "_Note: Access is valid for 7 days only._"
    )

    if user_id in approved_users:
        update.message.reply_markdown(msg)
    else:
        update.message.reply_markdown(msg + "\n\n⏳ Requesting access from admin...")
        context.bot.send_message(
            chat_id=ADMIN_ID,
            text=(
                f"🔐 Access request from @{update.effective_user.username or 'NoUsername'} (ID: `{user_id}`).\n"
                f"`/approve {user_id}` to approve\n"
                f"`/remove {user_id}` to remove"
            ),
            parse_mode=ParseMode.MARKDOWN
        )


def search_email(subject_filter: str, is_link=False):
    for email_address, app_password in GMAIL_ACCOUNTS:
        try:
            mail = imaplib.IMAP4_SSL("imap.gmail.com")
            mail.login(email_address, app_password)
            mail.select("inbox")
            result, data = mail.search(None, "UNSEEN")
            if result == "OK":
                email_ids = data[0].split()
                for e_id in reversed(email_ids):
                    result, msg_data = mail.fetch(e_id, "(RFC822)")
                    if result != "OK":
                        continue
                    raw_email = msg_data[0][1]
                    msg = email.message_from_bytes(raw_email)
                    subject = msg["Subject"] or ""
                    if subject_filter.lower() not in subject.lower():
                        continue
                    body = ""
                    if msg.is_multipart():
                        for part in msg.walk():
                            if part.get_content_type() == "text/plain":
                                body += part.get_payload(decode=True).decode(errors="ignore")
                    else:
                        body = msg.get_payload(decode=True).decode(errors="ignore")
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
            logger.error(f"Error accessing {email_address}: {e}")
    return "Not found"

@require_approval
def sicode(update: Update, context: CallbackContext):
    code = search_email("Your sign-in code")
    update.message.reply_text(f"🔐 *Sign-in Code:* `{code}`", parse_mode=ParseMode.MARKDOWN)

@require_approval
def tcode(update: Update, context: CallbackContext):
    code = search_email("Netflix temporary access code")
    update.message.reply_text(f"🔑 *Temporary Code:* `{code}`", parse_mode=ParseMode.MARKDOWN)

@require_approval
def reset(update: Update, context: CallbackContext):
    link = search_email("Complete your password reset request", is_link=True)
    update.message.reply_text(f"🔁 [Reset Link]({link})", parse_mode=ParseMode.MARKDOWN)

@require_approval
def rslink(update: Update, context: CallbackContext):
    link = search_email("Approve new sign in request", is_link=True)
    update.message.reply_text(f"🔓 [Sign-In Link]({link})", parse_mode=ParseMode.MARKDOWN)

@require_approval
def hlink(update: Update, context: CallbackContext):
    link = search_email("How to Update your Netflix Household", is_link=True)
    update.message.reply_text(f"🏠 [Household Link]({link})", parse_mode=ParseMode.MARKDOWN)

def main():
    updater = Updater(BOT_TOKEN, use_context=True)
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

if __name__ == '__main__':
    main()
