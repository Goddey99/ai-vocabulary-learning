from pathlib import Path
from gtts import gTTS
from app.config import Config


GTTS_LANGUAGE_CODES = {
    "french": "fr",
    "english": "en",
    "spanish": "es",
    "german": "de",
}


def normalize_language(language):
    return (language or Config.DEFAULT_LANGUAGE).strip().lower()


def get_gtts_language_code(language):
    return GTTS_LANGUAGE_CODES.get(normalize_language(language), GTTS_LANGUAGE_CODES["french"])


def generate_audio_with_openai(sentence, word, sentence_number, language=None):
    """
    Placeholder for future OpenAI audio integration.
    The current app uses gTTS, and this hook allows the provider to change later.
    """
    raise NotImplementedError("OpenAI audio provider is not implemented yet.")


def generate_audio_with_gtts(sentence, word, sentence_number, language=None):
    # File naming is deterministic so routes can resolve audio assets predictably per word/sentence pair.
    safe_word = word.replace(" ", "_").lower()
    filename = f"{safe_word}_{sentence_number}.mp3"
    path = Config.AUDIO_DIR / filename

    Path(Config.AUDIO_DIR).mkdir(parents=True, exist_ok=True)

    # Replace any stale file to keep generated audio aligned with the latest sentence text.
    if path.exists():
        path.unlink()

    tts = gTTS(text=sentence, lang=get_gtts_language_code(language), slow=False)
    tts.save(str(path))

    return f"/generated/audio/{filename}"


def generate_audio(sentence, word, sentence_number, language=None):
    # Cost-control gate allows the application to run without external TTS calls.
    if not Config.USE_REAL_AUDIO:
        return None

    # Provider router keeps audio generation modular and test-friendly.
    provider = Config.AUDIO_PROVIDER
    print(f"AUDIO PROVIDER = {provider}", flush=True)

    try:
        if provider == "gtts":
            return generate_audio_with_gtts(sentence, word, sentence_number, language)

        if provider == "openai":
            return generate_audio_with_openai(sentence, word, sentence_number, language)

        # Unsupported providers fail safely so study-card creation continues without hard errors.
        print(f"AUDIO PROVIDER UNAVAILABLE = {provider}", flush=True)
        return None
    except Exception as error:
        # Runtime provider errors are contained to preserve the rest of the generation pipeline.
        print(f"AUDIO PROVIDER FALLBACK USED: {provider} ({error})", flush=True)
        return None


def generate_audio_file(sentence, word, sentence_number, language=None):
    return generate_audio(sentence, word, sentence_number, language)