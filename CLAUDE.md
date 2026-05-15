# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

A Telegram bot that helps blue collar workers in India create professional resumes through voice-based conversations in Hindi. The bot collects user responses via voice notes or text, transcribes Hindi audio using Groq Whisper, structures data with Groq LLM (llama-3.3-70b-versatile), and generates a professional PDF resume.

## Commands

```bash
# Install dependencies
uv sync

# Run the bot
uv run src/bot.py
```

Required system dependencies (not in pyproject.toml):
- **ffmpeg** - for audio conversion (Telegram sends .ogg, need .mp3 for Whisper)
- **libreoffice** - for converting .docx to PDF in pdf_generator.py

## Environment Variables

Create `.env` from `.env.example`:
- `TELEGRAM_BOT_TOKEN` - from @BotFather
- `GROQ_API_KEY` - for both Hindi speech-to-text (Whisper) and resume data structuring

## Architecture

```
src/bot.py              # Main entry: Telegram handlers, message routing
src/conversation.py     # State machine: fresher/experienced questions, in-memory state
src/transcriber.py      # Voice processing: .ogg → .mp3 → Hindi text (Groq)
src/resume_builder.py   # Data structuring: raw answers → JSON (Groq LLM, different prompts for fresher/experienced)
src/pdf_generator.py   # PDF creation: fills template, converts to PDF
src/database.py         # SQLite storage for completed resumes
src/template/resume_template.docx  # Document template with placeholders
```

### Data Flow
1. User sends `/start` → bot shows inline buttons: "Fresher" or "Experience"
2. User clicks button → set `is_fresher` flag, show first question based on selection
3. Fresher: 8 questions (no work experience). Experienced: 10 questions
4. Each answer stored in memory (conversation.py)
5. Voice messages downloaded and transcribed via Groq Whisper
5. After last answer, Groq LLM structures data into JSON (different prompts for fresher vs experienced)
7. PDF generated from docx template and sent to user
8. Resume saved to SQLite database (with `is_fresher` flag)

### Key Design Patterns
- **Inline keyboard buttons** for fresher/experienced selection (not free-form text)
- **Dual question sets**: Fresher (8 questions) vs Experienced (10 questions)
- **State machine** in conversation.py tracks user progress and `is_fresher` flag
- **Async/sync bridge** in bot.py: Groq calls are synchronous, run in executor
- **Template substitution** in pdf_generator.py: placeholders like `{{FULL_NAME}}` replaced

## Bot Commands

- `/start` - Begin new resume conversation
- `/cancel` - Cancel current conversation
- `/history` - View past resumes for your user ID
- `/stats` - Admin: view total resumes and unique users (test user only)
- `/export` - Admin: export recent resumes (test user only)

## Testing

Test locally by messaging your bot on Telegram. The test user ID (8393898515) has admin privileges for `/stats` and `/export` commands.

## Database

SQLite stored at `data/resumes.db`. Tables: resumes (user_id, name, city, job_target, phone, work_bullets, skills, etc.)

## Deployment

### Railway (Recommended - Free Tier)
1. Push code to GitHub
2. Create Web Service on [railway.app](https://railway.app)
3. Settings:
   - Build Command: `pip install uv && uv sync`
   - Start Command: `uv run src/bot.py`
4. Add Environment Variables:
   - `TELEGRAM_BOT_TOKEN`
   - `GROQ_API_KEY`
5. Deploy - bot will auto-redeploy on GitHub push

### Docker
A `Dockerfile` is included for containerized deployment. Build:
```bash
docker build -t resume-bot .
docker run -e TELEGRAM_BOT_TOKEN=xxx -e GROQ_API_KEY=xxx resume-bot
```

## Updating After Deployment

1. Make changes locally
2. Push to GitHub
3. Railway auto-deploys on push