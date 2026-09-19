import os
from pathlib import Path

ROOT = Path(__file__).resolve().parent

DATABASE = ROOT / "lever.db"
DATABASE_URL = os.getenv("DATABASE_URL")

MODEL_PATH = ROOT / "saved_models" / "model.joblib"
METADATA_PATH = ROOT / "saved_models" / "metadata.joblib"

SECRET_KEY = os.getenv("SECRET_KEY", "change-this-for-production")
