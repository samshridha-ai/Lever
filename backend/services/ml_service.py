import json
from pathlib import Path
import joblib
import numpy as np
import pandas as pd
import shap
from config import MODEL_PATH, METADATA_PATH

_model = _metadata = None

def load_model():
    global _model, _metadata
    if _model is None:
        if not MODEL_PATH.exists() or not METADATA_PATH.exists():
            raise RuntimeError('Model files are missing. Run python backend/scripts/train_model.py first.')
        _model, _metadata = joblib.load(MODEL_PATH), joblib.load(METADATA_PATH)
    return _model, _metadata

def predict(features):
    model, metadata = load_model()
    row = {key: features.get(key) for key in metadata['features']}
    prediction = float(model.predict(pd.DataFrame([row], columns=metadata['features']))[0])
    return prediction, row

def has_model_inputs(features):
    _, metadata = load_model()
    return any(features.get(feature) not in (None, '') for feature in metadata['features'])

def model_input_status(features):
    """Describe supplied UCI inputs without manufacturing missing values.

    The persisted pipeline imputes omitted values as part of its trained
    preprocessing.  Returning this status keeps that distinction visible to
    the API/UI instead of treating absent student records as observed data.
    """
    _, metadata = load_model()
    provided = [feature for feature in metadata['features'] if features.get(feature) not in (None, '')]
    missing = [feature for feature in metadata['features'] if feature not in provided]
    return {
        'provided_model_inputs': provided,
        'missing_model_inputs': missing,
        'model_input_count': len(provided),
        'model_feature_count': len(metadata['features']),
    }

def risk_for(score):
    # Transparent hackathon thresholds on the UCI 0-20 grade scale; not universal validation.
    return 'HIGH' if score < 8 else 'MEDIUM' if score < 12 else 'LOW'

def explain(features):
    model, metadata = load_model()
    _, row = predict(features)
    transformed = model.named_steps['preprocessor'].transform(pd.DataFrame([row], columns=metadata['features']))
    forest = model.named_steps['model']
    values = shap.TreeExplainer(forest).shap_values(transformed)[0]
    names = model.named_steps['preprocessor'].get_feature_names_out()
    pairs = sorted(zip(names, values), key=lambda item: abs(item[1]), reverse=True)[:8]
    return [{'feature': str(name).split('__')[-1], 'impact': float(impact), 'direction': 'negative' if impact < 0 else 'positive', 'input_value': row.get(str(name).split('__')[-1])} for name, impact in pairs]

def feature_json(value):
    raw = json.loads(value or '{}')
    # Only features in the currently trained model are active or exposed.
    # Legacy JSON keys may remain in historic records, but never enter a new
    # prediction, explanation, recommendation, or API response.
    try:
        _, metadata = load_model()
    except RuntimeError:
        return raw
    return {feature: raw[feature] for feature in metadata['features'] if feature in raw}
