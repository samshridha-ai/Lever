from pathlib import Path

ROOT = Path(__file__).resolve().parent
DATABASE = ROOT / "lever.db"
MODEL_PATH = ROOT / "saved_models" / "model.joblib"
METADATA_PATH = ROOT / "saved_models" / "metadata.joblib"
SECRET_KEY = "change-this-for-production"
