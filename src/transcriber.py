"""Groq-based speech-to-text for Hindi voice messages."""

import logging
import os

from openai import OpenAI

logger = logging.getLogger(__name__)


def get_groq_client() -> OpenAI:
    """Get Groq client with API key from environment."""
    api_key = os.environ.get("GROQ_API_KEY")
    if not api_key:
        raise ValueError("GROQ_API_KEY not set in environment")
    return OpenAI(
        api_key=api_key,
        base_url="https://api.groq.com/openai/v1",
    )


def convert_ogg_to_mp3(ogg_path: str) -> str:
    """Convert .ogg file to .mp3 using pydub."""
    from pydub import AudioSegment

    audio = AudioSegment.from_ogg(ogg_path)
    mp3_path = ogg_path.replace(".ogg", ".mp3")
    audio.export(mp3_path, format="mp3")
    return mp3_path


def transcribe_audio(file_path: str) -> str:
    """Transcribe audio file to Hindi text using Groq Whisper."""
    client = get_groq_client()
    with open(file_path, "rb") as audio_file:
        transcript = client.audio.transcriptions.create(
            model="whisper-large-v3",
            file=audio_file,
            language="hi",
        )
    return transcript.text.strip()


async def process_voice_file(bot, file_id: str) -> str:
    """Download voice file, convert, and transcribe. Returns Hindi text."""
    import tempfile

    tmp_dir = tempfile.gettempdir()
    ogg_path = os.path.join(tmp_dir, f"voice_{file_id}.ogg")

    # Download .ogg from Telegram
    voice_file = await bot.get_file(file_id)
    await voice_file.download_to_drive(ogg_path)

    try:
        # Convert to mp3
        mp3_path = convert_ogg_to_mp3(ogg_path)

        # Transcribe
        text = transcribe_audio(mp3_path)

        return text
    finally:
        # Clean up temp files
        for path in [ogg_path, mp3_path]:
            if os.path.exists(path):
                os.remove(path)