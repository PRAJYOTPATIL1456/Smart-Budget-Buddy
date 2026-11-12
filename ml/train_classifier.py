"""Train and honestly evaluate SmartSpend AI using a reproducible split."""
import json
import platform
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path

import joblib
import numpy as np
import pandas as pd
import sklearn
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import accuracy_score, classification_report, f1_score
from sklearn.model_selection import StratifiedKFold, cross_val_score, train_test_split
from sklearn.pipeline import FeatureUnion, Pipeline

ROOT = Path(__file__).resolve().parents[1]
DATASET = ROOT / "dataset" / "prepared_expenses.csv"
MODEL_DIR = ROOT / "models"
MODEL_PATH = MODEL_DIR / "category_classifier.joblib"
METADATA_PATH = MODEL_DIR / "category_classifier_metadata.json"
REQUIRED_COLUMNS = {"description", "category"}
ALLOWED_CATEGORIES = {"Food", "Travel", "Education", "Shopping", "Entertainment", "Bills", "Other"}


def build_pipeline():
    features = FeatureUnion([
        ("word", TfidfVectorizer(
            analyzer="word", ngram_range=(1, 2), strip_accents="unicode",
            sublinear_tf=True, min_df=1, max_features=12000
        )),
        ("char", TfidfVectorizer(
            analyzer="char_wb", ngram_range=(3, 5), strip_accents="unicode",
            sublinear_tf=True, min_df=1, max_features=18000
        )),
    ])
    return Pipeline([
        ("features", features),
        ("classifier", LogisticRegression(
            max_iter=2000, class_weight="balanced", C=1.0, random_state=42
        )),
    ])


def main():
    if not DATASET.exists():
        raise SystemExit("Prepared dataset not found. Run: python -m ml.prepare_dataset")
    data = pd.read_csv(DATASET)
    if not REQUIRED_COLUMNS.issubset(data.columns):
        raise SystemExit("Dataset must contain description and category columns.")

    data = data.dropna(subset=["description", "category"]).copy()
    data["description"] = data["description"].astype(str).str.strip()
    data["category"] = data["category"].astype(str).str.strip()
    data = data[(data["description"] != "") & (data["category"].isin(ALLOWED_CATEGORIES))]
    data = data.drop_duplicates(subset=["description"])
    counts = data["category"].value_counts()
    if len(data) < 21 or len(counts) != 7 or counts.min() < 3:
        raise SystemExit(
            "Need at least 3 unique labelled examples in each of the 7 categories."
        )

    X, y = data["description"], data["category"]
    X_train, X_test, y_train, y_test = train_test_split(
        X, y, test_size=0.25, random_state=42, stratify=y
    )

    evaluation_model = build_pipeline().fit(X_train, y_train)
    predictions = evaluation_model.predict(X_test)
    accuracy = accuracy_score(y_test, predictions)
    macro_f1 = f1_score(y_test, predictions, average="macro", zero_division=0)
    report = classification_report(
        y_test, predictions, labels=sorted(ALLOWED_CATEGORIES),
        output_dict=True, zero_division=0
    )

    cv = StratifiedKFold(n_splits=3, shuffle=True, random_state=42)
    cv_scores = cross_val_score(
        build_pipeline(), X, y, cv=cv, scoring="f1_macro", n_jobs=1
    )

    print(f"Unique labelled examples: {len(data)}")
    print(f"Category counts: {dict(sorted(counts.items()))}")
    print(f"Hold-out accuracy: {accuracy:.1%} ({len(y_test)} test examples)")
    print(f"Hold-out macro F1: {macro_f1:.3f}")
    print(f"3-fold CV macro F1: {cv_scores.mean():.3f} ± {cv_scores.std():.3f}")
    print(classification_report(y_test, predictions, zero_division=0))

    # Refit only after evaluation; the held-out metrics above remain untouched.
    final_model = build_pipeline().fit(X, y)
    MODEL_DIR.mkdir(parents=True, exist_ok=True)
    joblib.dump(final_model, MODEL_PATH, compress=3)

    source_counts = data["source"].value_counts().to_dict() if "source" in data else {}
    metadata = {
        "model": "Hybrid inference: TF-IDF word + character n-grams and Logistic Regression, with transparent keyword rules",
        "training_examples": int(len(data)),
        "category_counts": {str(k): int(v) for k, v in counts.items()},
        "categories": sorted(data["category"].unique().tolist()),
        "source_counts": {str(k): int(v) for k, v in source_counts.items()},
        "holdout_accuracy": round(float(accuracy), 4),
        "holdout_macro_f1": round(float(macro_f1), 4),
        "test_examples": int(len(y_test)),
        "cross_validation_macro_f1_mean": round(float(cv_scores.mean()), 4),
        "cross_validation_macro_f1_std": round(float(cv_scores.std()), 4),
        "per_category_metrics": {
            label: {metric: round(float(report[label][metric]), 4)
                    for metric in ("precision", "recall", "f1-score", "support")}
            for label in sorted(ALLOWED_CATEGORIES)
        },
        "random_state": 42,
        "evaluation": "Stratified 25% hold-out plus 3-fold stratified cross-validation on the TF-IDF + Logistic Regression model only; keyword rules are not included. Small, partly synthetic dataset; metrics are indicative, not a guarantee.",
        "python_version": platform.python_version(),
        "scikit_learn_version": sklearn.__version__,
        "numpy_version": np.__version__,
        "pandas_version": pd.__version__,
        "joblib_version": joblib.__version__,
        "trained_at_utc": datetime.now(timezone.utc).isoformat(),
        "probability_note": "ML probabilities are model confidence estimates, not calibrated guarantees of correctness. Low confidence or a small top-two margin requires review. Rule matches do not report probabilities.",
    }
    METADATA_PATH.write_text(json.dumps(metadata, indent=2), encoding="utf-8")
    print(f"Saved model: {MODEL_PATH}")
    print(f"Saved metadata: {METADATA_PATH}")


if __name__ == "__main__":
    main()
