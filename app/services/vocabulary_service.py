import csv
from pathlib import Path

from app.config import Config


VOCABULARY_FILES = {
    "french": "french_frequency_words.csv",
    "english": "english_frequency_words.csv",
    "spanish": "spanish_frequency_words.csv",
    "german": "german_frequency_words.csv",
    "chinese": "chinese_frequency_words.csv",
}

STOPWORDS_BY_LANGUAGE = {
    "english": {
        "the", "a", "an", "of", "to", "and", "is", "are", "in", "on",
        "for", "with", "from", "into", "onto", "over", "under", "between",
        "through", "about", "after", "before", "during", "without", "around",
        "this", "that", "these", "those", "here", "there", "have", "has",
        "had", "was", "were", "been", "being", "can", "could", "would",
        "should", "do", "does", "did", "at", "by", "as", "or", "but", "if",
        "because", "while", "than", "then", "so", "very", "too", "just",
    },
    "french": {
        "le", "la", "les", "de", "des", "du", "et", "est", "dans", "un", "une",
        "pour", "avec", "dans", "sur", "sous", "entre", "ce", "cette", "ces",
        "être", "avoir", "fait", "faites", "comme", "chez", "sans", "au", "aux",
        "en", "par", "sur", "sous", "vers", "qui", "que", "quoi", "dont",
        "où", "ici", "là", "cela", "ça", "ont", "a", "es", "sont", "été",
        "être", "faire", "fait", "font", "pouvoir", "peut", "doit", "devrait",
    },
    "chinese": {
        "的", "了", "在", "是", "我", "有", "和", "不", "你", "他", "她", "们",
        "这", "那", "也", "就", "都", "很", "还", "与", "而", "从", "到", "给",
    },
}

PREFERRED_WORDS_BY_LANGUAGE = {
    "english": {
        "house", "school", "teacher", "music", "family", "garden", "dog", "food",
        "travel", "book", "friend", "child", "water", "car", "city", "work",
        "play", "learn", "home", "room", "tree", "park", "time", "day", "night",
        "read", "write", "speak", "study", "walk", "love", "eat", "live", "happy",
        "small", "big", "new", "old", "good", "beautiful", "fun", "easy", "bright",
    },
    "french": {
        "maison", "école", "ecole", "famille", "musique", "livre", "ami", "amie",
        "chien", "nourriture", "voyage", "jardin", "professeur", "maître", "maitre",
        "eau", "voiture", "ville", "travail", "jeu", "apprendre", "lire", "écrire",
        "ecrire", "parler", "étudier", "etudier", "marcher", "aimer", "vivre", "heureux",
        "heureuse", "petit", "grande", "nouveau", "nouvelle", "bon", "bonne", "beau",
        "belle", "temps", "jour", "nuit", "chambre", "arbre", "parc", "simple",
    },
    "chinese": {
        "学校", "老师", "学生", "朋友", "家", "书", "水", "狗", "饭", "城市",
        "家庭", "花园", "音乐", "旅行", "工作", "学习", "生活", "孩子", "房间", "树",
        "公园", "时间", "白天", "晚上", "阅读", "写", "说", "走", "爱", "吃",
        "好", "小", "大", "新", "旧", "漂亮", "简单", "快乐",
    },
}


def normalize_language(language):
    return (language or Config.DEFAULT_LANGUAGE).strip().lower()


def normalize_word(word):
    return (word or "").strip().casefold()


def get_stopwords(language):
    return STOPWORDS_BY_LANGUAGE.get(normalize_language(language), set())


def get_preferred_words(language):
    return PREFERRED_WORDS_BY_LANGUAGE.get(normalize_language(language), set())


def score_vocabulary_item(item, language):
    # Scoring emphasizes semantically meaningful words over function words for beginner study value.
    word = normalize_word(item.get("word"))
    if not word:
        return 0

    preferred_words = get_preferred_words(language)
    score = 0

    if word in preferred_words:
        score += 100

    if any(char.isalpha() for char in word):
        score += 10

    if len(word) >= 4:
        score += min(len(word), 12)

    if len(word) >= 6:
        score += 5

    if len(word) >= 8:
        score += 5

    rank = item.get("rank")
    try:
        rank_value = int(rank) if rank is not None else 0
    except (TypeError, ValueError):
        rank_value = 0

    if rank_value > 0:
        score += max(0, 40 - min(rank_value, 40))

    return score


def get_vocabulary_file(language):
    filename = VOCABULARY_FILES.get(
        normalize_language(language),
        VOCABULARY_FILES["french"]
    )

    return Config.DATA_DIR / filename


def load_vocabulary(language=Config.DEFAULT_LANGUAGE):
    # Language-specific frequency lists are the source of truth for reproducible vocabulary selection.
    vocabulary = []
    vocabulary_file = get_vocabulary_file(language)

    with open(vocabulary_file, mode="r", encoding="utf-8") as file:
        reader = csv.DictReader(file)

        for row in reader:
            vocabulary.append({
                "rank": int(row["rank"]),
                "word": row["word"].strip(),
                "meaning": row["meaning"].strip()
            })

    return vocabulary


def filter_vocabulary_for_selection(vocabulary, language):
    # Stopword filtering removes high-frequency connectors so selected targets are pedagogically useful.
    stopwords = get_stopwords(language)
    filtered_vocabulary = []
    filtered_stopwords_count = 0

    for item in vocabulary:
        word = normalize_word(item.get("word"))
        if word and word in stopwords:
            filtered_stopwords_count += 1
            continue
        filtered_vocabulary.append(item)

    return filtered_vocabulary, filtered_stopwords_count


def select_vocabulary_words(vocabulary, language, target_words):
    # Selection pipeline: filter, score, rank, and trim to keep output consistent and explainable.
    filtered_vocabulary, filtered_stopwords_count = filter_vocabulary_for_selection(vocabulary, language)
    # Fallback ensures generation still works when filtering removes all candidates.
    selected_pool = filtered_vocabulary or vocabulary
    scored_words = [
        {**item, "score": score_vocabulary_item(item, language), "selection_index": index}
        for index, item in enumerate(selected_pool)
    ]
    # Stable tie-breaking preserves deterministic ordering across runs and simplifies testing.
    scored_words.sort(
        key=lambda item: (
            -int(item.get("score", 0) or 0),
            int(item.get("rank", 10**9) or 10**9),
            int(item.get("selection_index", 10**9) or 10**9),
        )
    )
    # Final slice applies the user-selected target-word count after ranking.
    selected_words = scored_words[:target_words]
    fallback_used = not filtered_vocabulary
    return {
        "selected_words": selected_words,
        "filtered_vocabulary": filtered_vocabulary,
        "filtered_stopwords_count": filtered_stopwords_count,
        "fallback_used": fallback_used,
        "vocabulary_score": [(item.get("word"), item.get("score", 0)) for item in selected_words],
    }
