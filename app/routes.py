from pathlib import Path

from flask import (
    Blueprint,
    render_template,
    request,
    send_file,
    send_from_directory
)

from app.config import Config
from .services.vocabulary_service import load_vocabulary, select_vocabulary_words
from .services.sentence_service import generate_sentences
from .services.audio_service import generate_audio_file
from .services.image_service import generate_image_file, is_valid_existing_image

main = Blueprint("main", __name__)


def should_show_translation(word, translation):
    normalized_word = str(word or "").strip().casefold()
    normalized_translation = str(translation or "").strip().casefold()

    if not normalized_translation:
        return False

    return normalized_word != normalized_translation


@main.route("/", methods=["GET"])
def index():

    # Homepage initializes form defaults and communicates current feature-toggle status to the UI.

    form_values = {
        "language": "French",
        "target_words": 10,
        "sentences_per_word": 2,
        "allowed_range": 50,
        "image_style": "cartoon",
        "custom_word": "",
    }

    print("USE_REAL_IMAGES =", Config.USE_REAL_IMAGES, flush=True)
    print("ROUTE IMAGE ENABLED =", Config.USE_REAL_IMAGES, flush=True)

    return render_template(
        "index.html",
        results=[],
        form_values=form_values,
        image_enabled=Config.USE_REAL_IMAGES,
        ai_enabled=Config.USE_OPENAI,
        should_show_translation=should_show_translation,
    )


@main.route("/generate", methods=["POST"])
def generate():

    # Main orchestration route connecting form input, backend services, and rendered study cards.
    results = []

    # Form extraction normalizes user input into a single configuration object for this request.
    form_values = {
        "language": request.form.get("language", "French"),
        "target_words": int(request.form.get("target_words", 10)),
        "sentences_per_word": int(request.form.get("sentences_per_word", 2)),
        "allowed_range": int(request.form.get("allowed_range", 50)),
        "image_style": request.form.get("image_style", "cartoon"),
        "custom_word": request.form.get("custom_word", "").strip(),
    }

    language = form_values["language"]

    target_words = form_values["target_words"]

    sentences_per_word = form_values["sentences_per_word"]

    allowed_range = form_values["allowed_range"]

    image_style = form_values["image_style"]

    custom_word = form_values["custom_word"]

    print("USE_REAL_IMAGES =", Config.USE_REAL_IMAGES, flush=True)

    # Vocabulary loading is decoupled from routes so language datasets can evolve independently.
    vocabulary = load_vocabulary(language)

    # Custom-word mode bypasses normal selection so users can force focused practice on one term.
    if custom_word:
        normalized_custom = custom_word.casefold()
        meaning = "Custom word"
        for vocab_item in vocabulary:
            if vocab_item["word"].strip().casefold() == normalized_custom:
                meaning = vocab_item.get("meaning", "Custom word")
                break

        selected_words = [{"word": custom_word, "meaning": meaning}]
    # Standard mode ranks and selects beginner-friendly vocabulary from the chosen frequency range.
    else:
        selection = select_vocabulary_words(vocabulary, language, target_words)
        selected_words = selection["selected_words"]
        filtered_stopwords_count = selection["filtered_stopwords_count"]
        fallback_used = selection["fallback_used"]
        vocabulary_score = selection["vocabulary_score"]

    if custom_word:
        filtered_stopwords_count = 0
        fallback_used = False
        vocabulary_score = [(item["word"], 0) for item in selected_words]
    elif fallback_used:
        print("VOCABULARY_FILTER_FALLBACK_USED =", True, flush=True)

    allowed_pool = vocabulary if custom_word else selection["filtered_vocabulary"] or vocabulary
    allowed_words = allowed_pool[:allowed_range]
    run_mode = "custom" if custom_word else "normal"

    print("FILTERED_STOPWORDS_COUNT =", filtered_stopwords_count, flush=True)
    print("FINAL_SELECTED_WORDS =", [item["word"] for item in selected_words], flush=True)
    print("VOCABULARY_SCORE =", vocabulary_score, flush=True)

    for vocab_item in selected_words:

        word = vocab_item["word"]

        meaning = vocab_item["meaning"]

        safe_word = word.strip().lower().replace(" ", "_")

        # Text generation call is provider-routed inside the service layer for backend portability.
        sentences = generate_sentences(
            language=language,
            target_word=word,
            allowed_words=allowed_words,
            count=sentences_per_word,
            custom_mode=bool(custom_word),
        )

        sentence_items = []

        for index, sentence_entry in enumerate(
            sentences,
            start=1
        ):

            if isinstance(sentence_entry, dict):
                sentence = str(sentence_entry.get("sentence", "")).strip()
                translation = str(sentence_entry.get("translation", "")).strip()
            else:
                sentence = str(sentence_entry).strip()
                translation = ""

            # GENERATE AUDIO
            # Audio generation is modular and can be switched by environment provider settings.

            generate_audio_file(
                sentence,
                word,
                index,
                language
            )

            # GENERATE IMAGE
            # Image generation is provider-routed and guarded by cost-control toggles.
            image_filename = f"{safe_word}_{index}.png"
            image_path = Config.IMAGE_DIR / image_filename
            image_url = None
            image_result = None

            print("IMAGE GENERATION SKIPPED =", not Config.USE_REAL_IMAGES, flush=True)

            if Config.USE_REAL_IMAGES:
                image_url = f"/generated/images/{image_filename}"
                image_result = generate_image_file(
                    sentence,
                    word,
                    index,
                    image_style,
                    language,
                    mode=run_mode,
                )
                if image_result and image_result.get("path"):
                    image_path = Path(image_result["path"])
                if image_result and image_result.get("url"):
                    image_url = image_result["url"]

                valid_existing_image = is_valid_existing_image(image_path)
                image_available = bool(valid_existing_image)
                image_url = image_url if image_available else None
            else:
                image_available = False

            print("MODE =", run_mode, flush=True)
            print("WORD =", word, flush=True)
            print("SENTENCE =", sentence, flush=True)
            print("IMAGE FILENAME =", image_filename, flush=True)
            print("IMAGE PATH =", image_path, flush=True)
            print("IMAGE URL =", image_url, flush=True)
            print(
                "OPENAI IMAGE SUCCESS/FAILED =",
                "SUCCESS" if image_result and image_result.get("success") else "FAILED",
                flush=True,
            )
            print(
                "IMAGE REJECTED_REASON =",
                (image_result or {}).get("error") or "",
                flush=True,
            )
            print("image_path.exists() =", image_path.exists(), flush=True)

            audio_url = (
                f"/generated/audio/"
                f"{safe_word}_{index}.mp3"
            )

            # Study card assembly keeps frontend rendering simple and template-driven.
            sentence_items.append({

                "sentence": sentence,

                "translation": translation,

                "audio": audio_url,

                "image": image_url,

                "image_available": image_available,

                "image_generation_enabled": Config.USE_REAL_IMAGES,

                "final_audio": audio_url,

                "is_real_image": image_available

            })

        results.append({

            "word": word,

            "meaning": meaning,

            "sentences": sentence_items

        })

    print("USE_REAL_IMAGES =", Config.USE_REAL_IMAGES, flush=True)
    print("ROUTE IMAGE ENABLED =", Config.USE_REAL_IMAGES, flush=True)

    # Final template rendering returns the complete study-card payload for this request.
    return render_template(
        "index.html",
        results=results,
        form_values=form_values,
        image_enabled=Config.USE_REAL_IMAGES,
        ai_enabled=Config.USE_OPENAI,
        should_show_translation=should_show_translation,
    )


# AUDIO ROUTE


@main.route("/generated/audio/<path:filename>")
def generated_audio(filename):

    file_path = Config.AUDIO_DIR / filename

    return send_file(
        file_path,
        mimetype="audio/mpeg",
        as_attachment=False,
        conditional=True
    )


# IMAGE ROUTE


@main.route("/generated/images/<path:filename>")
def generated_images(filename):

    return send_from_directory(
        Config.IMAGE_DIR,
        filename
    )