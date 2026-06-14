import sys
from pathlib import Path
project_root = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(project_root))

from app.services.image_service import generate_image_file


if __name__ == '__main__':
    res = generate_image_file('Je vois je.','je',1,'cartoon')
    print('result:', res)
