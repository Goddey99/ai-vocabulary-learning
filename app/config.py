import os
from pathlib import Path
from dotenv import load_dotenv

load_dotenv(override=True)


class Config:
    BASE_DIR = Path(__file__).resolve().parent.parent
    DATA_DIR = BASE_DIR / "data"
    GENERATED_DIR = BASE_DIR / "generated"
    AUDIO_DIR = GENERATED_DIR / "audio"
    IMAGE_DIR = GENERATED_DIR / "images"

    VOCABULARY_FILE = DATA_DIR / "french_frequency_words.csv"

    # Centralized secret loading keeps provider credentials environment-driven and out of source control.
    OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
    GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")
    ANTHROPIC_API_KEY = os.getenv("ANTHROPIC_API_KEY")
    HUGGINGFACE_API_KEY = os.getenv("HUGGINGFACE_API_KEY")

    # Provider selectors make the service layer provider-agnostic without changing routes or templates.
    AI_TEXT_PROVIDER = os.getenv("AI_TEXT_PROVIDER", "openai").lower()
    AI_IMAGE_PROVIDER = os.getenv("AI_IMAGE_PROVIDER", "openai").lower()
    AUDIO_PROVIDER = os.getenv("AUDIO_PROVIDER", "gtts").lower()

    # Cost-control toggles allow local/demo operation when external API calls are not desired.
    USE_REAL_AUDIO = os.getenv("USE_REAL_AUDIO", "false").lower() == "true"
    USE_REAL_IMAGES = os.getenv("USE_REAL_IMAGES", "false").lower() == "true"
    # Backward compatibility for legacy UI status checks while provider routing is now primary.
    USE_OPENAI = os.getenv(
        "USE_OPENAI",
        "true" if AI_TEXT_PROVIDER == "openai" or AI_IMAGE_PROVIDER == "openai" else "false",
    ).lower() == "true"

    OPENAI_TEXT_MODEL = os.getenv("OPENAI_TEXT_MODEL", "gpt-5-mini")
    OPENAI_IMAGE_MODEL = os.getenv("OPENAI_IMAGE_MODEL", "gpt-image-1")
    TTS_MODEL = os.getenv("TTS_MODEL", "tts-1")
    TTS_VOICE = os.getenv("TTS_VOICE", "alloy")
    IMAGE_MODEL = os.getenv("IMAGE_MODEL", "gpt-image-1")

    DEFAULT_LANGUAGE = "French"
    DEFAULT_TARGET_WORDS = 10
    DEFAULT_SENTENCES_PER_WORD = 2
    DEFAULT_ALLOWED_VOCABULARY_RANGE = 50
    DEFAULT_IMAGE_STYLE = "cartoon"
