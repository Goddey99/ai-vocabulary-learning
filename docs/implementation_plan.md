# Implementation Plan

## Phase 1: Working Prototype

Goal: Build a small but complete vocabulary learning workflow.

Completed:
- Flask web application
- Vocabulary CSV loading
- User-configurable learning parameters
- Sentence generation service
- Audio file placeholder generation
- Image prompt placeholder generation
- Study card display

## Phase 2: Real Sentence Generation

Goal: Connect the sentence generator to a real AI API.

Steps:
1. Create a `.env` file.
2. Add `OPENAI_API_KEY`.
3. Set `USE_OPENAI=true`.
4. Run the application.
5. Test whether generated sentences obey the allowed vocabulary rule.

## Phase 3: Real Audio Generation

Goal: Generate actual MP3 files for every sentence.

Recommended provider:
- gTTS for a free/simple demo solution
- Google Cloud Text-to-Speech for higher-quality multilingual voices
- ElevenLabs for more natural voices (paid)

## Phase 4: Real Image Generation

Goal: Generate real images for each sentence.

Recommended provider:
- OpenAI gpt-image-1 for the primary implementation
- Stability AI only if a future multi-provider fallback is reintroduced

## Phase 5: Final Report and Demonstration

The final report should include:
- Introduction
- Problem statement
- Objectives
- System architecture
- AI provider comparison
- Selected provider justification
- Implementation details
- Screenshots
- Testing results
- Limitations
- Future improvements
- Conclusion
