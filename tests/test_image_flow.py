from pathlib import Path

import pytest
from PIL import Image

from app import create_app
from app.config import Config
import app.routes as routes


@pytest.fixture()
def app_client(monkeypatch, tmp_path):
    original_image_dir = Config.IMAGE_DIR
    original_use_openai = Config.USE_OPENAI
    original_use_real_images = Config.USE_REAL_IMAGES
    original_load_vocabulary = routes.load_vocabulary
    original_generate_sentences = routes.generate_sentences
    original_generate_audio_file = routes.generate_audio_file
    original_generate_image_file = routes.generate_image_file

    monkeypatch.setattr(Config, "IMAGE_DIR", tmp_path)
    monkeypatch.setattr(Config, "USE_OPENAI", True)
    monkeypatch.setattr(Config, "USE_REAL_IMAGES", False)
    monkeypatch.setattr(routes, "load_vocabulary", lambda language: [{"word": "livre", "meaning": "book"}])
    monkeypatch.setattr(
        routes,
        "generate_sentences",
        lambda count=1, **kwargs: [
            {"sentence": f"sentence {index}", "translation": f"translation {index}"}
            for index in range(1, count + 1)
        ],
    )
    monkeypatch.setattr(routes, "generate_audio_file", lambda *args, **kwargs: None)
    monkeypatch.setattr(routes, "generate_image_file", original_generate_image_file)

    app = create_app()
    app.config.from_object(Config)

    client = app.test_client()

    yield client, tmp_path, monkeypatch

    monkeypatch.setattr(Config, "IMAGE_DIR", original_image_dir)
    monkeypatch.setattr(Config, "USE_OPENAI", original_use_openai)
    monkeypatch.setattr(Config, "USE_REAL_IMAGES", original_use_real_images)
    monkeypatch.setattr(routes, "load_vocabulary", original_load_vocabulary)
    monkeypatch.setattr(routes, "generate_sentences", original_generate_sentences)
    monkeypatch.setattr(routes, "generate_audio_file", original_generate_audio_file)
    monkeypatch.setattr(routes, "generate_image_file", original_generate_image_file)


def _make_valid_image(path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    image = Image.new("RGB", (128, 128))
    pixels = []
    for y in range(128):
        for x in range(128):
            pixels.append(((x * 17 + 3) % 256, (y * 29 + 7) % 256, ((x + y) * 13 + 11) % 256))
    image.putdata(pixels)
    image.save(path, format="BMP")


def _post_generate(client, *, language="French", target_words=1, sentences_per_word=1, custom_word="", image_style="cartoon"):
    return client.post(
        "/generate",
        data={
            "language": language,
            "target_words": target_words,
            "sentences_per_word": sentences_per_word,
            "allowed_range": 50,
            "image_style": image_style,
            "custom_word": custom_word,
        },
    )


def test_image_flow_a_use_real_images_false_and_no_existing_image_shows_disabled(app_client):
    client, tmp_path, monkeypatch = app_client
    monkeypatch.setattr(Config, "USE_REAL_IMAGES", False)
    monkeypatch.setattr(routes, "generate_image_file", lambda *args, **kwargs: (_ for _ in ()).throw(AssertionError("image generation should not run")))
    response = _post_generate(client)

    assert response.status_code == 200
    html = response.get_data(as_text=True)
    assert "Image disabled" in html
    assert "Image unavailable" not in html
    assert "generated-image" not in html
    assert not any(tmp_path.glob("*.png"))


def test_image_flow_b_use_real_images_false_but_valid_existing_png_still_shows_disabled(app_client):
    client, tmp_path, monkeypatch = app_client
    monkeypatch.setattr(Config, "USE_REAL_IMAGES", False)
    _make_valid_image(tmp_path / "livre_1.png")

    response = _post_generate(client)

    assert response.status_code == 200
    html = response.get_data(as_text=True)
    assert 'class="generated-image"' not in html
    assert "Image disabled" in html
    assert "Image unavailable" not in html


def test_image_flow_c_use_real_images_true_but_provider_fails_shows_unavailable(app_client):
    client, tmp_path, monkeypatch = app_client
    monkeypatch.setattr(Config, "USE_REAL_IMAGES", True)
    monkeypatch.setattr(routes, "generate_image_file", lambda *args, **kwargs: {"success": False, "error": "provider failed"})

    response = _post_generate(client)

    assert response.status_code == 200
    html = response.get_data(as_text=True)
    assert "Image unavailable" in html
    assert 'class="generated-image"' not in html
    assert "Image disabled" not in html


def test_image_flow_d_use_real_images_true_and_provider_succeeds_displays_image(app_client):
    client, tmp_path, monkeypatch = app_client
    monkeypatch.setattr(Config, "USE_REAL_IMAGES", True)

    def successful_generate(sentence, word, sentence_number, style, language, mode="normal"):
        base_name = word.strip().lower().replace(" ", "_")
        image_path = tmp_path / f"{base_name}_{sentence_number}.png"
        _make_valid_image(image_path)
        return {"success": True, "path": image_path, "url": f"/generated/images/{image_path.name}"}

    monkeypatch.setattr(routes, "generate_image_file", successful_generate)

    response = _post_generate(client)

    assert response.status_code == 200
    html = response.get_data(as_text=True)
    assert 'class="generated-image"' in html
    assert "Image unavailable" not in html
    assert "Image disabled" not in html


def test_image_flow_e_custom_word_three_sentences_handle_each_sentence_independently(app_client):
    client, tmp_path, monkeypatch = app_client
    monkeypatch.setattr(Config, "USE_REAL_IMAGES", True)

    def selective_generate(sentence, word, sentence_number, style, language, mode="normal"):
        base_name = word.strip().lower().replace(" ", "_")
        image_path = tmp_path / f"{base_name}_{sentence_number}.png"
        if sentence_number in {1, 3}:
            _make_valid_image(image_path)
            return {"success": True, "path": image_path, "url": f"/generated/images/{image_path.name}"}
        return {"success": False, "error": "missing image"}

    monkeypatch.setattr(routes, "generate_image_file", selective_generate)

    response = _post_generate(client, sentences_per_word=3, custom_word="livre")

    assert response.status_code == 200
    html = response.get_data(as_text=True)
    assert html.count('class="generated-image"') == 2
    assert html.count("Image unavailable") == 1


def test_image_flow_f_normal_mode_three_sentences_handle_each_sentence_independently(app_client):
    client, tmp_path, monkeypatch = app_client
    monkeypatch.setattr(Config, "USE_REAL_IMAGES", True)

    def selective_generate(sentence, word, sentence_number, style, language, mode="normal"):
        base_name = word.strip().lower().replace(" ", "_")
        image_path = tmp_path / f"{base_name}_{sentence_number}.png"
        if sentence_number in {1, 3}:
            _make_valid_image(image_path)
            return {"success": True, "path": image_path, "url": f"/generated/images/{image_path.name}"}
        return {"success": False, "error": "missing image"}

    monkeypatch.setattr(routes, "generate_image_file", selective_generate)

    response = _post_generate(client, sentences_per_word=3)

    assert response.status_code == 200
    html = response.get_data(as_text=True)
    assert html.count('class="generated-image"') == 2
    assert html.count("Image unavailable") == 1


def test_custom_word_maison_one_sentence_uses_expected_image_filename(app_client):
    client, tmp_path, monkeypatch = app_client
    monkeypatch.setattr(Config, "USE_REAL_IMAGES", True)

    captured = {}

    def successful_generate(sentence, word, sentence_number, style, language, mode="normal"):
        base_name = word.strip().lower().replace(" ", "_")
        image_path = tmp_path / f"{base_name}_{sentence_number}.png"
        _make_valid_image(image_path)
        captured["filename"] = image_path.name
        captured["mode"] = mode
        return {"success": True, "path": image_path, "url": f"/generated/images/{image_path.name}"}

    monkeypatch.setattr(routes, "generate_image_file", successful_generate)

    response = _post_generate(client, custom_word="maison", sentences_per_word=1)

    assert response.status_code == 200
    assert captured.get("filename") == "maison_1.png"
    assert captured.get("mode") == "custom"
    html = response.get_data(as_text=True)
    assert 'src="/generated/images/maison_1.png' in html