"""Evaluate the hybrid classifier on a small hand-authored development smoke set."""
import csv
from pathlib import Path
import joblib
from sklearn.metrics import accuracy_score, classification_report
from ml.classifier import classify_text

ROOT = Path(__file__).resolve().parents[1]
MODEL = ROOT / "models" / "category_classifier.joblib"
DATA = ROOT / "dataset" / "evaluation_examples.csv"


def main():
    if not MODEL.exists():
        raise SystemExit("Model not found. Train it with python -m ml.train_classifier")
    model = joblib.load(MODEL)
    with DATA.open("r", newline="", encoding="utf-8") as file:
        rows = list(csv.DictReader(file))
    expected = [row["expected_category"] for row in rows]
    predicted = [classify_text(row["description"], model)["category"] for row in rows]
    print(f"Hand-authored development smoke examples (excluded from training): {len(rows)}")
    print(f"Accuracy: {accuracy_score(expected, predicted):.1%}")
    print(classification_report(expected, predicted, zero_division=0))
    print("Caution: this small smoke set was used during rule refinement; it is not an independent or representative benchmark.")


if __name__ == "__main__":
    main()
