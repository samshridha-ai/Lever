"""Download the UCI student-mat data, train LEVER's pipeline, and save real metrics."""
from pathlib import Path
import sys
import zipfile
from urllib.request import urlretrieve

import joblib
import pandas as pd
from sklearn.compose import ColumnTransformer
from sklearn.ensemble import RandomForestRegressor
from sklearn.impute import SimpleImputer
from sklearn.metrics import mean_absolute_error, mean_squared_error, r2_score
from sklearn.model_selection import train_test_split
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import OneHotEncoder

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from config import MODEL_PATH, METADATA_PATH

DATA_DIR = ROOT / 'data'
CSV = DATA_DIR / 'student-mat.csv'
ZIP_URL = 'https://archive.ics.uci.edu/ml/machine-learning-databases/00320/student.zip'
ZIP = DATA_DIR / 'student.zip'

def dataset():
    DATA_DIR.mkdir(exist_ok=True)
    if not CSV.exists():
        print(f'Downloading UCI dataset from {ZIP_URL}')
        urlretrieve(ZIP_URL, ZIP)
        with zipfile.ZipFile(ZIP) as archive:
            archive.extract('student-mat.csv', DATA_DIR)
    return pd.read_csv(CSV, sep=';')

def main():
    data = dataset()
    # LEVER's active model deliberately uses only verified academic inputs.
    # G3 is the final-grade target; G1/G2 are prior-period grades.
    features = ['absences', 'studytime', 'failures', 'G1', 'G2']
    X = data[features].copy()
    y = data['G3']
    numeric = X.select_dtypes(include=['number']).columns.tolist()
    categorical = [column for column in X.columns if column not in numeric]
    preprocess = ColumnTransformer([
        ('num', Pipeline([('impute', SimpleImputer(strategy='median'))]), numeric),
        ('cat', Pipeline([('impute', SimpleImputer(strategy='most_frequent')), ('onehot', OneHotEncoder(handle_unknown='ignore'))]), categorical),
    ])
    pipeline = Pipeline([('preprocessor', preprocess), ('model', RandomForestRegressor(n_estimators=300, random_state=42, min_samples_leaf=2, n_jobs=-1))])
    X_train, X_test, y_train, y_test = train_test_split(X, y, test_size=.2, random_state=42)
    pipeline.fit(X_train, y_train)
    predicted = pipeline.predict(X_test)
    metrics = {'mae': float(mean_absolute_error(y_test, predicted)), 'rmse': float(mean_squared_error(y_test, predicted) ** .5), 'r2': float(r2_score(y_test, predicted)), 'rows': int(len(data)), 'features': int(X.shape[1]), 'target': 'G3'}
    MODEL_PATH.parent.mkdir(exist_ok=True)
    joblib.dump(pipeline, MODEL_PATH)
    joblib.dump({'features': X.columns.tolist(), 'metrics': metrics, 'numeric_features': numeric, 'categorical_features': categorical}, METADATA_PATH)
    print('Dataset:', CSV)
    print('Rows:', metrics['rows'], 'Features:', metrics['features'])
    print('MAE:', metrics['mae'])
    print('RMSE:', metrics['rmse'])
    print('R2:', metrics['r2'])
    print('Model:', MODEL_PATH)

if __name__ == '__main__': main()
