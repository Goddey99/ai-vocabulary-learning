import sys
from pathlib import Path
project_root = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(project_root))

from app.services.sentence_service import generate_sentences
from app.services.audio_service import generate_audio_file
from app.services.image_service import generate_image_file
from app.services.vocabulary_service import load_vocabulary

def run_one():
    vocab = load_vocabulary()
    word = vocab[0]['word']
    print('Word:', word)
    sentences = generate_sentences('French', word, vocab[:50], 1)
    print('Sentences:', sentences)
    s = sentences[0]
    try:
        audio = generate_audio_file(s, word, 1)
        print('Audio path:', audio)
    except Exception as e:
        print('Audio error:', e)
    try:
        image = generate_image_file(s, word, 1, 'cartoon')
        print('Image path:', image)
    except Exception as e:
        print('Image error:', e)

if __name__ == '__main__':
    run_one()
