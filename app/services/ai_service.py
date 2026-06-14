import json
import os
import re
import unicodedata

from openai import OpenAI

from app.config import Config


OPENAI_TEXT_MODEL = os.getenv("OPENAI_TEXT_MODEL", "gpt-5-mini")


def get_openai_client() -> OpenAI:
    api_key = os.getenv("OPENAI_API_KEY") or Config.OPENAI_API_KEY
    if not api_key:
        raise RuntimeError("OPENAI_API_KEY is missing")
    return OpenAI(api_key=api_key)


def strip_accents(text):
    return "".join(
        char
        for char in unicodedata.normalize("NFKD", text or "")
        if not unicodedata.combining(char)
    )


def normalize_for_match(text):
    return strip_accents((text or "").strip().casefold())


def build_sentence_generation_prompt(language, target_word, allowed_words, count, custom_mode=False):
    allowed_text = ", ".join([item["word"].strip() for item in allowed_words if item.get("word")])
    mode_text = (
        "Custom word mode is active. The learner picked the target word manually, so keep the sentences natural, practical, and beginner-friendly."
        if custom_mode
        else "Normal vocabulary mode is active. Keep the sentences simple and aligned with the provided vocabulary range."
    )

    return f"""
You are generating language-learning study sentences.

Language: {language}
Target word: {target_word}
Sentence count: {count}
Allowed vocabulary: {allowed_text}

Rules:
- Return valid JSON only.
- Return exactly {count} items in the `sentences` array.
- Each item must have `sentence` and `translation` fields.
- `sentence` must be in {language}.
- `translation` must be in English.
- Every sentence must use the target word naturally.
- Keep the language simple, beginner-friendly, and natural.
- Prefer the allowed vocabulary when possible.
- Avoid awkward, robotic, or overly advanced phrasing.
- Do not include markdown fences, commentary, numbering, or extra keys.

{mode_text}

JSON shape:
{{
  "sentences": [
    {{"sentence": "...", "translation": "..."}}
  ]
}}
""".strip()


def _build_mock_sentences(language, target_word, allowed_words, count=2, custom_mode=False):
    # Local fallback keeps the learning flow usable when provider calls are disabled or fail.
    word = (target_word or "").strip()
    allowed_sample = [item.get("word", "").strip() for item in allowed_words if item.get("word")]

    if normalize_for_match(language) == "french":
        templates = [
            (f"Je lis un livre simple.", "I read a simple book."),
            (f"Le livre est sur la table.", "The book is on the table."),
            (f"Marie aime ce livre.", "Marie likes this book."),
        ]
    elif normalize_for_match(language) == "spanish":
        templates = [
            (f"Leo un libro simple.", "I read a simple book."),
            (f"El libro está en la mesa.", "The book is on the table."),
            (f"María ama este libro.", "Marie likes this book."),
        ]
    elif normalize_for_match(language) == "german":
        templates = [
            (f"Ich lese ein einfaches Buch.", "I read a simple book."),
            (f"Das Buch liegt auf dem Tisch.", "The book is on the table."),
            (f"Maria mag dieses Buch.", "Marie likes this book."),
        ]
    else:
        templates = [
            (f"I read a simple book.", "Je lis un livre simple."),
            (f"The book is on the table.", "Le livre est sur la table."),
            (f"Marie likes this book.", "Marie aime ce livre."),
        ]

    if custom_mode and word:
        templates = [
            (f"I use {word} in a simple sentence.", f"J'utilise {word} dans une phrase simple."),
            (f"The word {word} is useful today.", f"Le mot {word} est utile aujourd'hui."),
            (f"We practice {word} in class.", f"Nous pratiquons {word} en classe."),
        ]

    if allowed_sample:
        anchor = allowed_sample[0]
        templates = [
            (sentence.replace("simple book", anchor).replace("book", anchor), translation)
            for sentence, translation in templates
        ]

    results = []
    for index in range(count):
        sentence, translation = templates[index % len(templates)]
        results.append({"sentence": sentence, "translation": translation})

    return results[:count]


def _clean_json_text(raw_text: str) -> str:
    text = (raw_text or "").strip()
    if text.startswith("```"):
        text = re.sub(r"^```(?:json)?\s*", "", text)
        text = re.sub(r"\s*```$", "", text)
    return text.strip()


def parse_sentence_payload(raw_text, target_word, count):
    try:
        payload = json.loads(_clean_json_text(raw_text))
    except Exception as exc:
        raise RuntimeError(f"OpenAI returned invalid JSON: {exc}") from exc

    items = payload.get("sentences") if isinstance(payload, dict) else None
    if not isinstance(items, list):
        raise RuntimeError("OpenAI JSON did not include a sentences array")

    parsed = []
    target_key = normalize_for_match(target_word)
    for item in items:
        if len(parsed) >= count:
            break

        if not isinstance(item, dict):
            raise RuntimeError("OpenAI sentence item was not an object")

        sentence = str(item.get("sentence", "")).strip()
        translation = str(item.get("translation", "")).strip()
        if not sentence:
            raise RuntimeError("OpenAI sentence item was missing sentence text")
        if target_key and target_key not in normalize_for_match(sentence):
            raise RuntimeError(f"OpenAI sentence did not include target word: {sentence}")

        parsed.append({"sentence": sentence, "translation": translation})

    if len(parsed) < count:
        raise RuntimeError("OpenAI returned too few sentences")

    return parsed[:count]


def generate_sentences_with_openai(language, target_word, allowed_words, count=2, custom_mode=False):
    # Dedicated OpenAI implementation keeps provider-specific API code isolated from routing logic.
    prompt = build_sentence_generation_prompt(language, target_word, allowed_words, count, custom_mode)
    client = get_openai_client()

    print("OPENAI TEXT REQUEST STARTED", flush=True)
    try:
        response = client.chat.completions.create(
            model=OPENAI_TEXT_MODEL,
            messages=[
                {
                    "role": "system",
                    "content": (
                        "You are a careful language tutor that returns only valid JSON. "
                        "Always follow the requested JSON shape exactly."
                    ),
                },
                {
                    "role": "user",
                    "content": prompt,
                },
            ],
            response_format={"type": "json_object"},
        )
        raw_text = getattr(response.choices[0].message, "content", "") or ""
        parsed = parse_sentence_payload(raw_text, target_word, count)
        print("OPENAI TEXT SUCCESS", flush=True)
        return parsed
    except Exception as error:
        print(f"OPENAI TEXT FAILED: {error}", flush=True)
        raise


def generate_sentences_with_gemini(language, target_word, allowed_words, count=2, custom_mode=False):
    """
    Placeholder for future Gemini integration.
    This function can be implemented later without changing routes.py.
    """
    raise NotImplementedError("Gemini text provider is not implemented yet.")


def generate_sentences_with_claude(language, target_word, allowed_words, count=2, custom_mode=False):
    """
    Placeholder for future Claude integration.
    This function can be implemented later without changing routes.py.
    """
    raise NotImplementedError("Claude text provider is not implemented yet.")


def generate_sentences(language, target_word, allowed_words, count=2, custom_mode=False):
    # Provider router enables backend provider switching without touching route handlers or frontend logic.
    provider = Config.AI_TEXT_PROVIDER
    print(f"TEXT PROVIDER = {provider}", flush=True)
    try:
        if provider == "openai":
            return generate_sentences_with_openai(language, target_word, allowed_words, count, custom_mode)

        if provider == "gemini":
            return generate_sentences_with_gemini(language, target_word, allowed_words, count, custom_mode)

        if provider == "claude":
            return generate_sentences_with_claude(language, target_word, allowed_words, count, custom_mode)

        # Unknown providers are handled safely by returning deterministic local output.
        return _build_mock_sentences(language, target_word, allowed_words, count, custom_mode)
    except Exception as error:
        # Any provider failure degrades gracefully to mock sentences so card generation does not crash.
        print(f"TEXT PROVIDER FALLBACK USED: {provider} ({error})", flush=True)
        return _build_mock_sentences(language, target_word, allowed_words, count, custom_mode)
