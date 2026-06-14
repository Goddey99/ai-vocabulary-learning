# API Integration Notes

The project description requires Steps 3, 4, and 5 to be completed through API calls to AI services.

## Step 3: Sentence Generation

Provider used:
- OpenAI GPT-5 mini

Purpose:
- Generate beginner-level language-learning sentences for each vocabulary word with structured JSON output.

File:
- `app/services/sentence_service.py`

## Step 4: Audio Generation

Provider used:
- gTTS (Google Translate TTS)

Purpose:
- Generate MP3 audio for each sentence (offline/free wrapper calling Google TTS).

File:
- `app/services/audio_service.py`

## Step 5: Image Generation

Provider used:
- OpenAI gpt-image-1

Purpose:
- Generate a visual representation of each sentence and save the validated PNG locally.

File:
- `app/services/image_service.py`

## Why OpenAI / gTTS Were Selected

OpenAI provides both the text and image generation paths through a single SDK, which simplifies the application and removes provider fallback complexity. `gTTS` is still used for audio because it keeps the audio path lightweight and local.

## Testing Advice

Turn the API features on one at a time:

1. `USE_OPENAI=true`
2. `USE_REAL_AUDIO=true`
3. Verify `OPENAI_API_KEY` is set

This avoids unnecessary API cost during early testing.
