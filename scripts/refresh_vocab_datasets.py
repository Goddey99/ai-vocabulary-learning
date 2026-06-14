from __future__ import annotations

import csv
import re
import sys
import time
from pathlib import Path
from typing import Iterable

import requests

ROOT = Path(__file__).resolve().parent.parent
DATA_DIR = ROOT / "data"
SOURCE_URL = "https://raw.githubusercontent.com/hermitdave/FrequencyWords/master/content/2018/{code}/{code}_50k.txt"
TARGET_COUNT = 200

LANGUAGES = {
    "French": {
        "code": "fr",
        "filename": "french_frequency_words.csv",
        "overrides": {
            "de": "of/from",
            "je": "I",
            "est": "is",
            "pas": "not",
            "le": "the",
            "la": "the",
            "les": "the",
            "que": "that/which",
            "vous": "you",
            "tu": "you",
            "un": "a/an",
            "une": "a/an",
            "à": "to/at",
            "et": "and",
            "il": "he/it",
            "a": "has",
            "ne": "not",
            "en": "in",
            "on": "one/we",
            "ça": "that/it",
            "des": "some/of the",
            "qui": "who/which",
            "mais": "but",
            "dans": "in",
            "nous": "we",
            "elle": "she",
            "me": "me",
            "bien": "well",
            "si": "if",
            "du": "of the/from the",
            "y": "there",
            "suis": "am",
            "non": "no",
            "avec": "with",
            "tout": "everything/all",
            "plus": "more",
            "mon": "my",
            "te": "you",
            "au": "to the/at the",
            "pour": "for",
            "ai": "have",
            "son": "his/her",
            "se": "oneself",
            "ce": "this",
            "qu'": "that/what",
            "par": "by",
            "sur": "on",
            "ils": "they",
            "très": "very",
            "comme": "like/as",
            "mais": "but",
            "où": "where",
            "sans": "without",
            "contre": "against",
            "bien": "well",
            "toujours": "always",
            "encore": "again",
            "avant": "before",
            "après": "after",
        },
    },
    "English": {
        "code": "en",
        "filename": "english_frequency_words.csv",
        "overrides": {},
    },
    "Spanish": {
        "code": "es",
        "filename": "spanish_frequency_words.csv",
        "overrides": {
            "qué": "what",
            "yo": "I",
            "no": "not",
            "la": "the",
            "el": "the",
            "y": "and",
            "es": "is",
            "en": "in",
            "lo": "it",
            "un": "a/an",
            "una": "a/an",
            "por": "for/by",
            "me": "me",
            "se": "oneself",
            "te": "you",
            "con": "with",
            "para": "for",
            "está": "is",
            "mi": "my",
            "pero": "but",
            "sí": "yes",
            "si": "if",
            "bien": "well",
            "eso": "that",
            "su": "his/her/their",
            "los": "the",
            "las": "the",
            "del": "of the",
            "como": "like/as",
            "aquí": "here",
            "tu": "your/you",
            "al": "to the",
            "más": "more",
            "le": "to him/her",
            "esto": "this",
            "todo": "everything/all",
            "ya": "already",
            "estoy": "I am",
            "ahora": "now",
            "muy": "very",
            "ha": "has",
            "esta": "this",
            "así": "like this",
            "vamos": "let's go / we go",
            "algo": "something",
            "hay": "there is/are",
            "bueno": "good",
            "ayer": "yesterday",
            "hoy": "today",
            "mañana": "tomorrow",
        },
    },
    "German": {
        "code": "de",
        "filename": "german_frequency_words.csv",
        "overrides": {
            "ich": "I",
            "sie": "she/they",
            "das": "the/that",
            "ist": "is",
            "du": "you",
            "nicht": "not",
            "die": "the",
            "es": "it",
            "und": "and",
            "der": "the",
            "wir": "we",
            "was": "what",
            "zu": "to",
            "er": "he",
            "ein": "a/an",
            "in": "in",
            "ja": "yes",
            "mir": "me",
            "mit": "with",
            "wie": "how/like",
            "den": "the",
            "mich": "me",
            "auf": "on/up",
            "dass": "that",
            "aber": "but",
            "eine": "a/an",
            "so": "so",
            "hat": "has",
            "hier": "here",
            "haben": "have",
            "für": "for",
            "sind": "are",
            "war": "was",
            "von": "of/from",
            "wenn": "if/when",
            "dich": "you",
            "ihr": "you/they",
            "nein": "no",
            "habe": "have",
            "an": "on/at",
            "bin": "am",
            "noch": "still/yet",
            "nur": "only",
            "da": "there",
            "dir": "you",
            "sich": "oneself",
            "einen": "a/an",
            "uns": "us",
            "hast": "have",
            "dem": "the",
            "keinen": "no/none",
            "mutter": "mother",
            "gemacht": "made",
            "paar": "few/pair",
            "jetzt": "now",
            "gut": "good",
            "hier": "here",
            "heute": "today",
            "morgen": "tomorrow",
        },
    },
}

NON_WORD_RE = re.compile(r"^[^\wÀ-ÿ]+$", re.UNICODE)


def fetch_source_words(code: str, limit: int = TARGET_COUNT) -> list[str]:
    url = SOURCE_URL.format(code=code)
    response = requests.get(url, timeout=30)
    response.raise_for_status()

    words: list[str] = []
    seen: set[str] = set()

    for raw_line in response.text.splitlines():
        token = raw_line.split()[0].strip()
        if not token:
            continue
        if NON_WORD_RE.match(token):
            continue
        lowered = token.lower()
        if lowered in seen:
            continue
        seen.add(lowered)
        words.append(token)
        if len(words) >= limit:
            break

    return words


def translate_word(word: str, source_lang: str, overrides: dict[str, str]) -> str:
    normalized = word.strip().lower()
    if normalized in overrides:
        return overrides[normalized]

    if source_lang == "en":
        return word

    params = {
        "client": "gtx",
        "sl": source_lang,
        "tl": "en",
        "dt": "t",
        "q": word,
    }
    try:
        response = requests.get("https://translate.googleapis.com/translate_a/single", params=params, timeout=30)
        response.raise_for_status()
        payload = response.json()
        translated = "".join(part[0] for part in payload[0] if part and part[0]).strip()
        return translated or word
    except Exception:
        return word


def write_csv(path: Path, rows: list[tuple[int, str, str]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="") as file:
        writer = csv.writer(file)
        writer.writerow(["rank", "word", "meaning"])
        writer.writerows(rows)


def validate_csv(path: Path) -> None:
    with path.open("r", encoding="utf-8", newline="") as file:
        reader = csv.DictReader(file)
        if reader.fieldnames != ["rank", "word", "meaning"]:
            raise ValueError(f"{path.name}: invalid columns {reader.fieldnames}")

        rows = list(reader)
        if len(rows) < TARGET_COUNT:
            raise ValueError(f"{path.name}: expected at least {TARGET_COUNT} rows, found {len(rows)}")

        for index, row in enumerate(rows, start=1):
            if int(row["rank"]) != index:
                raise ValueError(f"{path.name}: rank mismatch at row {index} -> {row['rank']}")
            if not row["word"].strip():
                raise ValueError(f"{path.name}: empty word at row {index}")
            if not row["meaning"].strip():
                raise ValueError(f"{path.name}: empty meaning at row {index}")


def build_dataset(language_name: str, config: dict[str, object]) -> list[tuple[int, str, str]]:
    code = config["code"]
    overrides = config["overrides"]
    source_words = fetch_source_words(code, TARGET_COUNT)
    rows: list[tuple[int, str, str]] = []

    for rank, word in enumerate(source_words, start=1):
        meaning = translate_word(word, code, overrides)
        rows.append((rank, word, meaning))

    return rows


def main() -> None:
    if "--validate-only" in sys.argv:
        for language_name, config in LANGUAGES.items():
            validate_csv(DATA_DIR / config["filename"])
            print(f"Validated {language_name}")
        return

    for language_name, config in LANGUAGES.items():
        rows = build_dataset(language_name, config)
        path = DATA_DIR / config["filename"]
        write_csv(path, rows)
        validate_csv(path)
        print(f"Wrote and validated {path.name}: {len(rows)} rows")

    try:
        from app.services.vocabulary_service import load_vocabulary

        for language_name in LANGUAGES:
            vocabulary = load_vocabulary(language_name)
            if len(vocabulary) < TARGET_COUNT:
                raise ValueError(f"{language_name}: load_vocabulary returned {len(vocabulary)} rows")
            print(f"Loaded {language_name}: {len(vocabulary)} rows")
    except Exception as error:
        raise SystemExit(f"Vocabulary loading validation failed: {error}")


if __name__ == "__main__":
    main()
