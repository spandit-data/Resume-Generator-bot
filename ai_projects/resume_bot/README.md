# Resume Bot - Hindi Voice Resume Builder

A Telegram bot that helps blue collar workers in India create professional resumes through voice-based conversations in Hindi.

## Features

- Voice note support (Hindi voice messages)
- Text input support
- Conversational resume building
- Professional PDF output
- Works entirely in Hindi

## Prerequisites

### 1. Telegram Bot Token (BotFather)

1. Open Telegram and search for **@BotFather**
2. Send `/newbot`
3. Follow the prompts to name your bot
4. Copy the token provided (looks like `123456789:ABCdefGhIJKlmNoPQRsTUVwxyZ`)

### 2. OpenAI API Key (for Whisper)

1. Go to [platform.openai.com](https://platform.openai.com)
2. Sign up or log in
3. Go to API Keys section
4. Create a new secret key
5. Copy the key (starts with `sk-`)

### 3. Anthropic API Key (for Claude)

1. Go to [console.anthropic.com](https://console.anthropic.com)
2. Sign up or log in
3. Go to API Keys section
4. Create a new key
5. Copy the key (starts with `sk-ant-`)

## Setup

1. **Clone the repository**
   ```bash
   cd resume_bot
   ```

2. **Install uv** (if not already installed)
   ```bash
   pip install uv
   ```

3. **Create environment file**
   ```bash
   cp .env.example .env
   ```

4. **Add your API keys to `.env`**
   ```
   TELEGRAM_BOT_TOKEN=your_telegram_bot_token
   OPENAI_API_KEY=your_openai_api_key
   ANTHROPIC_API_KEY=your_anthropic_api_key
   ```

5. **Install dependencies**
   ```bash
   uv sync
   ```

6. **Install ffmpeg** (required for audio conversion)
   ```bash
   # Ubuntu/Debian
   sudo apt install ffmpeg

   # macOS
   brew install ffmpeg

   # Windows - download from https://ffmpeg.org/download.html
   ```

## Running the Bot

```bash
uv run src/bot.py
```

## Testing

1. Open Telegram and find your bot (by the name you gave it)
2. Send `/start`
3. The bot will greet you in Hindi and start asking questions
4. You can respond via:
   - Voice notes (recommended)
   - Text messages
5. After answering all 9 questions, your resume will be generated as a PDF

## Bot Commands

- `/start` - Start a new resume conversation
- `/cancel` - Cancel current conversation and start fresh

## How It Works

1. The bot asks questions one at a time in Hindi
2. User responds via voice note or text
3. Voice notes are transcribed using OpenAI Whisper
4. After all questions, Claude structures the data
5. A professional PDF resume is generated and sent to the user

## Privacy

- All conversation state is stored in memory (not persisted)
- Temporary audio files are deleted after processing
- No user data is stored on any server
