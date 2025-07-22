import os
import logging
from dotenv import load_dotenv
from telegram import Update, ParseMode
from telegram.ext import Updater, CommandHandler, CallbackContext
from datetime import datetime, timedelta

# Load environment variables
load_dotenv()
TOKEN = os.getenv("TOKEN")
ADMIN_ID = int(os.getenv("ADMIN_ID"))

# User approvals with timestamp
approved_users = {}  # user_id: approval_time

logging.basicConfig(level=logging.INFO)

# Decorator to check access
def check_access(func):
    def wrapper(update: Update, context: CallbackContext):
        user_id = update.effective_user.id
        now = datetime.utcnow()

        # Check if approved
        if user_id not in approved_users:
            return update.message.reply_text("❌ You’re not approved.")
        
        # Check if expired
        approved_time = approved_users[user_id]
        if now - approved_time > timedelta(days=7):
            del approved_users[user_id]
            update.message.reply_text("⏳ Your access expired. Please request approval again.")
            context.bot.send_message(
                chat_id=ADMIN_ID,
                text=f"🔄 User @{update.effective_user.username or 'NoUsername'} (ID: {user_id}) access expired.",
            )
            return

        return func(update, context)
    return wrapper

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

def approve(update: Update, context: CallbackContext):
    if update.effective_user.id != ADMIN_ID:
        return update.message.reply_text("⛔ You’re not allowed to approve.")
    try:
        user_id = int(context.args[0])
        approved_users[user_id] = datetime.utcnow()

        try:
            context.bot.send_message(chat_id=user_id, text="✅ You’ve been approved for 7 days!")
        except Exception as e:
            update.message.reply_text(f"⚠️ Failed to notify user: {e}")

        update.message.reply_text(f"✅ User {user_id} approved for 7 days.")
    except Exception as e:
        update.message.reply_text(f"⚠️ Usage: /approve <user_id>\nError: {e}")

def remove(update: Update, context: CallbackContext):
    if update.effective_user.id != ADMIN_ID:
        return update.message.reply_text("⛔ You’re not allowed to remove users.")
    try:
        user_id = int(context.args[0])
        if user_id in approved_users:
            del approved_users[user_id]
            context.bot.send_message(chat_id=user_id, text="🚫 Your access has been revoked.")
            update.message.reply_text(f"🚫 User {user_id} removed.")
        else:
            update.message.reply_text("⚠️ That user is not approved.")
    except:
        update.message.reply_text("⚠️ Usage: /remove <user_id>")

# Commands with email argument
@check_access
def sicode(update: Update, context: CallbackContext):
    if not context.args:
        return update.message.reply_text("❗ Usage: /sicode your@email.com")
    email = context.args[0]
    update.message.reply_text(f"🔐 Sign-in code for *{email}*: `1234` (Sample)", parse_mode=ParseMode.MARKDOWN)

@check_access
def tcode(update: Update, context: CallbackContext):
    if not context.args:
        return update.message.reply_text("❗ Usage: /tcode your@email.com")
    email = context.args[0]
    update.message.reply_text(f"📩 Tempo code for *{email}*: `4321` (Sample)", parse_mode=ParseMode.MARKDOWN)

@check_access
def reset(update: Update, context: CallbackContext):
    if not context.args:
        return update.message.reply_text("❗ Usage: /reset your@email.com")
    email = context.args[0]
    update.message.reply_text(f"🔁 [Reset password link]({email}) sent.", parse_mode=ParseMode.MARKDOWN)

@check_access
def hlink(update: Update, context: CallbackContext):
    if not context.args:
        return update.message.reply_text("❗ Usage: /hlink your@email.com")
    email = context.args[0]
    update.message.reply_text(f"🏠 [Household link]({email}) sent.", parse_mode=ParseMode.MARKDOWN)

@check_access
def rslink(update: Update, context: CallbackContext):
    if not context.args:
        return update.message.reply_text("❗ Usage: /rslink your@email.com")
    email = context.args[0]
    update.message.reply_text(f"📨 [Request sign-in link]({email}) sent.", parse_mode=ParseMode.MARKDOWN)

# Main setup
def main():
    updater = Updater(TOKEN, use_context=True)
    dp = updater.dispatcher

    dp.add_handler(CommandHandler("start", start))
    dp.add_handler(CommandHandler("approve", approve))
    dp.add_handler(CommandHandler("remove", remove))
    dp.add_handler(CommandHandler("sicode", sicode))
    dp.add_handler(CommandHandler("tcode", tcode))
    dp.add_handler(CommandHandler("reset", reset))
    dp.add_handler(CommandHandler("hlink", hlink))
    dp.add_handler(CommandHandler("rslink", rslink))

    updater.start_polling()
    print("🤖 Bot is running...")
    updater.idle()

if __name__ == "__main__":
    main()
