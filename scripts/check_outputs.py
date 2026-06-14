from pathlib import Path

def check():
    p1 = Path('generated/audio/je_1.mp3')
    p2 = Path('generated/images/je_1.png')
    print('audio exists', p1.exists(), 'size', p1.stat().st_size if p1.exists() else None)
    print('image exists', p2.exists(), 'size', p2.stat().st_size if p2.exists() else None)

if __name__ == '__main__':
    check()
