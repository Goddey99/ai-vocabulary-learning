import base64
import json
from io import BytesIO
from pathlib import Path

import pytest
from PIL import Image

from app.config import Config
from app.services.ai_service import generate_sentences
from app.services.audio_service import generate_audio, generate_audio_file
from app.services.image_service import generate_image_file
import app.services.ai_service as ai_service
import app.services.image_service as image_service
import app.services.audio_service as audio_service


class _FakeMessage:
    def __init__(self, content):
        self.content = content


class _FakeChoice:
    def __init__(self, content):
        self.message = _FakeMessage(content)


class _FakeChatCompletionResponse:
    def __init__(self, content):
        self.choices = [_FakeChoice(content)]


class _FakeChatCompletions:
    def __init__(self, payloads, prompt_log):
        self._payloads = payloads
        self._prompt_log = prompt_log
        self._index = 0

    def create(self, **kwargs):
        self._prompt_log.append(kwargs["messages"][1]["content"])
        payload = self._payloads[self._index]
        self._index += 1
        return _FakeChatCompletionResponse(json.dumps(payload))


class _FakeImageData:
    def __init__(self, b64_json):
        self.b64_json = b64_json


class _FakeImageResponse:
    def __init__(self, b64_json):
        self.data = [_FakeImageData(b64_json)]


class _FakeImages:
    def __init__(self, payloads, request_log=None):
        self._payloads = payloads
        self._index = 0
        self._request_log = request_log if request_log is not None else []

    def generate(self, **kwargs):
        self._request_log.append(kwargs)
        payload = self._payloads[self._index]
        self._index += 1
        if isinstance(payload, Exception):
            raise payload
        return _FakeImageResponse(payload)


class _FakeOpenAIClient:
    def __init__(self, text_payloads=None, image_payloads=None, prompt_log=None, image_request_log=None):
        self.chat = type("ChatNamespace", (), {})()
        self.images = _FakeImages(image_payloads or [], image_request_log)
        self.chat.completions = _FakeChatCompletions(text_payloads or [], prompt_log if prompt_log is not None else [])


@pytest.fixture()
def openai_enabled(monkeypatch, tmp_path):
    monkeypatch.setattr(Config, "AI_TEXT_PROVIDER", "openai")
    monkeypatch.setattr(Config, "AI_IMAGE_PROVIDER", "openai")
    monkeypatch.setattr(Config, "AUDIO_PROVIDER", "gtts")
    monkeypatch.setattr(Config, "USE_OPENAI", True)
    monkeypatch.setattr(Config, "USE_REAL_IMAGES", True)
    monkeypatch.setattr(Config, "USE_REAL_AUDIO", True)
    monkeypatch.setattr(Config, "OPENAI_TEXT_MODEL", "gpt-5-mini")
    monkeypatch.setattr(Config, "OPENAI_IMAGE_MODEL", "gpt-image-1")
    monkeypatch.setattr(Config, "IMAGE_DIR", tmp_path)
    monkeypatch.setattr(Config, "AUDIO_DIR", tmp_path)
    monkeypatch.setattr(Config, "OPENAI_API_KEY", "test-key")
    monkeypatch.setattr(ai_service, "get_openai_client", lambda: _FakeOpenAIClient())
    monkeypatch.setattr(image_service, "_build_openai_client", lambda: _FakeOpenAIClient())
    return tmp_path


def _make_image_bytes():
    image = Image.new("RGB", (128, 128))
    pixels = []
    for y in range(128):
        for x in range(128):
            pixels.append(((x * 17 + 5) % 256, (y * 29 + 9) % 256, ((x + y) * 13 + 11) % 256))
    image.putdata(pixels)
    buffer = BytesIO()
    image.save(buffer, format="BMP")
    return buffer.getvalue()


def _make_solid_color_image_bytes():
    image = Image.new("RGB", (512, 512), color=(240, 240, 240))
    buffer = BytesIO()
    image.save(buffer, format="BMP")
    return buffer.getvalue()


def test_generate_sentences_returns_structured_json_for_custom_and_normal_modes(monkeypatch, openai_enabled):
    payloads = [
        {
            "sentences": [
                {"sentence": "Je lis un livre simple.", "translation": "I read a simple book."},
                {"sentence": "Le livre est sur la table.", "translation": "The book is on the table."},
                {"sentence": "Marie aime ce livre.", "translation": "Marie likes this book."},
            ]
        },
        {
            "sentences": [
                {"sentence": "I read a book.", "translation": "Je lis un livre."},
                {"sentence": "The book is on the table.", "translation": "Le livre est sur la table."},
                {"sentence": "My friend likes this book.", "translation": "Mon ami aime ce livre."},
            ]
        },
    ]
    fake_client = _FakeOpenAIClient(payloads)
    monkeypatch.setattr(ai_service, "get_openai_client", lambda: fake_client)

    custom_sentences = generate_sentences("French", "livre", [{"word": "livre"}, {"word": "table"}], count=3, custom_mode=True)
    normal_sentences = generate_sentences("English", "book", [{"word": "book"}, {"word": "table"}], count=3, custom_mode=False)

    assert len(custom_sentences) == 3
    assert len(normal_sentences) == 3
    assert all("sentence" in item and "translation" in item for item in custom_sentences)
    assert all("sentence" in item and "translation" in item for item in normal_sentences)


def test_generate_sentences_uses_openai_provider_route(monkeypatch, openai_enabled):
    called = {}

    def fake_openai(language, target_word, allowed_words, count=2, custom_mode=False):
        called["provider"] = "openai"
        return [{"sentence": "Bonjour.", "translation": "Hello."}]

    monkeypatch.setattr(Config, "AI_TEXT_PROVIDER", "openai")
    monkeypatch.setattr(ai_service, "generate_sentences_with_openai", fake_openai)

    result = generate_sentences("French", "bonjour", [{"word": "bonjour"}], count=1, custom_mode=False)

    assert called["provider"] == "openai"
    assert result == [{"sentence": "Bonjour.", "translation": "Hello."}]


def test_generate_sentences_falls_back_safely_for_unsupported_provider(monkeypatch, openai_enabled):
    monkeypatch.setattr(Config, "AI_TEXT_PROVIDER", "unknown")
    monkeypatch.setattr(ai_service, "generate_sentences_with_openai", lambda *args, **kwargs: (_ for _ in ()).throw(AssertionError("openai should not be used")))

    result = generate_sentences("French", "livre", [{"word": "livre"}], count=2, custom_mode=False)

    assert len(result) == 2
    assert all("sentence" in item and "translation" in item for item in result)
    assert any("livre" in item["sentence"].lower() for item in result)


def test_generate_sentences_falls_back_when_openai_text_raises(monkeypatch, openai_enabled):
    monkeypatch.setattr(ai_service, "get_openai_client", lambda: (_ for _ in ()).throw(RuntimeError("boom")))

    results = generate_sentences(
        "French",
        "livre",
        [{"word": "livre"}, {"word": "table"}],
        count=3,
        custom_mode=True,
    )

    assert len(results) == 3
    assert all("sentence" in item and "translation" in item for item in results)
    assert any("livre" in item["sentence"].lower() for item in results)


def test_generate_image_file_requests_smallest_size_and_saves_valid_rich_image(monkeypatch, openai_enabled):
    monkeypatch.setattr(Config, "AI_IMAGE_PROVIDER", "openai")
    monkeypatch.setattr(Config, "USE_REAL_IMAGES", True)
    valid_b64 = base64.b64encode(_make_image_bytes()).decode("utf-8")
    image_request_log = []

    fake_client = _FakeOpenAIClient(image_payloads=[valid_b64], image_request_log=image_request_log)
    monkeypatch.setattr(
        image_service,
        "_build_openai_client",
        lambda: fake_client,
    )

    success_result = generate_image_file("I read a book.", "book", 1, "cartoon", "English")

    assert success_result["success"] is True
    assert success_result["path"].exists()
    assert image_request_log
    assert image_request_log[0]["size"] == "512x512"


def test_generate_image_file_uses_openai_provider_route(monkeypatch, openai_enabled):
    called = {}

    def fake_openai(sentence, word, sentence_number, style="cartoon", language=None, mode="normal"):
        called["provider"] = "openai"
        return {"success": True, "path": openai_enabled / "book_1.png", "url": "/generated/images/book_1.png"}

    monkeypatch.setattr(Config, "AI_IMAGE_PROVIDER", "openai")
    monkeypatch.setattr(Config, "USE_REAL_IMAGES", True)
    monkeypatch.setattr(image_service, "generate_image_with_openai", fake_openai)

    result = generate_image_file("I read a book.", "book", 1, "cartoon", "English")

    assert called["provider"] == "openai"
    assert result["success"] is True


def test_generate_image_file_returns_unavailable_for_unsupported_provider(monkeypatch, tmp_path):
    monkeypatch.setattr(Config, "AI_IMAGE_PROVIDER", "unsupported")
    monkeypatch.setattr(Config, "USE_REAL_IMAGES", True)
    monkeypatch.setattr(Config, "IMAGE_DIR", tmp_path)
    monkeypatch.setattr(image_service, "generate_image_with_openai", lambda *args, **kwargs: (_ for _ in ()).throw(AssertionError("openai image path should not be used")))

    result = generate_image_file("I read a book.", "book", 1, "cartoon", "English")

    assert result["success"] is False
    assert result["path"] is None
    assert result["url"] is None
    assert "unavailable" in (result["error"] or "").lower()


def test_generate_image_file_skips_when_use_real_images_false(monkeypatch, tmp_path):
    monkeypatch.setattr(Config, "AI_IMAGE_PROVIDER", "openai")
    monkeypatch.setattr(Config, "USE_REAL_IMAGES", False)
    monkeypatch.setattr(Config, "IMAGE_DIR", tmp_path)
    monkeypatch.setattr(image_service, "generate_image_with_openai", lambda *args, **kwargs: (_ for _ in ()).throw(AssertionError("OpenAI image client should not be called")))

    result = generate_image_file("I read a book.", "book", 1, "cartoon", "English")

    assert result["success"] is False
    assert result["path"] is None
    assert result["url"] is None
    assert "disabled" in (result["error"] or "").lower()
    assert not (tmp_path / "book_1.png").exists()


def test_generate_image_file_rejects_solid_color_image(monkeypatch, openai_enabled):
    monkeypatch.setattr(Config, "USE_REAL_IMAGES", True)
    monkeypatch.setattr(Config, "AI_IMAGE_PROVIDER", "openai")
    solid_color_b64 = base64.b64encode(_make_solid_color_image_bytes()).decode("utf-8")

    fake_client = _FakeOpenAIClient(image_payloads=[solid_color_b64])
    monkeypatch.setattr(
        image_service,
        "_build_openai_client",
        lambda: fake_client,
    )

    failure_result = generate_image_file("I read a book.", "book", 1, "cartoon", "English")

    assert failure_result["success"] is False
    assert failure_result["path"] is None
    assert not (openai_enabled / "book_1.png").exists()
    error_text = (failure_result["error"] or "").lower()
    assert "dominant solid color" in error_text or "unique colors" in error_text


def test_generate_image_file_rejects_corrupted_and_non_image_bytes(monkeypatch, openai_enabled):
    monkeypatch.setattr(Config, "USE_REAL_IMAGES", True)
    monkeypatch.setattr(Config, "AI_IMAGE_PROVIDER", "openai")
    valid_b64 = base64.b64encode(_make_image_bytes()).decode("utf-8")
    invalid_b64 = base64.b64encode(b"not-a-real-image").decode("utf-8")
    html_b64 = base64.b64encode(b"<html><body>not image</body></html>").decode("utf-8")
    json_b64 = base64.b64encode(b'{"error":"not image"}').decode("utf-8")

    fake_client = _FakeOpenAIClient(image_payloads=[valid_b64, invalid_b64, html_b64, json_b64])
    monkeypatch.setattr(
        image_service,
        "_build_openai_client",
        lambda: fake_client,
    )

    success_result = generate_image_file("I read a book.", "book", 1, "cartoon", "English")
    corrupted_result = generate_image_file("I read a book.", "book", 2, "cartoon", "English")
    html_result = generate_image_file("I read a book.", "book", 3, "cartoon", "English")
    json_result = generate_image_file("I read a book.", "book", 4, "cartoon", "English")

    assert success_result["success"] is True
    assert success_result["path"].exists()
    assert corrupted_result["success"] is False
    assert corrupted_result["path"] is None
    assert html_result["success"] is False
    assert html_result["path"] is None
    assert json_result["success"] is False
    assert json_result["path"] is None
    assert not (openai_enabled / "book_2.png").exists()
    assert not (openai_enabled / "book_3.png").exists()
    assert not (openai_enabled / "book_4.png").exists()


def test_generate_audio_file_uses_gtts_provider_route(monkeypatch, tmp_path):
    monkeypatch.setattr(Config, "AUDIO_PROVIDER", "gtts")
    monkeypatch.setattr(Config, "USE_REAL_AUDIO", True)
    monkeypatch.setattr(Config, "AUDIO_DIR", tmp_path)

    saved_paths = []

    class FakeTTS:
        def __init__(self, text, lang, slow=False):
            self.text = text
            self.lang = lang
            self.slow = slow

        def save(self, path):
            saved_paths.append(path)
            Path(path).write_bytes(b"ID3\x00fake-mp3-data")

    monkeypatch.setattr(audio_service, "gTTS", FakeTTS)

    result_url = generate_audio("Je lis un livre.", "livre", 1, "French")

    assert result_url == "/generated/audio/livre_1.mp3"
    assert saved_paths
    assert (tmp_path / "livre_1.mp3").exists()


def test_generate_audio_file_returns_none_for_unsupported_provider(monkeypatch, tmp_path):
    monkeypatch.setattr(Config, "AUDIO_PROVIDER", "unsupported")
    monkeypatch.setattr(Config, "USE_REAL_AUDIO", True)
    monkeypatch.setattr(Config, "AUDIO_DIR", tmp_path)
    monkeypatch.setattr(audio_service, "generate_audio_with_gtts", lambda *args, **kwargs: (_ for _ in ()).throw(AssertionError("gTTS path should not be used")))

    result = generate_audio("Je lis un livre.", "livre", 1, "French")

    assert result is None


def test_generate_audio_file_writes_mp3(monkeypatch, tmp_path):
    monkeypatch.setattr(Config, "AUDIO_PROVIDER", "gtts")
    monkeypatch.setattr(Config, "USE_REAL_AUDIO", True)
    monkeypatch.setattr(Config, "AUDIO_DIR", tmp_path)

    saved_paths = []

    class FakeTTS:
        def __init__(self, text, lang, slow=False):
            self.text = text
            self.lang = lang
            self.slow = slow

        def save(self, path):
            saved_paths.append(path)
            Path(path).write_bytes(b"ID3\x00fake-mp3-data")

    monkeypatch.setattr(audio_service, "gTTS", FakeTTS)

    result_url = generate_audio_file("Je lis un livre.", "livre", 1, "French")

    assert result_url == "/generated/audio/livre_1.mp3"
    assert saved_paths
    assert (tmp_path / "livre_1.mp3").exists()
