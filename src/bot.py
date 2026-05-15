"""Main Telegram bot entry point for Hindi voice resume builder."""

import asyncio
import logging
import os
import threading
from aiohttp import web

from dotenv import load_dotenv
from telegram import Update
from telegram.ext import (
    Application,
    CommandHandler,
    ContextTypes,
    MessageHandler,
    CallbackQueryHandler,
    filters,
)
from telegram import InlineKeyboardButton, InlineKeyboardMarkup

from src.conversation import (
    clear_state,
    get_current_question,
    get_state,
    is_complete,
    next_step,
    reset_state,
    save_answer,
    INITIAL_QUESTION,
    FINAL_MESSAGE,
    set_fresher_status,
    is_awaiting_fresher_selection,
    get_questions,
)
from src.database import get_user_resumes, save_resume, get_stats, get_all_resumes
from src.pdf_generator import generate_pdf, cleanup_files
from src.resume_builder import structure_resume_data
from src.transcriber import process_voice_file

# Load environment variables
load_dotenv()

# Configure logging
logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    level=logging.INFO,
)
logger = logging.getLogger(__name__)

# Get API keys
TELEGRAM_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
GROQ_API_KEY = os.getenv("GROQ_API_KEY")
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")
TEST_USER_ID = 8393898515  # Your test Telegram ID

if not TELEGRAM_TOKEN:
    raise ValueError("TELEGRAM_BOT_TOKEN not found in environment")

# Set API keys for other modules
if GROQ_API_KEY:
    os.environ["GROQ_API_KEY"] = GROQ_API_KEY
if GEMINI_API_KEY:
    os.environ["GEMINI_API_KEY"] = GEMINI_API_KEY


async def generate_resume(update: Update, context: ContextTypes.DEFAULT_TYPE, answers: dict, is_fresher: bool) -> None:
    """Generate and send resume PDF."""
    user_id = update.effective_user.id

    try:
        # Run synchronous Gemini call in executor to avoid blocking
        loop = asyncio.get_running_loop()
        structured_data = await loop.run_in_executor(
            None,
            lambda: structure_resume_data(answers, is_fresher)
        )

        # Send final message
        await update.message.reply_text(FINAL_MESSAGE)

        # Save to database
        resume_id = await loop.run_in_executor(None, lambda: save_resume(user_id, structured_data, is_fresher))
        logger.info(f"Resume {resume_id} saved for user {user_id}")

        pdf_path = generate_pdf(user_id, structured_data)

        # Send PDF to user
        with open(pdf_path, "rb") as pdf_file:
            await update.message.reply_document(
                document=pdf_file,
                filename=f"resume_{user_id}.pdf",
                caption=(
                    "🎉 Aapka resume taiyaar hai!\n"
                    "Isse download karein aur job apply karne mein use karein.\n"
                    "All the best! 👍"
                ),
            )

        # Clean up files
        cleanup_files(user_id)

        # Clear user state
        clear_state(user_id)

    except Exception as e:
        import traceback
        traceback.print_exc()
        await context.bot.send_message(
            chat_id=update.effective_chat.id,
            text="Kuch technical problem aayi. Thodi der baad /start karke dobara try karein."
        )
        clear_state(user_id)


async def start_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle /start command - show fresher/experienced selection."""
    user_id = update.effective_user.id
    reset_state(user_id)

    keyboard = [
        [InlineKeyboardButton("🎓 Fresher (Naya)", callback_data="fresher")],
        [InlineKeyboardButton("💼 Experience (Kaam Kiya Hai)", callback_data="experienced")],
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)

    await update.message.reply_text(INITIAL_QUESTION, reply_markup=reply_markup)


async def handle_callback(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle inline button callbacks for fresher/experienced selection."""
    query = update.callback_query
    await query.answer()

    user_id = update.effective_user.id
    callback_data = query.data

    if callback_data == "fresher":
        set_fresher_status(user_id, True)
        questions = get_questions(True)
        if questions:
            await query.edit_message_text(text=f"Aapne Fresher choose kiya. 🎓\n\n{questions[0]}")
    elif callback_data == "experienced":
        set_fresher_status(user_id, False)
        questions = get_questions(False)
        if questions:
            await query.edit_message_text(text=f"Aapne Experience choose kiya. 💼\n\n{questions[0]}")


async def cancel_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle /cancel command - cancel and restart."""
    user_id = update.effective_user.id
    clear_state(user_id)

    await update.message.reply_text(
        "Conversation cancelled.\n/start likhkar dobara shuru karein."
    )


async def history_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle /history command - show user's past resumes."""
    user_id = update.effective_user.id

    resumes = get_user_resumes(user_id)

    if not resumes:
        await update.message.reply_text(
            "Aapne abhi tak koi resume nahi banaya hai.\n"
            "/start karke apna pehla resume banein!"
        )
        return

    msg = f"Aapke {len(resumes)} resume(banaye hue) hain:\n\n"
    for i, r in enumerate(resumes, 1):
        date = r["created_at"][:10] if r["created_at"] else "Unknown"
        name = r["name"] or "Unknown"
        job = r["job_target"] or "Not specified"
        msg += f"{i}. {name} | {job} | {date}\n"

    await update.message.reply_text(msg)


async def stats_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle /stats command - show bot statistics (admin only)."""
    user_id = update.effective_user.id

    # Only allow test user to see stats
    if user_id != TEST_USER_ID:
        await update.message.reply_text("Ye command sirf admin ke liye hai.")
        return

    stats = get_stats()

    msg = f"📊 Bot Statistics:\n\n"
    msg += f"Total Resumes: {stats['total_resumes']}\n"
    msg += f"Unique Users: {stats['unique_users']}\n"

    await update.message.reply_text(msg)


async def export_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle /export command - export all resumes as text (admin only)."""
    user_id = update.effective_user.id

    # Only allow test user
    if user_id != TEST_USER_ID:
        await update.message.reply_text("Ye command sirf admin ke liye hai.")
        return

    resumes = get_all_resumes(limit=50)

    if not resumes:
        await update.message.reply_text("Abhi koi resume nahi hai.")
        return

    msg = f"📋 Recent {len(resumes)} Resumes:\n\n"

    for r in resumes[:10]:  # Show first 10
        date = r["created_at"][:10] if r["created_at"] else "Unknown"
        msg += f"--- {date} ---\n"
        msg += f"Name: {r['name']}\n"
        msg += f"City: {r['city']}\n"
        msg += f"Job: {r['job_target']}\n"
        msg += f"Phone: {r['phone']}\n\n"

    await update.message.reply_text(msg)


async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle text or voice messages."""
    user_id = update.effective_user.id
    state = get_state(user_id)

    # Check if user needs to select fresher/experienced first
    if is_awaiting_fresher_selection(user_id):
        await update.message.reply_text(
            "Pehle niche buttons mein se kisi ek option ko choose karein 👇"
        )
        return

    text = None

    # Check if it's a voice message
    if update.message.voice:
        try:
            text = await process_voice_file(context.bot, update.message.voice.file_id)
            logger.info(f"Transcribed voice for user {user_id}: {text}")
        except Exception as e:
            logger.error(f"Voice transcription failed: {e}")
            await update.message.reply_text(
                "Maafi chahta hoon, mujhe samajh nahi aaya. "
                "Kya aap dobara bol sakte hain?"
            )
            return

        if not text:
            await update.message.reply_text(
                "Maafi chahta hoon, mujhe samajh nahi aaya. "
                "Kya aap dobara bol sakte hain?"
            )
            return
    elif update.message.text:
        text = update.message.text.strip()
    else:
        # Unsupported content type
        try:
            await update.message.reply_text(
                "Kripya sirf voice note ya text mein jawab dein 🙏"
            )
        except Exception:
            pass
        return

    if not text:
        await update.message.reply_text(
            "Kripya kuch likhke ya bolke bhejein."
        )
        return

    current_step = state["step"]
    is_fresher = state.get("is_fresher")
    save_answer(user_id, current_step, text)

    # Check if conversation is complete
    if is_complete(current_step + 1, is_fresher):
        # Call async generate_resume function
        await generate_resume(update, context, state["answers"], bool(is_fresher))

    else:
        # Move to next question
        next_step(user_id)
        next_question = get_current_question(state["step"], is_fresher)

        if next_question:
            await update.message.reply_text(next_question)
        else:
            # No more questions - conversation complete!
            await generate_resume(update, context, state["answers"], bool(is_fresher))


async def error_handler(update: object, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle all unhandled errors gracefully."""
    logger.error(f"Exception while handling an update: {context.error}")


async def health_handler(request):
    """Health check endpoint that returns 200 OK."""
    return web.Response(text="ok")


async def start_web_server():
    """Start aiohttp web server for health checks."""
    app = web.Application()
    app.router.add_get("/health", health_handler)
    runner = web.AppRunner(app)
    await runner.setup()
    port = int(os.getenv("PORT", 8080))
    site = web.TCPSite(runner, "0.0.0.0", port)
    await site.start()
    logger.info(f"Health check server running on port {port}")


async def main():
    """Start the bot and health check server."""
    # Start health check server in a separate thread to avoid event loop conflict
    def run_health_server():
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        loop.run_until_complete(start_web_server())
        loop.run_forever()  # Keep the loop running
    
    health_thread = threading.Thread(target=run_health_server, daemon=True)
    health_thread.start()
    
    # Give health server time to start
    await asyncio.sleep(1)
    
    app = Application.builder().token(TELEGRAM_TOKEN).build()
    
    # Add error handler
    app.add_error_handler(error_handler)
    
    # Add handlers
    app.add_handler(CommandHandler("start", start_command))
    app.add_handler(CommandHandler("cancel", cancel_command))
    app.add_handler(CommandHandler("history", history_command))
    app.add_handler(CommandHandler("stats", stats_command))
    app.add_handler(CommandHandler("export", export_command))
    app.add_handler(CallbackQueryHandler(handle_callback))
    app.add_handler(MessageHandler(filters.VOICE, handle_message))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))
    
    logger.info("Resume bot starting...")
    await app.run_polling(allowed_updates=Update.ALL_TYPES)


if __name__ == "__main__":
    asyncio.run(main())