import base64
import io
import math
import os
from pathlib import Path

from PIL import Image, ImageChops, ImageFilter, ImageStat
from openai import OpenAI

from app.config import Config


IMAGE_MIN_BYTES = 1000
VISUAL_MIN_UNIQUE_COLORS = 16
VISUAL_MIN_ENTROPY = 2.0
VISUAL_MIN_VARIANCE = 150.0
VISUAL_MIN_EDGE_SCORE = 4.0
VISUAL_MAX_BLOCKINESS_RATIO = 0.35
DOMINANT_COLOR_REJECT_RATIO = 0.85
DOMINANT_COLOR_STRONG_KEEP_ENTROPY = 6.0
DOMINANT_COLOR_STRONG_KEEP_EDGE = 10.0
DOMINANT_COLOR_STRONG_KEEP_UNIQUE_COLORS = 50000
DOMINANT_COLOR_LOW_QUALITY_ENTROPY = 4.0
DOMINANT_COLOR_LOW_QUALITY_EDGE = 5.0
DOMINANT_COLOR_LOW_QUALITY_UNIQUE_COLORS = 5000


def _preferred_image_sizes_for_model(model_name):
    normalized_model = (model_name or "").strip().lower()

    # Prefer the smallest square size first to reduce cost.
    if normalized_model == "gpt-image-1":
        return ["512x512", "1024x1024"]

    return ["512x512", "1024x1024"]


def normalize_language(language):
    return (language or Config.DEFAULT_LANGUAGE).strip().lower()


def build_image_result(success, path=None, url=None, error=None, provider=None, status=None, content_type=None, file_size=None):
    return {
        "success": success,
        "path": path,
        "url": url,
        "error": error,
        "provider": provider,
        "status": status,
        "content_type": content_type,
        "file_size": file_size,
    }


def delete_if_exists(path):
    try:
        if path and path.exists():
            path.unlink()
    except Exception:
        pass


def log_image_file_validation(width, height, unique_colors_count, image_verified, rejected_reason):
    print("IMAGE WIDTH =", width, flush=True)
    print("IMAGE HEIGHT =", height, flush=True)
    print("UNIQUE COLORS COUNT =", unique_colors_count, flush=True)
    print("IMAGE VERIFIED =", image_verified, flush=True)
    print("IMAGE REJECTED REASON =", rejected_reason or "", flush=True)


def _histogram_entropy(histogram):
    total = float(sum(histogram) or 1.0)
    entropy = 0.0
    for count in histogram:
        if count:
            probability = count / total
            entropy -= probability * math.log2(probability)
    return entropy


def _analyze_image_visual_quality(image_path):
    # Multi-metric validation rejects low-information images before they reach the learner UI.
    width = None
    height = None
    unique_colors_count = None
    entropy = None
    variance = None
    edge_score = None
    dominant_ratio = None
    dominant_color_rejected = False
    image_verified = False
    rejected_reason = None

    try:
        with Image.open(image_path) as image:
            width, height = image.size
            image.verify()
            image_verified = True
    except Exception as exc:
        rejected_reason = rejected_reason or f"PIL could not open or verify image: {exc}"
        return False, {
            "width": width,
            "height": height,
            "unique_colors_count": unique_colors_count,
            "entropy": entropy,
            "variance": variance,
            "edge_score": edge_score,
            "image_verified": image_verified,
            "rejected_reason": rejected_reason,
        }

    try:
        with Image.open(image_path) as image:
            rgb_image = image.convert("RGB")
            width, height = rgb_image.size

            if width < 100 or height < 100:
                rejected_reason = f"Image dimensions too small: {width}x{height}"
            else:
                colors = rgb_image.getcolors(maxcolors=262144)
                unique_colors_count = len(colors) if colors is not None else 262145

                grayscale = rgb_image.convert("L")
                grayscale_histogram = grayscale.histogram()
                entropy = _histogram_entropy(grayscale_histogram)
                variance = ImageStat.Stat(grayscale).var[0]

                edges = grayscale.filter(ImageFilter.FIND_EDGES)
                edge_stat = ImageStat.Stat(edges)
                edge_score = edge_stat.mean[0]

                block_sample = rgb_image.resize((24, 24), Image.Resampling.NEAREST).resize(rgb_image.size, Image.Resampling.NEAREST)
                block_diff = ImageChops.difference(rgb_image, block_sample)
                block_ratio = sum(ImageStat.Stat(block_diff).mean) / (255.0 * 3.0)

                dominant_count = 0
                if colors:
                    dominant_count = max(color_count for color_count, _ in colors)
                    total_pixels = sum(color_count for color_count, _ in colors) or 1
                    dominant_ratio = dominant_count / total_pixels
                else:
                    dominant_ratio = 1.0

                preserve_rich_image = (
                    (entropy is not None and entropy > DOMINANT_COLOR_STRONG_KEEP_ENTROPY)
                    or (edge_score is not None and edge_score > DOMINANT_COLOR_STRONG_KEEP_EDGE)
                    or (
                        unique_colors_count is not None
                        and unique_colors_count > DOMINANT_COLOR_STRONG_KEEP_UNIQUE_COLORS
                    )
                )
                if unique_colors_count < VISUAL_MIN_UNIQUE_COLORS:
                    rejected_reason = f"Only {unique_colors_count} unique colors"
                elif entropy < VISUAL_MIN_ENTROPY:
                    rejected_reason = f"Entropy too low: {entropy:.2f}"
                elif variance < VISUAL_MIN_VARIANCE:
                    rejected_reason = f"Variance too low: {variance:.2f}"
                elif edge_score < VISUAL_MIN_EDGE_SCORE:
                    rejected_reason = f"Edge density too low: {edge_score:.2f}"
                elif (
                    dominant_ratio > DOMINANT_COLOR_REJECT_RATIO
                    and not preserve_rich_image
                    and entropy < DOMINANT_COLOR_LOW_QUALITY_ENTROPY
                    and edge_score < DOMINANT_COLOR_LOW_QUALITY_EDGE
                    and unique_colors_count < DOMINANT_COLOR_LOW_QUALITY_UNIQUE_COLORS
                ):
                    rejected_reason = "Image has a dominant solid color"
                    dominant_color_rejected = True
                elif block_ratio <= VISUAL_MAX_BLOCKINESS_RATIO and unique_colors_count <= 32:
                    rejected_reason = f"Image appears blocky or test-pattern-like: block_ratio={block_ratio:.2f}"
    except Exception as exc:
        rejected_reason = rejected_reason or f"PIL validation failed: {exc}"

    valid = rejected_reason is None
    details = {
        "width": width,
        "height": height,
        "unique_colors_count": unique_colors_count,
        "entropy": entropy,
        "variance": variance,
        "edge_score": edge_score,
        "image_verified": image_verified,
        "rejected_reason": rejected_reason,
    }

    log_image_file_validation(width, height, unique_colors_count, image_verified, rejected_reason)
    print("IMAGE ENTROPY =", entropy, flush=True)
    print("IMAGE VARIANCE =", variance, flush=True)
    print("IMAGE UNIQUE COLORS =", unique_colors_count, flush=True)
    print("IMAGE EDGE SCORE =", edge_score, flush=True)
    print("DOMINANT_COLOR_RATIO =", dominant_ratio, flush=True)
    print("DOMINANT_COLOR_REJECTED =", dominant_color_rejected, flush=True)
    print("IMAGE REJECTED_REASON =", rejected_reason or "", flush=True)

    return valid, details


def _validate_image_file_details(path):
    valid, details = _analyze_image_visual_quality(path)
    if not valid:
        delete_if_exists(path)
    return valid, details


def validate_image_file(path) -> bool:
    valid, _ = _validate_image_file_details(path)
    return valid


def is_valid_existing_image(image_path) -> bool:
    try:
        if not image_path or not image_path.exists():
            return False

        if image_path.stat().st_size < IMAGE_MIN_BYTES:
            delete_if_exists(image_path)
            return False

        return validate_image_file(image_path)
    except Exception:
        delete_if_exists(image_path)
        return False


def _build_openai_client():
    api_key = os.getenv("OPENAI_API_KEY") or Config.OPENAI_API_KEY
    if not api_key:
        raise RuntimeError("OPENAI_API_KEY is missing")
    return OpenAI(api_key=api_key)


def _build_openai_image_prompt(sentence, style="cartoon", language=None):
    style_guidance = {
        "cartoon": "storybook quality, children's educational flashcard style, clean educational illustration, clean lines, friendly expressive characters, warm lighting, colorful but balanced composition, simple composition",
        "realistic": "high-quality realistic illustration, storybook quality, children's educational flashcard style, cinematic but soft lighting, natural details, clean composition, professional educational feel, simple composition",
        "watercolor": "soft watercolor illustration, storybook quality, children's educational flashcard style, gentle brush textures, warm palette, airy composition, polished educational look, simple composition",
    }

    selected_style = style_guidance.get((style or "cartoon").lower(), style_guidance["cartoon"])
    normalized_language = normalize_language(language)
    language_guidance = {
        "french": "French-language learning context with culturally appropriate details for French learners",
        "english": "English-language learning context with culturally appropriate details for English learners",
        "spanish": "Spanish-language learning context with culturally appropriate details for Spanish learners",
        "german": "German-language learning context with culturally appropriate details for German learners",
        "chinese": "Chinese-language learning context with culturally appropriate details for Chinese learners",
    }
    selected_language = language_guidance.get(normalized_language, "language-learning context suitable for the selected vocabulary")

    return (
        f"Create a high-quality educational illustration for a beginner language learner. "
        f"Show the meaning of this sentence clearly: {sentence}. "
        f"Use a {selected_language}. "
        f"Style: {selected_style}. "
        f"The image must be warm, colorful, child-friendly, professional, and visually clean. "
        f"Use a simple clean illustration with one clear scene showing the sentence meaning. "
        f"Use simple composition with one main idea and a calm background. "
        f"Absolutely no text anywhere in the image. "
        f"No letters, no words, no captions, no labels, no posters, no signs, no writing anywhere. "
        f"No writing on walls, books, paper, clothing, or background. "
        f"No classroom boards or posters. "
        f"No symbols, no fake writing, no numbers, no watermarks, and no logos. "
        f"Aim for a warm child-friendly educational style, storybook quality, and flashcard style."
    )


def _validate_decoded_image_bytes(image_bytes: bytes) -> None:
    with Image.open(io.BytesIO(image_bytes)) as image:
        image.verify()


def generate_image_with_gemini(sentence, word, sentence_number, style="cartoon", language=None, mode="normal"):
    """
    Placeholder for future Gemini image integration.
    This keeps the router stable while the provider implementation is added later.
    """
    raise NotImplementedError("Gemini image provider is not implemented yet.")


def generate_image_with_huggingface(sentence, word, sentence_number, style="cartoon", language=None, mode="normal"):
    """
    Placeholder for future Hugging Face image integration.
    This keeps the router stable while the provider implementation is added later.
    """
    raise NotImplementedError("Hugging Face image provider is not implemented yet.")


def generate_image_with_openai(sentence, word, sentence_number, style="cartoon", language=None, mode="normal"):
    # Provider-specific implementation is isolated so other image providers can be added incrementally.
    safe_word = word.replace(" ", "_").lower()
    Path(Config.IMAGE_DIR).mkdir(parents=True, exist_ok=True)
    filename = f"{safe_word}_{sentence_number}.png"
    path = Config.IMAGE_DIR / filename
    image_url = f"/generated/images/{filename}"

    print("USE_REAL_IMAGES =", Config.USE_REAL_IMAGES, flush=True)

    # Local cost-control gate: skip image API calls when real generation is disabled.
    if not Config.USE_REAL_IMAGES:
        print("IMAGE GENERATION SKIPPED =", True, flush=True)
        return build_image_result(False, path=None, url=None, error="Image generation disabled or unavailable")

    print("IMAGE GENERATION SKIPPED =", False, flush=True)

    try:
        client = _build_openai_client()
        response = None
        attempted_sizes = []
        image_sizes = _preferred_image_sizes_for_model(Config.OPENAI_IMAGE_MODEL)
        prompt = _build_openai_image_prompt(sentence, style, language)

        print("MODE =", mode, flush=True)
        print("WORD =", word, flush=True)
        print("SENTENCE =", sentence, flush=True)
        print("IMAGE PROMPT =", prompt, flush=True)
        print("IMAGE FILENAME =", filename, flush=True)
        print("IMAGE PATH =", path, flush=True)
        print("IMAGE URL =", image_url, flush=True)

        # Size retry strategy improves resilience across model/endpoint constraints.
        for requested_size in image_sizes:
            attempted_sizes.append(requested_size)
            print(f"IMAGE SIZE REQUESTED = {requested_size}", flush=True)
            try:
                response = client.images.generate(
                    model=Config.OPENAI_IMAGE_MODEL,
                    prompt=prompt,
                    n=1,
                    size=requested_size,
                    output_format="png",
                )
                break
            except Exception as size_error:
                error_text = str(size_error).lower()
                is_size_problem = "size" in error_text and (
                    "unsupported" in error_text
                    or "invalid" in error_text
                    or "not support" in error_text
                    or "must be one of" in error_text
                )
                if is_size_problem and requested_size != image_sizes[-1]:
                    print(
                        f"OPENAI IMAGE SIZE RETRY: {requested_size} rejected, trying next size",
                        flush=True,
                    )
                    continue
                raise

        if response is None:
            raise RuntimeError(f"No OpenAI image response after size attempts: {attempted_sizes}")

        image_data = (response.data or [None])[0]
        if not image_data or not getattr(image_data, "b64_json", None):
            raise RuntimeError("OpenAI image response missing base64 image data")

        image_bytes = base64.b64decode(image_data.b64_json)
        if len(image_bytes) < IMAGE_MIN_BYTES:
            raise RuntimeError(f"OpenAI returned file smaller than {IMAGE_MIN_BYTES} bytes")

        _validate_decoded_image_bytes(image_bytes)
        path.write_bytes(image_bytes)
        valid, details = _validate_image_file_details(path)
        if not valid:
            error = details.get("rejected_reason") or "OpenAI image validation failed"
            delete_if_exists(path)
            print("OPENAI IMAGE SUCCESS/FAILED = FAILED", flush=True)
            print("IMAGE REJECTED_REASON =", error, flush=True)
            print("image_path.exists() =", path.exists(), flush=True)
            print(f"OPENAI IMAGE FAILED: {error}", flush=True)
            return build_image_result(False, path=None, url=None, error=error, provider="OpenAI")

        print("OPENAI IMAGE SUCCESS/FAILED = SUCCESS", flush=True)
        print("IMAGE REJECTED_REASON =", "", flush=True)
        print("image_path.exists() =", path.exists(), flush=True)
        print("OPENAI IMAGE SUCCESS", flush=True)
        return build_image_result(True, path=path, url=image_url, error=None, provider="OpenAI", file_size=path.stat().st_size)
    except Exception as error:
        delete_if_exists(path)
        print("OPENAI IMAGE SUCCESS/FAILED = FAILED", flush=True)
        print("IMAGE REJECTED_REASON =", str(error), flush=True)
        print("image_path.exists() =", path.exists(), flush=True)
        print(f"OPENAI IMAGE FAILED: {error}", flush=True)
        return build_image_result(False, path=None, url=None, error=str(error), provider="OpenAI")


def generate_image_file(sentence, word, sentence_number, style="cartoon", language=None, mode="normal"):
    # Global gate avoids any image-provider invocation when demo mode or budget mode is active.
    if not Config.USE_REAL_IMAGES:
        print("IMAGE GENERATION SKIPPED =", True, flush=True)
        return build_image_result(False, path=None, url=None, error="Image generation disabled or unavailable")

    # Provider router keeps route-level orchestration unchanged while enabling pluggable providers.
    provider = Config.AI_IMAGE_PROVIDER
    print(f"IMAGE PROVIDER = {provider}", flush=True)
    print("IMAGE GENERATION SKIPPED =", False, flush=True)

    try:
        if provider == "openai":
            return generate_image_with_openai(sentence, word, sentence_number, style, language, mode)

        if provider == "gemini":
            return generate_image_with_gemini(sentence, word, sentence_number, style, language, mode)

        if provider == "huggingface":
            return generate_image_with_huggingface(sentence, word, sentence_number, style, language, mode)

        # Unsupported providers return a structured failure instead of breaking the request pipeline.
        return build_image_result(False, path=None, url=None, error=f"Image provider '{provider}' is unavailable")
    except Exception as error:
        print(f"IMAGE PROVIDER FALLBACK USED: {provider} ({error})", flush=True)
        return build_image_result(False, path=None, url=None, error=str(error), provider=provider)
