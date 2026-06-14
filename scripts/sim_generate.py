import sys
from pathlib import Path
project_root = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(project_root))

from app.config import Config
from app.services.vocabulary_service import load_vocabulary
from app.services.sentence_service import generate_sentences
from app.services.audio_service import generate_audio_file
from app.services.image_service import generate_image_file

vocab = load_vocabulary()
word = vocab[0]['word']
meaning = vocab[0]['meaning']
print('word', word)
sentences = generate_sentences('French', word, vocab[:50], 1)
print('sentences', sentences)
for index, sentence in enumerate(sentences, start=1):
    audio_path = generate_audio_file(sentence, word, index)
    image_path = None
    # image retries - copy logic from routes
    safe_word = word.replace(' ', '_').lower()
    png_name = f"{safe_word}_{index}.png"
    png_path = Path(__file__).resolve().parent.parent / f"generated/images/{png_name}"
    for attempt in range(1,4):
        image_path = generate_image_file(sentence, word, index, 'cartoon')
        print('attempt', attempt, 'returned', image_path)
        try:
            if png_path.exists() and png_path.stat().st_size > 2000:
                image_path = f"/generated/images/{png_name}"
                break
            image_file = (Path(__file__).resolve().parent.parent / image_path.lstrip('/'))
            if image_file.exists() and image_file.suffix.lower() in ('.png','.jpg','.jpeg') and image_file.stat().st_size > 2000:
                break
        except Exception as e:
            print('check exception', e)
        print('retrying...')
    print('final image_path', image_path)
    # final override
    try:
        if png_path.exists() and png_path.stat().st_size > 2000:
            image_path = f"/generated/images/{png_name}"
    except Exception as e:
        print('final override exception', e)
    print('after final override image_path =', image_path)
