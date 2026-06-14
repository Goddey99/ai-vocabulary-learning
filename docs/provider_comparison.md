# AI Service Provider Comparison

## 1. OpenAI GPT-5 mini

### Services
- Text generation

### Advantages
- High-quality language generation
- Structured JSON output support
- Single SDK for the text and image pipeline

### Disadvantages
- Requires API key for production use

### Best Use in This Project
OpenAI GPT-5 mini is the current sentence generation provider in the application.

---

## 2. Google Cloud Text-to-Speech

### Services
- Text-to-speech
- Multilingual voices
- Neural voices

### Advantages
- Reliable pronunciation quality
- Strong multilingual support
- Good documentation
- Suitable for educational projects

### Disadvantages
- Setup requires Google Cloud account
- Credentials can be confusing for beginners
- Some advanced voices are paid

### Best Use in This Project
Google Cloud Text-to-Speech is suitable for generating MP3 files for each sentence.

---

## 3. ElevenLabs

### Services
- Text-to-speech
- Voice cloning
- Multilingual speech generation

### Advantages
- Very natural voice quality
- Strong emotional tone
- Good for realistic pronunciation

### Disadvantages
- More expensive than basic TTS options
- Free tier is limited
- Voice cloning is not necessary for this project

### Best Use in This Project
ElevenLabs is useful if the project prioritizes natural-sounding speech.

---

## 4. OpenAI gpt-image-1

### Services
- Image generation

### Advantages
- Direct integration with the app's OpenAI SDK
- Supports local validation of returned image bytes
- Works with the selected image style prompt

### Disadvantages
- Requires API key
- Requires local validation before saving

### Best Use in This Project
OpenAI gpt-image-1 is the current image generation provider in the application.

---

## Selected Providers

For this project, the recommended choice is:

- OpenAI GPT-5 mini for sentence generation
- OpenAI gpt-image-1 for image generation
- gTTS for free demo audio, or Google Cloud Text-to-Speech for production-quality audio

## Justification

This combination keeps the application on a single OpenAI path for text and image generation while preserving the lightweight local audio workflow. The result is simpler, easier to test, and less brittle than the earlier multi-provider setup.
