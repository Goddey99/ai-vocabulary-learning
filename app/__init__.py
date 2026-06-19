from pathlib import Path

from flask import Flask
from .config import Config
from .routes import main


def create_app():
    app = Flask(__name__)
    app.config.from_object("app.config.Config")
    app.register_blueprint(main)

    @app.context_processor
    def inject_form_values():
        return {
            "form_values": {
                "language": Config.DEFAULT_LANGUAGE,
                "target_words": 10,
                "sentences_per_word": 2,
                "allowed_range": 50,
                "image_style": "cartoon",
                "custom_word": "",
            },
            "supported_languages": Config.SUPPORTED_LANGUAGES,
        }

    log_dir = Path(app.instance_path)
    log_dir.mkdir(parents=True, exist_ok=True)
    request_log_path = log_dir / "request.log"

    @app.before_request
    def log_incoming_request():
        try:
            import sys
            proto = "HTTP/1.1"
            method = getattr(__import__('flask').request, 'method', '?')
            path = getattr(__import__('flask').request, 'path', '?')
            log_line = f"{method} {path} {proto}"
            print(log_line, file=sys.stdout)
            sys.stdout.flush()
            with request_log_path.open("a", encoding="utf-8") as log_file:
                log_file.write(log_line + "\n")
        except Exception:
            pass

    # Template helper to resolve generated asset URLs to real PNG/MP3 when present
    def resolve_generated_asset(url_path: str) -> str:
        try:
            from pathlib import Path
            root = Path(__file__).resolve().parent.parent
            if not url_path:
                return url_path

            # images: prefer a png with the same base name
            if url_path.startswith("/generated/images/"):
                name = url_path.split("/")[-1]
                # if it's an image prompt file, derive the base name before _image_prompt
                if name.endswith("_image_prompt.txt"):
                    base = name[: -len("_image_prompt.txt")]
                    png_name = f"{base}.png"
                else:
                    png_name = name

                png_path = root / "generated" / "images" / png_name
                if png_path.exists() and png_path.stat().st_size > 2000:
                    return f"/generated/images/{png_name}"
                return url_path

            # audio: prefer mp3 with same base name
            if url_path.startswith("/generated/audio/"):
                name = url_path.split("/")[-1]
                mp3_name = name
                if not mp3_name.lower().endswith('.mp3'):
                    mp3_name = mp3_name + '.mp3'
                mp3_path = root / "generated" / "audio" / mp3_name
                if mp3_path.exists() and mp3_path.stat().st_size > 1000:
                    return f"/generated/audio/{mp3_name}"
                return url_path

            return url_path
        except Exception:
            return url_path

    app.jinja_env.globals['resolve_generated_asset'] = resolve_generated_asset

    return app
