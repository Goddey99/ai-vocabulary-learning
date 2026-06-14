from app.routes import should_show_translation
from app import create_app
from app.config import Config
import app.routes as routes


def test_should_show_translation_hides_identical_case_insensitive():
    assert should_show_translation("the", "the") is False
    assert should_show_translation("The", "the") is False
    assert should_show_translation("maison", "Maison") is False
    assert should_show_translation("The Time Is Now", "the time is now") is False


def test_should_show_translation_shows_different_values():
    assert should_show_translation("maison", "house") is True
    assert should_show_translation("livre", "book") is True


def test_translation_rendering_hides_identical_translation(monkeypatch):
    monkeypatch.setattr(Config, "USE_OPENAI", False)
    monkeypatch.setattr(routes, "load_vocabulary", lambda language: [{"word": "house", "meaning": "house"}])
    monkeypatch.setattr(
        routes,
        "generate_sentences",
        lambda **kwargs: [{"sentence": "The time is now.", "translation": "the time is now."}],
    )
    monkeypatch.setattr(routes, "generate_audio_file", lambda *args, **kwargs: None)
    monkeypatch.setattr(routes, "generate_image_file", lambda *args, **kwargs: {"success": False, "error": "disabled"})

    app = create_app()
    app.config.from_object(Config)
    client = app.test_client()

    response = client.post(
        "/generate",
        data={
            "language": "English",
            "target_words": 1,
            "sentences_per_word": 1,
            "allowed_range": 50,
            "image_style": "cartoon",
            "custom_word": "",
        },
    )

    html = response.get_data(as_text=True)
    assert response.status_code == 200
    assert html.count('class="translation"') == 0
    assert "The time is now." in html


def test_translation_rendering_shows_different_translation(monkeypatch):
    monkeypatch.setattr(Config, "USE_OPENAI", False)
    monkeypatch.setattr(routes, "load_vocabulary", lambda language: [{"word": "maison", "meaning": "house"}])
    monkeypatch.setattr(
        routes,
        "generate_sentences",
        lambda **kwargs: [{"sentence": "Je vois la maison.", "translation": "I see the house."}],
    )
    monkeypatch.setattr(routes, "generate_audio_file", lambda *args, **kwargs: None)
    monkeypatch.setattr(routes, "generate_image_file", lambda *args, **kwargs: {"success": False, "error": "disabled"})

    app = create_app()
    app.config.from_object(Config)
    client = app.test_client()

    response = client.post(
        "/generate",
        data={
            "language": "French",
            "target_words": 1,
            "sentences_per_word": 1,
            "allowed_range": 50,
            "image_style": "cartoon",
            "custom_word": "",
        },
    )

    html = response.get_data(as_text=True)
    assert response.status_code == 200
    assert 'class="translation"' in html
    assert "I see the house." in html


def test_translation_rendering_hides_case_insensitive_sentence_translation(monkeypatch):
    monkeypatch.setattr(Config, "USE_OPENAI", False)
    monkeypatch.setattr(routes, "load_vocabulary", lambda language: [{"word": "house", "meaning": "house"}])
    monkeypatch.setattr(
        routes,
        "generate_sentences",
        lambda **kwargs: [{"sentence": "The time is now.", "translation": "the time is now."}],
    )
    monkeypatch.setattr(routes, "generate_audio_file", lambda *args, **kwargs: None)
    monkeypatch.setattr(routes, "generate_image_file", lambda *args, **kwargs: {"success": False, "error": "disabled"})

    app = create_app()
    app.config.from_object(Config)
    client = app.test_client()

    response = client.post(
        "/generate",
        data={
            "language": "English",
            "target_words": 1,
            "sentences_per_word": 1,
            "allowed_range": 50,
            "image_style": "cartoon",
            "custom_word": "",
        },
    )

    html = response.get_data(as_text=True)
    assert response.status_code == 200
    assert html.count('class="translation"') == 0
