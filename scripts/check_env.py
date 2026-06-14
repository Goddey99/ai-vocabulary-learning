import sys
from pathlib import Path
import importlib.util
project_root = Path(__file__).resolve().parent.parent
env_path = project_root / '.env'

def read_env():
    data = {}
    if env_path.exists():
        for line in env_path.read_text(encoding='utf-8').splitlines():
            line = line.strip()
            if not line or line.startswith('#'):
                continue
            if '=' in line:
                k,v = line.split('=',1)
                data[k.strip()] = v.strip()
    return data
import subprocess
import sys

def print_config():
    env = read_env()
    print('OPENAI_API_KEY=' + repr(env.get('OPENAI_API_KEY')))
    print('USE_OPENAI=' + str(env.get('USE_OPENAI')))
    print('USE_REAL_AUDIO=' + str(env.get('USE_REAL_AUDIO')))
    print('OPENAI_TEXT_MODEL=' + str(env.get('OPENAI_TEXT_MODEL')))
    print('OPENAI_IMAGE_MODEL=' + str(env.get('OPENAI_IMAGE_MODEL')))

def check_packages():
    pkgs = ['openai', 'requests', 'gtts']
    for p in pkgs:
        spec = importlib.util.find_spec(p)
        print(f"{p}: {'installed' if spec else 'MISSING'}")

def pip_show(pkgs):
    for pkg in pkgs:
        try:
            res = subprocess.run([sys.executable, '-m', 'pip', 'show', pkg], capture_output=True, text=True)
            if res.returncode == 0 and res.stdout:
                first = res.stdout.splitlines()[0]
                print(f"pip show {pkg}: {first}")
            else:
                print(f"pip show {pkg}: not installed")
        except Exception as e:
            print(f"pip show {pkg}: error: {e}")

if __name__ == '__main__':
    print('--- Config values ---')
    print_config()
    print('\n--- Package availability ---')
    check_packages()
    print('\n--- pip show ---')
    pip_show(['openai', 'requests', 'gTTS'])
