import os
from pathlib import Path
from dotenv import load_dotenv

BASE_DIR = Path(__file__).resolve().parent
ENV_FILE = BASE_DIR / ".env"
load_dotenv(ENV_FILE)

UPLOAD_FOLDER = BASE_DIR / "uploads"
UPLOAD_FOLDER.mkdir(exist_ok=True)

DATABASE = UPLOAD_FOLDER / "database.db"
SETTINGS_FILE = BASE_DIR / "settings.json"
SECRET_KEY = os.getenv("SECRET_KEY", "assignment_ui_secret_key_2026")
