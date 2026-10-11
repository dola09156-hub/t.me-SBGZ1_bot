import os
import random
import logging
from datetime import time as dtime

from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    Application, CommandHandler, CallbackQueryHandler,
    ContextTypes, MessageHandler, filters,
)

logging.basicConfig(level=logging.INFO)
log = logging.getLogger(__name__)

TOKEN = os.environ["BOT_TOKEN"]

STUDY_TIPS = [
    "Study in short blocks of 25 minutes, then take a 5 minute break. Short bursts keep your focus sharp.",
    "Test yourself instead of rereading. Recalling information from memory is one of the best ways to learn.",
    "Teach what you learned to someone else, or explain it out loud. If you can explain it simply, you understand it.",
    "Space your revision over several days instead of cramming. Spaced review helps memory last.",
    "Start with the hardest subject when your energy is highest.",
    "Put your phone in another room while studying. Even a nearby phone pulls attention away.",
    "Write down what you will study before you begin. A clear goal makes starting easier.",
    "Use active notes: write questions in the margin and answer them later.",
    "Sleep is part of studying. Your brain stores what you learned while you rest.",
    "Break big topics into small chunks. Finishing small pieces builds momentum.",
    "Review your notes within 24 hours of learning something new.",
    "Study in the same place each day so your mind links that space with focus.",
]

PRODUCTIVITY_TIPS = [
    "Pick your top 3 tasks each morning. Finish those first and the day already feels productive.",
    "If a task takes less than 2 minutes, do it right away instead of adding it to your list.",
    "Do one thing at a time. Switching between tasks costs more time than it seems.",
    "Prepare tomorrow's to-do list tonight so you can start without thinking.",
    "Start before you feel ready. Motivation often comes after you begin.",
    "Say no to things that do not matter. Protecting your time is a skill.",
    "Take real breaks: stretch, drink water, or step outside for a few minutes.",
    "Batch similar tasks together, like replying to messages at set times only.",
    "Clear your desk before you start. A tidy space helps a tidy mind.",
    "Celebrate small wins. They keep you going on long projects.",
]

QUOTES = [
    "Small steps every day add up to big results.",
    "You do not have to be perfect, just consistent.",
    "Focus on progress, not perfection.",
    "The best time to start was yesterday. The next best time is now.",
    "Discipline is doing it even when you do not feel like it.",
]

MENU = InlineKeyboardMarkup([
    [InlineKeyboardButton("📚 Study Tip", callback_data="study"),
     InlineKeyboardButton("⚡ Productivity Tip", callback_data="prod")],
    [InlineKeyboardButton("⏱ Focus Timer (25 min)", callback_data="timer"),
     InlineKeyboardButton("✨ Quote", callback_data="quote")],
    [InlineKeyboardButton("🔔 Daily Tip", callback_data="subscribe")],
])


def study_text():
    return f"📚 *Study tip*\n\n{random.choice(STUDY_TIPS)}"


def prod_text():
    return f"⚡ *Productivity tip*\n\n{random.choice(PRODUCTIVITY_TIPS)}"


def quote_text():
    return f"✨ {random.choice(QUOTES)}"


async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    name = update.effective_user.first_name or "friend"
    await update.message.reply_text(
        f"👋 Hi {name}! I help you study smarter and get more done.\n\n"
        "Get quick tips, start a focus timer, or subscribe to one daily tip.\n\n"
        "Choose an option:",
        reply_markup=MENU,
    )


async def help_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "Commands:\n"
        "/start - Main menu\n"
        "/study - Study tip\n"
        "/productivity - Productivity tip\n"
        "/focus - Start a 25 minute focus timer\n"
        "/cancel - Cancel your timer\n"
        "/quote - Motivational quote\n"
        "/subscribe - Get one tip every day\n"
        "/unsubscribe - Stop daily tips\n"
        "/about - About this bot"
    )


async def about(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "This bot shares free study and productivity tips and includes a "
        "simple focus timer. It is made for students and anyone who wants "
        "to build better habits."
    )


async def study_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(study_text(), parse_mode="Markdown", reply_markup=MENU)


async def prod_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(prod_text(), parse_mode="Markdown", reply_markup=MENU)


async def quote_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(quote_text(), reply_markup=MENU)


# ---------- Focus timer ----------
FOCUS_MINUTES = 25
BREAK_MINUTES = 5


async def focus_done(context: ContextTypes.DEFAULT_TYPE):
    chat_id = context.job.chat_id
    await context.bot.send_message(
        chat_id,
        f"✅ Great work! Your {FOCUS_MINUTES} minute session is over.\n"
        f"Take a {BREAK_MINUTES} minute break. Stretch and drink some water.",
        reply_markup=MENU,
    )


async def start_timer(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat_id = update.effective_chat.id
    for job in context.job_queue.get_jobs_by_name(f"focus_{chat_id}"):
        job.schedule_removal()
    context.job_queue.run_once(
        focus_done, FOCUS_MINUTES * 60, chat_id=chat_id, name=f"focus_{chat_id}"
    )
    await update.effective_message.reply_text(
        f"⏱ Focus timer started for {FOCUS_MINUTES} minutes.\n"
        "Put your phone away and work on one task. I will message you when time is up.\n\n"
        "Use /cancel to stop."
    )


async def cancel_timer(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat_id = update.effective_chat.id
    jobs = context.job_queue.get_jobs_by_name(f"focus_{chat_id}")
    if not jobs:
        await update.message.reply_text("You have no active timer.")
        return
    for job in jobs:
        job.schedule_removal()
    await update.message.reply_text("Timer cancelled.")


# ---------- Daily tip subscriptions (in memory; resets on redeploy) ----------
SUBSCRIBERS = set()


async def subscribe(update: Update, context: ContextTypes.DEFAULT_TYPE):
    SUBSCRIBERS.add(update.effective_chat.id)
    await update.effective_message.reply_text(
        "🔔 Subscribed! You will get one tip every day. Use /unsubscribe to stop."
    )


async def unsubscribe(update: Update, context: ContextTypes.DEFAULT_TYPE):
    SUBSCRIBERS.discard(update.effective_chat.id)
    await update.message.reply_text("🔕 Unsubscribed. Come back any time with /subscribe.")


async def daily_job(context: ContextTypes.DEFAULT_TYPE):
    for chat_id in list(SUBSCRIBERS):
        try:
            text = study_text() if random.random() < 0.5 else prod_text()
            await context.bot.send_message(chat_id, text, parse_mode="Markdown")
        except Exception as e:
            log.warning("Could not send to %s: %s", chat_id, e)
            SUBSCRIBERS.discard(chat_id)


async def button(update: Update, context: ContextTypes.DEFAULT_TYPE):
    q = update.callback_query
    await q.answer()
    if q.data == "study":
        await q.message.reply_text(study_text(), parse_mode="Markdown", reply_markup=MENU)
    elif q.data == "prod":
        await q.message.reply_text(prod_text(), parse_mode="Markdown", reply_markup=MENU)
    elif q.data == "quote":
        await q.message.reply_text(quote_text(), reply_markup=MENU)
    elif q.data == "timer":
        await start_timer(update, context)
    elif q.data == "subscribe":
        await subscribe(update, context)


async def fallback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("Use the buttons below or type /help.", reply_markup=MENU)


def main():
    app = Application.builder().token(TOKEN).build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("help", help_cmd))
    app.add_handler(CommandHandler("about", about))
    app.add_handler(CommandHandler("study", study_cmd))
    app.add_handler(CommandHandler("productivity", prod_cmd))
    app.add_handler(CommandHandler("quote", quote_cmd))
    app.add_handler(CommandHandler("focus", start_timer))
    app.add_handler(CommandHandler("cancel", cancel_timer))
    app.add_handler(CommandHandler("subscribe", subscribe))
    app.add_handler(CommandHandler("unsubscribe", unsubscribe))
    app.add_handler(CallbackQueryHandler(button))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, fallback))

    # Daily tip at 08:00 UTC
    app.job_queue.run_daily(daily_job, time=dtime(hour=8, minute=0))

    log.info("Bot started")
    app.run_polling()


if __name__ == "__main__":
    main()
