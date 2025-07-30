# Standard library
import os, time, re, logging, email, imaplib
from datetime import datetime, timedelta
from email.header import decode_header

# Third-party
import requests
from dotenv import load_dotenv
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from webdriver_manager.chrome import ChromeDriverManager
from telegram import Bot, ParseMode
from telegram.utils.request import Request
from telegram.ext import Updater, CommandHandler, MessageHandler, Filters

logging.basicConfig(
    format='%(asctime)s - %(levelname)s - %(message)s',
    level=logging.INFO
)

load_dotenv()

# Bot & Admin setup
request = Request(con_pool_size=8, read_timeout=15)
TOKEN = os.getenv("BOT_TOKEN")
ADMIN_ID = int(os.getenv("ADMIN_ID"))

# Gmail credentials
GMAIL_ACCOUNTS = [
    (os.getenv("GMAIL_1_EMAIL"), os.getenv("GMAIL_1_PASS")),
    (os.getenv("GMAIL_2_EMAIL"), os.getenv("GMAIL_2_PASS")),
    (os.getenv("GMAIL_3_EMAIL"), os.getenv("GMAIL_3_PASS")),
    (os.getenv("GMAIL_4_EMAIL"), os.getenv("GMAIL_4_PASS")),
]

APPROVED_USERS_FILE = "approved_users.txt"

EMAIL_REGEX = re.compile(r"[^@]+@[^@]+\.[^@]+")
def is_valid_email(email):
    return EMAIL_REGEX.match(email)

def log_command(user, command_name, email=None):
    from telegram import Bot
    username = user.username or f"{user.first_name} {user.last_name or ''}".strip()
    log_msg = f"Command {command_name} used by {username} (ID: {user.id})"
    if email:
        log_msg += f" | Target Email: {email}"
    logging.info(log_msg)

    # Send to admin via Telegram
    try:
        Bot(token=TOKEN).send_message(
            chat_id=ADMIN_ID,
            text=log_msg
        )
    except Exception as e:
        logging.error(f"Failed to send admin log: {e}")

def load_approved_users():
    try:
        with open(APPROVED_USERS_FILE, "r") as f:
            lines = f.readlines()
        return {line.split(",")[0]: float(line.strip().split(",")[1]) for line in lines}
    except:
        return {}

def save_approved_users(users):
    with open(APPROVED_USERS_FILE, "w") as f:
        for uid, ts in users.items():
            f.write(f"{uid},{ts}\n")

approved_users = load_approved_users()

def is_user_approved(user_id):
    users = load_approved_users()  # Always reload from file
    expiry = users.get(str(user_id))
    if not expiry:
        return False
    if time.time() > expiry:
        del users[str(user_id)]
        save_approved_users(users)
        return False
    return True

def approve_user(update, context):
    if update.message.chat_id != ADMIN_ID:
        update.message.reply_text("⛔ You are not authorized to use this command.")
        return

    try:
        uid = str(context.args[0])
        approved_users[uid] = time.time() + 7 * 86400  # 7 days
        save_approved_users(approved_users)

        context.bot.send_message(
            chat_id=int(uid),
            text=(
                "💋 *Access Approved*\n"
                "Welcome to @ic4in BOT!\n"
                "Use any command below:\n"
                "⪩ `/sicode` <email>\n"
                "⪩ `/tcode` <email>\n"
                "⪩ `/reset` <email>\n"
                "⪩ `/rslink` <email>\n"
                "⪩ `/hlink` <email>"
            ),
            parse_mode='Markdown'
        )

        update.message.reply_text(f"✅ Approved user {uid}")

    except (IndexError, ValueError):
        update.message.reply_text("❌ Usage: /approve <user_id>")
    except Exception as e:
        update.message.reply_text("❌ Failed to approve user.")
        print(f"Error in /approve: {e}")

def remove_user(update, context):
    if update.message.chat_id != ADMIN_ID:
        return
    try:
        uid = str(context.args[0])
        if uid in approved_users:
            del approved_users[uid]
            save_approved_users(approved_users)
            update.message.reply_text(f"❌ Removed user {uid}")
        else:
            update.message.reply_text("User not found.")
    except:
        update.message.reply_text("❌ Failed to remove user.")

def start(update, context):
    user = update.message.from_user
    uid = user.id

    if not is_user_approved(uid):
        context.bot.send_message(
            chat_id=uid,
            text="💋 *Waiting for admin approval…*",
            parse_mode=ParseMode.MARKDOWN
        )
        context.bot.send_message(
            chat_id=ADMIN_ID,
            text=f"💄 *Approval Request*\n"
                 f"User: `{user.full_name}`\n"
                 f"ID: `{uid}`\n\n"
                 f"To approve, send:\n`/approve {uid}`",
            parse_mode=ParseMode.MARKDOWN
        )
    else:
        context.bot.send_message(
            chat_id=uid,
            text="💋 *welcome to @ic4in BOT!*\nUse any command below:\n"
                 "⪩ `/sicode` <email>\n"
                 "⪩ `/tcode` <email>\n"
                 "⪩ `/reset` <email>\n"
                 "⪩ `/rslink` <email>\n"
                 "⪩ `/hlink` <email>\n"
                  "*Before you send commands, make sure you have sent it in Netflix.*",
            parse_mode=ParseMode.MARKDOWN
        )

# --------------- GMAIL FETCH FUNCTION ---------------

def fetch_latest_matching_email(target_email, subject_keyword):
    now = datetime.utcnow()
    cutoff_time = now - timedelta(minutes=15)

    for email_user, email_pass in GMAIL_ACCOUNTS:
        try:
            imap = imaplib.IMAP4_SSL("imap.gmail.com")
            imap.login(email_user, email_pass)
            imap.select("inbox")

            # Only search for the SUBJECT to optimize speed
            result, data = imap.search(None, 'SUBJECT "{}"'.format(subject_keyword))

            if result == "OK":
                ids = data[0].split()
                ids.reverse()  # Most recent first

                for mail_id in ids[:10]:  # only check the 10 latest emails
                    res, msg_data = imap.fetch(mail_id, "(RFC822)")
                    if res != "OK": continue

                    raw_email = msg_data[0][1]
                    msg = email.message_from_bytes(raw_email)

                    # Match "To" field against the target email
                    to_header = msg.get("To", "")
                    if target_email.lower() not in to_header.lower():
                        continue

                    # Check if the email was received within 1 minute
                    date_tuple = email.utils.parsedate_tz(msg.get("Date"))
                    if date_tuple:
                        local_date = datetime.fromtimestamp(email.utils.mktime_tz(date_tuple))
                        if local_date < cutoff_time:
                            continue

                    # Get subject
                    subject, encoding = decode_header(msg.get("Subject"))[0]
                    if isinstance(subject, bytes):
                        subject = subject.decode(encoding or "utf-8")

                    # Get body
                    body = ""
                    if msg.is_multipart():
                        for part in msg.walk():
                            content_type = part.get_content_type()
                            if content_type == "text/plain" and not part.get('Content-Disposition'):
                                body = part.get_payload(decode=True).decode(errors="ignore")
                                break
                    else:
                        body = msg.get_payload(decode=True).decode(errors="ignore")

                    imap.logout()
                    return subject, body

            imap.logout()
        except Exception as e:
            print(f"Error reading {email_user}: {e}")

    return None, None

# --------------- COMMAND HANDLERS ---------------

def sicode(update, context):
    if not is_user_approved(update.message.chat_id):
        return
    if len(context.args) != 1:
        update.message.reply_text("Usage: /sicode email@example.com")
        return
    target_email = context.args[0]
    log_command(update.effective_user, "/sicode", target_email)

    email_arg = context.args[0]
    if not is_valid_email(email_arg):
        return update.message.reply_text("⛔ Invalid email format.")

    # ✅ Respond right away
    update.message.reply_text("⏳ Fetching, please wait...")

    subject, body = fetch_latest_matching_email(context.args[0], "Your sign-in code")
    if body:
        import re
        match = re.search(r'\b\d{4}\b', body)
        if match:
            code = match.group()
            msg = f"💋 *sign-in code*\n✉️ {context.args[0]}\n🔐 code: {code}\n🕐 valid: 15 mins"
            return update.message.reply_text(msg, parse_mode=ParseMode.MARKDOWN)
    update.message.reply_text("💋 No matching email found.")

def tcode(update, context):
    if not is_user_approved(update.message.chat_id):
        return
    if len(context.args) != 1:
        update.message.reply_text("Usage: /tcode email@example.com")
        return
    target_email = context.args[0]
    log_command(update.effective_user, "/tcode", target_email)

    if len(context.args) != 1:
        update.message.reply_text("Usage: /tcode email@example.com")
        return

    email_arg = context.args[0]
    if not is_valid_email(email_arg):
        return update.message.reply_text("⛔ Invalid email format.")

    target_email = context.args[0]
    update.message.reply_text("⏳ Fetching, please wait...")

    subject, body = fetch_latest_matching_email(target_email, "temporary access")

    if body:
        import re

        link_match = re.search(r"https://www\.netflix\.com/account/travel/verify[^\s)>\]\"']+", body)
        if link_match:
            link = link_match.group(0)

            try:
                # Setup headless Chrome
                chrome_options = Options()
                chrome_options.add_argument("--headless")
                chrome_options.add_argument("--disable-gpu")
                chrome_options.add_argument("--no-sandbox")

                driver = webdriver.Chrome(ChromeDriverManager().install(), options=chrome_options)
                driver.get(link)

                time.sleep(5)  # Wait for JS to load

                page_source = driver.page_source
                driver.quit()

                code_match = re.search(r'\b\d{4}\b', page_source)
                if code_match:
                    code = code_match.group()
                    msg = f"💋 *temporary code*\n✉️ {target_email}\n🔐 code: `{code}`\n🕐 valid: 15 mins"
                    return update.message.reply_text(msg, parse_mode=ParseMode.MARKDOWN)

            except Exception as e:
                update.message.reply_text(f"⚠️ Error fetching code: {e}")
                return

    update.message.reply_text(
        f"⛔ No matching email found.",
        parse_mode=ParseMode.MARKDOWN
    )

def reset(update, context):
    if not is_user_approved(update.message.chat_id):
        return
    if len(context.args) != 1:
        update.message.reply_text("Usage: /reset email@example.com")
        return
    target_email = context.args[0]
    log_command(update.effective_user, "/reset", target_email)

    email_arg = context.args[0]
    if not is_valid_email(email_arg):
        return update.message.reply_text("⛔ Invalid email format.")

    update.message.reply_text("⏳ Fetching, please wait...")

    subject, body = fetch_latest_matching_email(context.args[0], "Complete your password reset request")
    if body:
        # This ensures we extract a proper full reset URL without extra characters
        match = re.search(r'(https://www\.netflix\.com/password\?[^)\]\s]+)', body)
        if match:
            link = match.group().strip(").]")  # Clean any trailing ), ]
            msg = (
                f"💋 *reset password link*\n"
                f"✉️ {context.args[0]}\n"
                f"🔗 [reset link]({link})\n"
                f"🕐 valid: 24 hours\n"
            )
            return update.message.reply_text(msg, parse_mode=ParseMode.MARKDOWN)

    update.message.reply_text("💋 No matching email found.")

def rslink(update, context):
    if not is_user_approved(update.message.chat_id):
        return
    if len(context.args) != 1:
        update.message.reply_text("Usage: /rslink email@example.com")
        return
    target_email = context.args[0]
    log_command(update.effective_user, "/rslink", target_email)

    if len(context.args) != 1:
        update.message.reply_text("Usage: /rslink email@example.com")
        return

    email_arg = context.args[0]
    if not is_valid_email(email_arg):
        return update.message.reply_text("⛔ Invalid email format.")
    target_email = context.args[0]
    update.message.reply_text("⏳ Fetching approval link...")

    # Look for email with this subject
    subject, body = fetch_latest_matching_email(target_email, "Netflix: new sign-in request")

    if subject and body:
        import re
        match = re.search(r'https:\/\/www\.netflix\.com\/ilum\?code=[\w\-]+', body)
        if match:
            link = match.group()
            msg = (
                f"💋 *approval link*\n"
                f"✉️ {target_email}\n"
                f"🔗 [approve now]({link})\n"
                f"🕐 valid: ~15 mins"
            )
            return update.message.reply_text(msg, parse_mode=ParseMode.MARKDOWN)
    
    # Fallback if no link
    update.message.reply_text("⛔ No matching email found.")

def hlink(update, context):
    if not is_user_approved(update.message.chat_id):
        return
    if len(context.args) != 1:
        update.message.reply_text("Usage: /hlink email@example.com")
        return
    target_email = context.args[0]
    log_command(update.effective_user, "/hlink", target_email)

    if len(context.args) != 1:
        update.message.reply_text("Usage: /hlink email@example.com")
        return

    email_arg = context.args[0]
    if not is_valid_email(email_arg):
        return update.message.reply_text("⛔ Invalid email format.")

    target_email = context.args[0]
    update.message.reply_text("⏳ Fetching, please wait...")

    subject, body = fetch_latest_matching_email(target_email, "How to Update your Netflix Household")

    if subject and body:
        # Extract the first Netflix household update link
        match = re.search(r"https://www\.netflix\.com/account/update-primary-location[^\s)\]>\"']+", body)
        if match:
            update.message.reply_text(
                f"💋 *household update link*\n"
                f"`mail:` {target_email}\n"
                f"🛠️ update: [click here]({match.group(0)})\n"
                f"valid: 15 mins",
                parse_mode=ParseMode.MARKDOWN,
                disable_web_page_preview=True
            )
            return

    update.message.reply_text(
        f"💋 *No Match Found*\n"
        f"`mail:` {target_email}\n"
        f"⛔ No matching email found.",
        parse_mode=ParseMode.MARKDOWN
    )

def unknown(update, context):
    update.message.reply_text("⛔ Unknown command.")

# ---------------- RUN BOT ----------------

def main():
    updater = Updater(TOKEN, use_context=True)
    dp = updater.dispatcher

    dp.add_handler(CommandHandler("start", start))
    dp.add_handler(CommandHandler("approve", approve_user, pass_args=True))
    dp.add_handler(CommandHandler("remove", remove_user, pass_args=True))
    dp.add_handler(CommandHandler("sicode", sicode, pass_args=True))
    dp.add_handler(CommandHandler("tcode", tcode, pass_args=True))
    dp.add_handler(CommandHandler("reset", reset, pass_args=True))
    dp.add_handler(CommandHandler("rslink", rslink, pass_args=True))
    dp.add_handler(CommandHandler("hlink", hlink, pass_args=True))
    dp.add_handler(MessageHandler(Filters.command, unknown))

    updater.start_polling()
    updater.idle()

if __name__ == '__main__':
    main()