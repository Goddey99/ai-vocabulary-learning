from app import create_app
from app.config import Config
import app.routes as routes


def test_stopwords_excluded_from_vocabulary_selection(monkeypatch):
    captured_words = []

    monkeypatch.setattr(Config, "USE_OPENAI", False)
    monkeypatch.setattr(
        routes,
        "load_vocabulary",
        lambda language: [
            {"word": "the", "meaning": "the"},
            {"word": "house", "meaning": "house"},
            {"word": "and", "meaning": "and"},
            {"word": "school", "meaning": "school"},
        ],
    )

    def fake_generate_sentences(**kwargs):
        captured_words.append(kwargs["target_word"])
        return [{"sentence": "A clean sentence.", "translation": "A clean translation."}]

    monkeypatch.setattr(routes, "generate_sentences", fake_generate_sentences)
    monkeypatch.setattr(routes, "generate_audio_file", lambda *args, **kwargs: None)
    monkeypatch.setattr(routes, "generate_image_file", lambda *args, **kwargs: {"success": False, "error": "disabled"})

    app = create_app()
    app.config.from_object(Config)
    client = app.test_client()

    response = client.post(
        "/generate",
        data={
            "language": "English",
            "target_words": 2,
            "sentences_per_word": 1,
            "allowed_range": 50,
            "image_style": "cartoon",
            "custom_word": "",
        },
    )

    assert response.status_code == 200
    assert set(captured_words) == {"house", "school"}
    assert all(word not in {"the", "and"} for word in captured_words)


def test_meaningful_words_are_preferred_over_weak_connectors(monkeypatch):
    captured_words = []

    monkeypatch.setattr(Config, "USE_OPENAI", False)
    monkeypatch.setattr(
        routes,
        "load_vocabulary",
        lambda language: [
            {"word": "for", "meaning": "for"},
            {"word": "with", "meaning": "with"},
            {"word": "house", "meaning": "house"},
            {"word": "school", "meaning": "school"},
            {"word": "music", "meaning": "music"},
        ],
    )

    def fake_generate_sentences(**kwargs):
        captured_words.append(kwargs["target_word"])
        return [{"sentence": "A clean sentence.", "translation": "A clean translation."}]

    monkeypatch.setattr(routes, "generate_sentences", fake_generate_sentences)
    monkeypatch.setattr(routes, "generate_audio_file", lambda *args, **kwargs: None)
    monkeypatch.setattr(routes, "generate_image_file", lambda *args, **kwargs: {"success": False, "error": "disabled"})

    app = create_app()
    app.config.from_object(Config)
    client = app.test_client()

    response = client.post(
        "/generate",
        data={
            "language": "English",
            "target_words": 3,
            "sentences_per_word": 1,
            "allowed_range": 50,
            "image_style": "cartoon",
            "custom_word": "",
        },
    )

    assert response.status_code == 200
    assert set(captured_words) == {"house", "school", "music"}
    assert all(word not in {"for", "with"} for word in captured_words)


def test_stopword_filter_falls_back_gracefully_when_no_meaningful_words(monkeypatch, capsys):
    captured_words = []

    monkeypatch.setattr(Config, "USE_OPENAI", False)
    monkeypatch.setattr(
        routes,
        "load_vocabulary",
        lambda language: [
            {"word": "the", "meaning": "the"},
            {"word": "and", "meaning": "and"},
        ],
    )

    def fake_generate_sentences(**kwargs):
        captured_words.append(kwargs["target_word"])
        return [{"sentence": "Fallback sentence.", "translation": "Fallback translation."}]

    monkeypatch.setattr(routes, "generate_sentences", fake_generate_sentences)
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

    captured = capsys.readouterr().out
    assert response.status_code == 200
    assert len(captured_words) == 1
    assert captured_words[0] in {"the", "and"}
    assert "VOCABULARY_FILTER_FALLBACK_USED = True" in captured
    assert "FILTERED_STOPWORDS_COUNT = 2" in captured


def test_tiny_vocabulary_set_does_not_crash(monkeypatch):
    captured_words = []

    monkeypatch.setattr(Config, "USE_OPENAI", False)
    monkeypatch.setattr(
        routes,
        "load_vocabulary",
        lambda language: [{"word": "house", "meaning": "house"}],
    )

    def fake_generate_sentences(**kwargs):
        captured_words.append(kwargs["target_word"])
        return [{"sentence": "A tiny set sentence.", "translation": "A tiny set translation."}]

    monkeypatch.setattr(routes, "generate_sentences", fake_generate_sentences)
    monkeypatch.setattr(routes, "generate_audio_file", lambda *args, **kwargs: None)
    monkeypatch.setattr(routes, "generate_image_file", lambda *args, **kwargs: {"success": False, "error": "disabled"})

    app = create_app()
    app.config.from_object(Config)
    client = app.test_client()

    response = client.post(
        "/generate",
        data={
            "language": "English",
            "target_words": 3,
            "sentences_per_word": 1,
            "allowed_range": 50,
            "image_style": "cartoon",
            "custom_word": "",
        },
    )

    assert response.status_code == 200
    assert captured_words == ["house"]
