"""
بوت تيليجرام مدمج مع Groq (مجاني بالكامل) - متوافق مع استضافة Render
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
from groq import Groq

TELEGRAM_BOT_TOKEN = os.environ.get("TELEGRAM_BOT_TOKEN")
GROQ_API_KEY = os.environ.get("GROQ_API_KEY")

if not TELEGRAM_BOT_TOKEN or not GROQ_API_KEY:
    raise RuntimeError(
        "يجب ضبط المتغيرين TELEGRAM_BOT_TOKEN و GROQ_API_KEY من إعدادات Render قبل التشغيل."
    )

client = Groq(api_key=GROQ_API_KEY)
GROQ_MODEL = "llama-3.3-70b-versatile"

SYSTEM_PROMPT = (
    "أنت مساعد ذكي داخل بوت تيليجرام. "
    "رد بإيجاز ووضوح، وباللغة نفسها التي يكتب بها المستخدم."
)

user_histories = {}
MAX_HISTORY_MESSAGES = 20

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def ask_groq(user_id, user_message):
    history = user_histories.setdefault(user_id, [])
    history.append({"role": "user", "content": user_message})

    messages = [{"role": "system", "content": SYSTEM_PROMPT}] + history[-MAX_HISTORY_MESSAGES:]

    response = client.chat.completions.create(
        model=GROQ_MODEL,
        messages=messages,
        max_tokens=1024,
    )

    reply_text = response.choices[0].message.content

    history.append({"role": "assistant", "content": reply_text})
    user_histories[user_id] = history

    return reply_text


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
        reply = ask_groq(user_id, user_message)
    except Exception:
        logger.exception("خطأ أثناء استدعاء Groq API")
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
