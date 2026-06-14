# AI-Based Vocabulary Memorization Tool

This project uses AI services to help learners memorize vocabulary when learning a new language.

The system supports French, English, Spanish, and German, with French used as the primary demonstration language.

## Core Idea

The learning flow is:

```text
word → sentence → audio → image
```

This helps the learner remember vocabulary through reading, listening, and visual memory.

## System Flow

User Input → Vocabulary Loader → Sentence Generator → Audio Generator → Image Generator → Study Cards UI

## Features

- Load vocabulary from a frequency-based CSV file
- Allow the user to choose:
  - language
  - number of target words
  - number of sentences per word
  - allowed vocabulary range
  - image style
- Generate beginner-level learning sentences
- Generate pronunciation audio for each sentence
- Generate contextual illustrative images for each sentence
- Display results as study cards

## Project Structure

```text
app/        # Flask routes, templates, and services
data/       # Vocabulary frequency CSV files
docs/       # Documentation and screenshots
generated/  # Generated audio and images
tests/      # Unit tests
scripts/    # Helper scripts
instance/   # Local runtime data
```

## Technology Stack

- Python
- Flask
- HTML/CSS
- CSV vocabulary file
- OpenAI GPT-5 mini sentence generation with structured JSON output
- OpenAI gpt-image-1 image generation with local validation
- Placeholder-ready audio generation service

## How to Run

### 1. Create a virtual environment

```bash
python -m venv venv
```

### 2. Activate the virtual environment

Windows:

```bash
venv\Scripts\activate
```

Mac/Linux:

```bash
source venv/bin/activate
```

### 3. Install dependencies

```bash
pip install -r requirements.txt
```

### 4. Run the app

```bash
python run.py
```

Open this in your browser:

```text
http://127.0.0.1:5050
```

## Provider-Agnostic AI Configuration

The app keeps OpenAI as the active provider today, but the service layer is routed by environment variables so the provider can be switched later without touching routes or templates.

### 1. Copy `.env.example`

Create a new file called `.env`.

### 2. Add your API settings

```text
OPENAI_API_KEY=your_openai_api_key_here
AI_TEXT_PROVIDER=openai
AI_IMAGE_PROVIDER=openai
AUDIO_PROVIDER=gtts
USE_REAL_AUDIO=true
USE_REAL_IMAGES=true
```

### 3. Run the app again

```bash
python run.py
```

If OpenAI fails, the app automatically falls back to local mock sentence generation so the UI still renders.

### Provider notes

- Text generation is selected by `AI_TEXT_PROVIDER`.
- Image generation is selected by `AI_IMAGE_PROVIDER`.
- Audio generation is selected by `AUDIO_PROVIDER`.
- OpenAI is currently selected for text and image generation because it is the implemented production path.
- gTTS is currently selected for audio because it is the implemented production path.
- Gemini, Claude, and Hugging Face hooks exist as placeholders for later provider swaps.

## Important Notes

The current version is intentionally built in a safe professional way:
- It supports both real AI providers and fallback local generation for development.
- It has a clean service-based design.
- OpenAI is the primary provider for text and image generation.
- It is suitable for classroom demonstration and future expansion.

## Documentation

See:

```text
docs/provider_comparison.md
docs/implementation_plan.md
```
