"""
بوت تيليجرام مدمج مع Google Gemini (مجاني بالكامل) - متوافق مع استضافة Render
"""

import os
import logging
import threading
from flask import Flask
from telegram import Update
from telegram.ext import (
    ApplicationBuilder,
    ContextTypes,
    CommandHandler,
    MessageHandler,
    filters,
)
import google.generativeai as genai

TELEGRAM_BOT_TOKEN = os.environ.get("TELEGRAM_BOT_TOKEN")
GEMINI_API_KEY = os.environ.get("GEMINI_API_KEY")

if not TELEGRAM_BOT_TOKEN or not GEMINI_API_KEY:
    raise RuntimeError(
        "يجب ضبط المتغيرين TELEGRAM_BOT_TOKEN و GEMINI_API_KEY من إعدادات Render قبل التشغيل."
    )

genai.configure(api_key=GEMINI_API_KEY)
GEMINI_MODEL = "gemini-2.5-flash"

SYSTEM_PROMPT = (
    "أنت مساعد ذكي داخل بوت تيليجرام. "
    "رد بإيجاز ووضوح، وباللغة نفسها التي يكتب بها المستخدم."
)

user_histories = {}
MAX_HISTORY_MESSAGES = 20

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

model = genai.GenerativeModel(
    model_name=GEMINI_MODEL,
    system_instruction=SYSTEM_PROMPT,
)


def ask_gemini(user_id, user_message):
    history = user_histories.setdefault(user_id, [])
    chat = model.start_chat(history=history[-MAX_HISTORY_MESSAGES:])
    response = chat.send_message(user_message)

    history.append({"role": "user", "parts": [user_message]})
    history.append({"role": "model", "parts": [response.text]})
    user_histories[user_id] = history

    return response.text


async def start_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "أهلاً! أنا بوت مدعوم بالذكاء الاصطناعي. اكتب أي رسالة وسأرد عليك."
    )


async def reset_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    user_histories.pop(user_id, None)
    await update.message.reply_text("تم مسح سجل المحادثة. يمكنك البدء من جديد.")


async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    user_message = update.message.text

    await context.bot.send_chat_action(chat_id=update.effective_chat.id, action="typing")

    try:
        reply = ask_gemini(user_id, user_message)
    except Exception:
        logger.exception("خطأ أثناء استدعاء Gemini API")
        reply = "حدث خطأ أثناء معالجة طلبك، حاول مرة أخرى بعد قليل."

    await update.message.reply_text(reply)


web_app = Flask(__name__)


@web_app.route("/")
def health_check():
    return "Bot is running."


def run_web_server():
    port = int(os.environ.get("PORT", 10000))
    web_app.run(host="0.0.0.0", port=port)


def main():
    threading.Thread(target=run_web_server, daemon=True).start()

    app = ApplicationBuilder().token(TELEGRAM_BOT_TOKEN).build()
    app.add_handler(CommandHandler("start", start_command))
    app.add_handler(CommandHandler("reset", reset_command))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))

    logger.info("البوت يعمل الآن...")
    app.run_polling()


if __name__ == "__main__":
    main()
