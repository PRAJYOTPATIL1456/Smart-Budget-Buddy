"""Build a reproducible ML dataset without modifying source datasets or SQLite."""
import csv
import os
import re
import sqlite3
import unicodedata
from collections import Counter, defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DB_PATH = Path(os.getenv("BUDGET_DB_PATH", ROOT / "data" / "budget_buddy.db"))
SOURCE_PATHS = [
    ROOT / "dataset" / "expenses_synthetic.csv",
    ROOT / "dataset" / "student_expenses_augmented.csv",
]
OUTPUT_PATH = ROOT / "dataset" / "prepared_expenses.csv"
FIELDS = ["description", "amount", "category", "date", "source"]
CATEGORIES = {"Food", "Travel", "Education", "Shopping", "Entertainment", "Bills", "Other"}
ALIASES = {
    "study": "Education", "studies": "Education", "stationary": "Education",
    "transport": "Travel", "commute": "Travel", "groceries": "Food",
    "food and drink": "Food", "utilities": "Bills", "subscription": "Bills",
    "misc": "Other", "miscellaneous": "Other",
}


def normalise_description(value):
    value = unicodedata.normalize("NFKC", str(value or "")).casefold()
    return " ".join(re.findall(r"[a-z0-9]+", value))


def canonical_category(value):
    label = " ".join(str(value or "").strip().split())
    if label in CATEGORIES:
        return label
    return ALIASES.get(label.casefold())


def main():
    rows = []
    invalid = 0
    for source_path in SOURCE_PATHS:
        if not source_path.exists():
            continue
        with source_path.open("r", newline="", encoding="utf-8-sig") as file:
            for row in csv.DictReader(file):
                description = str(row.get("description", "")).strip()
                category = canonical_category(row.get("category"))
                if not description or not category:
                    invalid += 1
                    continue
                rows.append({
                    "description": description[:120],
                    "amount": row.get("amount", ""),
                    "category": category,
                    "date": row.get("date", ""),
                    "source": "synthetic",
                })

    real_count = 0
    if DB_PATH.exists():
        with sqlite3.connect(f"file:{DB_PATH}?mode=ro", uri=True) as db:
            tables = {r[0] for r in db.execute(
                "SELECT name FROM sqlite_master WHERE type='table'"
            )}
            if "expenses" in tables:
                for title, amount, category, date in db.execute(
                    "SELECT title, amount, category, date FROM expenses"
                ):
                    label = canonical_category(category)
                    if not str(title or "").strip() or not label:
                        invalid += 1
                        continue
                    rows.append({
                        "description": str(title).strip()[:120],
                        "amount": amount,
                        "category": label,
                        "date": date,
                        "source": "real",
                    })
                    real_count += 1

    # Drop conflicting labels for the same normalised description.
    labels_by_text = defaultdict(set)
    for row in rows:
        labels_by_text[normalise_description(row["description"])].add(row["category"])
    conflicts = {key for key, labels in labels_by_text.items() if len(labels) > 1}
    kept = [r for r in rows if normalise_description(r["description"]) not in conflicts]

    # Deduplicate exact descriptions, preferring real, user-labelled records.
    unique = {}
    for row in kept:
        key = normalise_description(row["description"])
        previous = unique.get(key)
        if previous is None or (row["source"] == "real" and previous["source"] != "real"):
            unique[key] = row
    output_rows = sorted(unique.values(), key=lambda r: (r["category"], r["description"].casefold()))

    OUTPUT_PATH.parent.mkdir(parents=True, exist_ok=True)
    with OUTPUT_PATH.open("w", newline="", encoding="utf-8") as file:
        writer = csv.DictWriter(file, fieldnames=FIELDS)
        writer.writeheader()
        writer.writerows(output_rows)

    counts = Counter(r["category"] for r in output_rows)
    sources = Counter(r["source"] for r in output_rows)
    print(f"Prepared {len(output_rows)} unique examples.")
    print(f"Sources: {dict(sources)}")
    print(f"Categories: {dict(sorted(counts.items()))}")
    print(f"Skipped invalid/unknown labels: {invalid}; conflicting descriptions: {len(conflicts)}.")
    print(f"Output: {OUTPUT_PATH}")
    print("Original source CSV files and SQLite records were not modified.")


if __name__ == "__main__":
    main()
