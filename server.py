"""Smart Budget Buddy backend with local SQLite persistence and SmartSpend AI."""

import json
import math
import os
import sqlite3
from contextlib import contextmanager
from pathlib import Path

import joblib
import sklearn

import requests
from flask import Flask, jsonify, request, send_from_directory

from ml.classifier import classify_text

BASE_DIR = Path(__file__).resolve().parent
DATA_DIR = BASE_DIR / "data"
DEFAULT_DB_PATH = DATA_DIR / "budget_buddy.db"
DB_PATH = Path(os.getenv("BUDGET_DB_PATH", str(DEFAULT_DB_PATH))).resolve()
CLASSIFIER_PATH = BASE_DIR / "models" / "category_classifier.joblib"
CLASSIFIER_METADATA_PATH = BASE_DIR / "models" / "category_classifier_metadata.json"
_classifier_cache = None
DEFAULT_STATE = {"allowance": 8000, "expenses": [], "incomes": [], "goal": None}
app = Flask(__name__, static_folder=None)


def get_connection():
    DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    connection = sqlite3.connect(DB_PATH, timeout=10)
    connection.row_factory = sqlite3.Row
    connection.execute("PRAGMA foreign_keys = ON")
    return connection


@contextmanager
def database_connection():
    connection = get_connection()
    try:
        yield connection
        connection.commit()
    except Exception:
        connection.rollback()
        raise
    finally:
        connection.close()


def init_db():
    with database_connection() as db:
        db.executescript(
            """
            CREATE TABLE IF NOT EXISTS settings (
                setting_key TEXT PRIMARY KEY,
                setting_value TEXT NOT NULL
            );
            CREATE TABLE IF NOT EXISTS expenses (
                id TEXT PRIMARY KEY,
                title TEXT NOT NULL,
                amount REAL NOT NULL CHECK(amount > 0),
                category TEXT NOT NULL,
                date TEXT NOT NULL
            );
            CREATE TABLE IF NOT EXISTS incomes (
                id TEXT PRIMARY KEY,
                source TEXT NOT NULL,
                amount REAL NOT NULL CHECK(amount > 0),
                date TEXT NOT NULL
            );
            CREATE TABLE IF NOT EXISTS saving_goals (
                id INTEGER PRIMARY KEY CHECK(id = 1),
                name TEXT NOT NULL,
                amount REAL NOT NULL CHECK(amount > 0),
                saved REAL NOT NULL DEFAULT 0 CHECK(saved >= 0)
            );
            """
        )


def valid_date(value):
    if not isinstance(value, str) or len(value) != 10:
        return False
    try:
        from datetime import date
        date.fromisoformat(value)
        return True
    except ValueError:
        return False


def clean_records(records, kind):
    if not isinstance(records, list) or len(records) > 5000:
        raise ValueError(f"Invalid {kind} list (maximum 5000 records).")
    cleaned = []
    seen_ids = set()
    for record in records:
        if not isinstance(record, dict):
            raise ValueError(f"Invalid {kind} record.")
        try:
            amount = float(record.get("amount"))
        except (TypeError, ValueError):
            raise ValueError(f"Invalid {kind} amount.")
        if not math.isfinite(amount) or amount <= 0:
            raise ValueError(f"{kind.capitalize()} amount must be positive.")
        date_value = record.get("date")
        if not valid_date(date_value):
            raise ValueError(f"Invalid {kind} date; use YYYY-MM-DD.")
        record_id = str(record.get("id", "")).strip()[:80]
        if not record_id:
            raise ValueError(f"Missing {kind} ID.")
        if record_id in seen_ids:
            raise ValueError(f"Duplicate {kind} ID.")
        seen_ids.add(record_id)
        if kind == "expense":
            title = str(record.get("title", "")).strip()[:120]
            category = str(record.get("category", "Other")).strip()[:40] or "Other"
            if not title:
                raise ValueError("Expense title is required.")
            cleaned.append({"id": record_id, "title": title, "amount": amount,
                            "category": category, "date": date_value})
        else:
            source = str(record.get("source", "")).strip()[:120]
            if not source:
                raise ValueError("Income source is required.")
            cleaned.append({"id": record_id, "source": source,
                            "amount": amount, "date": date_value})
    return cleaned


def read_state():
    with database_connection() as db:
        allowance_row = db.execute(
            "SELECT setting_value FROM settings WHERE setting_key = 'allowance'"
        ).fetchone()
        if allowance_row is None:
            return {"initialized": False, "state": DEFAULT_STATE.copy()}
        expenses = [dict(row) for row in db.execute(
            "SELECT id, title, amount, category, date FROM expenses ORDER BY date, rowid"
        )]
        incomes = [dict(row) for row in db.execute(
            "SELECT id, source, amount, date FROM incomes ORDER BY date, rowid"
        )]
        goal_row = db.execute(
            "SELECT name, amount, saved FROM saving_goals WHERE id = 1"
        ).fetchone()
        goal = dict(goal_row) if goal_row else None
        return {"initialized": True, "state": {
            "allowance": float(allowance_row[0]),
            "expenses": expenses,
            "incomes": incomes,
            "goal": goal
        }}


def write_state(data):
    if not isinstance(data, dict):
        raise ValueError("Request body must be a JSON object.")
    required = {"allowance", "expenses", "incomes", "goal"}
    missing = required.difference(data)
    if missing:
        raise ValueError(
            "Incomplete state; refusing to replace saved data. Missing: " +
            ", ".join(sorted(missing))
        )
    try:
        allowance = float(data.get("allowance"))
    except (TypeError, ValueError):
        raise ValueError("Invalid allowance.")
    if not math.isfinite(allowance) or allowance <= 0:
        raise ValueError("Allowance must be a positive number.")

    expenses = clean_records(data.get("expenses", []), "expense")
    incomes = clean_records(data.get("incomes", []), "income")
    goal = data.get("goal")
    if goal is not None:
        if not isinstance(goal, dict):
            raise ValueError("Invalid saving goal.")
        name = str(goal.get("name", "")).strip()[:120]
        try:
            goal_amount = float(goal.get("amount"))
            saved = float(goal.get("saved", 0))
        except (TypeError, ValueError):
            raise ValueError("Invalid saving goal amounts.")
        if not name or not math.isfinite(goal_amount) or goal_amount <= 0:
            raise ValueError("Saving goal needs a name and positive target.")
        if not math.isfinite(saved) or saved < 0:
            raise ValueError("Saved amount cannot be negative.")
        goal = {"name": name, "amount": goal_amount, "saved": saved}

    with database_connection() as db:
        db.execute("BEGIN")
        db.execute(
            "INSERT INTO settings(setting_key, setting_value) VALUES('allowance', ?) "
            "ON CONFLICT(setting_key) DO UPDATE SET setting_value=excluded.setting_value",
            (str(allowance),)
        )
        db.execute("DELETE FROM expenses")
        db.execute("DELETE FROM incomes")
        db.execute("DELETE FROM saving_goals")
        db.executemany(
            "INSERT INTO expenses(id,title,amount,category,date) VALUES(?,?,?,?,?)",
            [(x["id"], x["title"], x["amount"], x["category"], x["date"]) for x in expenses]
        )
        db.executemany(
            "INSERT INTO incomes(id,source,amount,date) VALUES(?,?,?,?)",
            [(x["id"], x["source"], x["amount"], x["date"]) for x in incomes]
        )
        if goal:
            db.execute(
                "INSERT INTO saving_goals(id,name,amount,saved) VALUES(1,?,?,?)",
                (goal["name"], goal["amount"], goal["saved"])
            )


@app.get("/")
def home():
    return send_from_directory(BASE_DIR, "index.html")


@app.get("/style.css")
def stylesheet():
    return send_from_directory(BASE_DIR, "style.css")


@app.get("/script.js")
def javascript():
    return send_from_directory(BASE_DIR, "script.js")


@app.get("/api/health")
def health():
    try:
        with database_connection() as db:
            db.execute("SELECT 1")
        return jsonify({"status": "ok", "database": "sqlite"})
    except sqlite3.Error:
        app.logger.exception("SQLite health check failed")
        return jsonify({"status": "error", "database": "unavailable"}), 500


@app.get("/api/state")
def get_app_state():
    try:
        return jsonify(read_state())
    except sqlite3.Error:
        app.logger.exception("Could not read SQLite state")
        return jsonify({"error": "Could not read local database."}), 500


@app.put("/api/state")
def put_app_state():
    data = request.get_json(silent=True)
    try:
        write_state(data)
        return jsonify({"saved": True})
    except ValueError as error:
        return jsonify({"error": str(error)}), 400
    except sqlite3.Error:
        app.logger.exception("Could not save SQLite state")
        return jsonify({"error": "Could not save to local database."}), 500


@app.post("/api/ml/classify")
def classify_expense():
    """Suggest a category using high-signal rules and the local ML model."""
    global _classifier_cache
    data = request.get_json(silent=True)
    if not isinstance(data, dict):
        return jsonify({"error": "Send a JSON object with an expense title."}), 400
    title = data.get("title")
    if not isinstance(title, str):
        return jsonify({"error": "Expense title must be text."}), 400
    title = title.strip()
    if not title or len(title) > 120:
        return jsonify({"error": "Enter an expense name (1–120 characters)."}), 400
    if not CLASSIFIER_PATH.exists():
        return jsonify({
            "error": "SmartSpend AI model is not trained yet. Run python -m ml.prepare_dataset and python -m ml.train_classifier."
        }), 503
    try:
        if _classifier_cache is None:
            if CLASSIFIER_METADATA_PATH.exists():
                metadata = json.loads(CLASSIFIER_METADATA_PATH.read_text(encoding="utf-8"))
                trained_version = metadata.get("scikit_learn_version")
                if trained_version and trained_version != sklearn.__version__:
                    return jsonify({
                        "error": (
                            f"Model was trained with scikit-learn {trained_version}, "
                            f"but {sklearn.__version__} is installed. Install the pinned "
                            "requirements or retrain the model."
                        )
                    }), 503
            _classifier_cache = joblib.load(CLASSIFIER_PATH)
        result = classify_text(title, _classifier_cache)
        result.update({
            "model": "SmartSpend AI · keyword rules + TF-IDF + Logistic Regression",
            "message": (
                "Matched a high-signal expense keyword. Please verify the category."
                if result["match_type"] == "keyword_rule"
                else "ML probability is an estimate, not a guarantee. Please review the category."
            )
        })
        return jsonify(result)
    except Exception:
        app.logger.exception("SmartSpend AI classifier could not predict")
        _classifier_cache = None
        return jsonify({
            "error": "The category model could not be loaded. Retrain it using the README instructions."
        }), 500


# Optional legacy Gemini endpoint. This remains separate from the local SmartSpend AI classifier.
@app.post("/api/insights")
def insights():
    key = os.getenv("GEMINI_API_KEY", "").strip()
    if not key:
        return jsonify({"error": "Gemini API is not configured on the server."}), 503
    data = request.get_json(silent=True)
    if not isinstance(data, dict):
        return jsonify({"error": "Invalid request data."}), 400
    try:
        allowance = float(data.get("allowance"))
    except (TypeError, ValueError):
        return jsonify({"error": "Invalid allowance."}), 400
    if not math.isfinite(allowance) or allowance <= 0:
        return jsonify({"error": "Invalid allowance."}), 400
    expenses = data.get("expenses", [])
    if not isinstance(expenses, list) or len(expenses) > 500:
        return jsonify({"error": "Invalid expense list."}), 400
    safe_expenses = []
    for expense in expenses:
        if not isinstance(expense, dict):
            return jsonify({"error": "Invalid expense record."}), 400
        try:
            amount = float(expense.get("amount"))
        except (TypeError, ValueError):
            return jsonify({"error": "Invalid expense amount."}), 400
        if not math.isfinite(amount) or amount <= 0:
            return jsonify({"error": "Invalid expense amount."}), 400
        safe_expenses.append({"title": str(expense.get("title", ""))[:60],
                              "amount": round(amount, 2),
                              "category": str(expense.get("category", ""))[:30],
                              "date": str(expense.get("date", ""))[:20]})
    prompt = (
        "Act as a careful, supportive budgeting coach for a college student in India. "
        "Analyse the supplied monthly allowance and expenses. Give 3-4 short, specific, "
        "non-judgmental tips. Do not invent facts, recommend loans or investments, or "
        "claim certainty. Return only JSON in this format: "
        '{"insights":["tip 1","tip 2","tip 3"]}. Data: ' +
        json.dumps({"allowance": allowance, "expenses": safe_expenses}, ensure_ascii=False)
    )
    model = os.getenv("GEMINI_MODEL", "gemini-3.8-flash").strip()
    if not model.replace("-", "").replace(".", "").isalnum():
        return jsonify({"error": "Invalid AI model configuration."}), 500
    url = f"https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent"
    try:
        response = requests.post(
            url,
            headers={"x-goog-api-key": key, "Content-Type": "application/json"},
            json={"contents": [{"parts": [{"text": prompt}]}],
                  "generationConfig": {"temperature": 0.3, "responseMimeType": "application/json"}},
            timeout=(5, 25)
        )
        response.raise_for_status()
        api_data = response.json()
        candidates = api_data.get("candidates", [])
        if not candidates:
            raise ValueError("No AI response received.")
        parts = candidates[0].get("content", {}).get("parts", [])
        if not parts or not isinstance(parts[0].get("text"), str):
            raise ValueError("Invalid AI response format.")
        tips = json.loads(parts[0]["text"]).get("insights", [])
        if not isinstance(tips, list):
            raise ValueError("Invalid insights format.")
        clean_tips = [str(t).strip()[:400] for t in tips[:4] if isinstance(t, str) and t.strip()]
        if not clean_tips:
            raise ValueError("No useful insights received.")
        return jsonify({"insights": clean_tips})
    except (requests.RequestException, ValueError, KeyError, IndexError, TypeError):
        app.logger.exception("Gemini request failed")
        return jsonify({"error": "AI service is temporarily unavailable."}), 502


init_db()

if __name__ == "__main__":
    app.run(host="127.0.0.1", port=5000, debug=False)
