# Smart Budget Buddy – Student Edition

**AI feature:** SmartSpend AI  
A local-first student budgeting application built with HTML, CSS, JavaScript, Flask, SQLite and scikit-learn.

## Features

- Monthly allowance and balance dashboard
- Monthly spending forecast and daily safe-spend estimate
- Spend Before You Buy calculator
- Add, edit and delete expenses and income
- Transaction history and date/date-range filters
- Savings goal tracking
- Rule-based Smart Spending Coach
- Dark NeoFin interface with lime accent and responsive layout
- SQLite persistence with browser `localStorage` fallback/backup
- SmartSpend AI category suggestions for Food, Travel, Education, Shopping, Entertainment, Bills and Other

## Requirements

- Python 3.11 or newer (Python 3.14 is supported by current Flask and scikit-learn releases)
- Windows PowerShell, macOS Terminal or Linux shell
- Internet access for the initial `pip install` only

Scikit-learn 1.8 supports Python 3.11–3.14. The bundled model was trained and tested in this delivery environment with Python 3.13.5 and scikit-learn 1.8.0; Python 3.14 installation is supported by the dependency versions but was not executed in this environment.

## Windows PowerShell setup

Open PowerShell in the extracted `Smart_Budget_Buddy_Phase1` folder.

```powershell
py -3.14 --version
py -3.14 -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
python -m pip install -r requirements.txt
```

If Python 3.14 is not installed, use `py -3.13` instead of `py -3.14` in the first two commands.

If PowerShell blocks virtual-environment activation, run this for the current terminal only:

```powershell
Set-ExecutionPolicy -Scope Process -ExecutionPolicy Bypass
.\.venv\Scripts\Activate.ps1
```

Start the application:

```powershell
python server.py
```

Open this address in your browser:

`http://127.0.0.1:5000`

Keep the terminal open while using the app. Press `Ctrl+C` in that terminal to stop the local server.

## SmartSpend AI

The classifier uses a hybrid design:

1. Transparent high-signal keyword rules handle short descriptions such as `books`, `lunch`, `bus` and `recharge`.
2. Other descriptions are processed by word-level and character-level TF-IDF features and Logistic Regression.

The API is `POST /api/ml/classify`. It returns a category suggestion and whether the user should review it. For rule matches, the response does not invent a probability. For ML predictions, the probability is an estimate, not a guarantee. Low probability or a small margin between the top two classes triggers manual review. The frontend never saves an expense from the AI response; the user must submit the expense form.

### Retrain the model

From the project folder with `.venv` activated:

```powershell
python -m ml.prepare_dataset
python -m ml.train_classifier
```

Dataset preparation reads:

- `dataset/expenses_synthetic.csv` (original starter data)
- `dataset/student_expenses_augmented.csv` (additional curated synthetic examples)
- correctly categorised expenses from the local SQLite database

It writes `dataset/prepared_expenses.csv`. It does **not** overwrite the original CSVs, `combined_expenses.csv`, or the SQLite database. The source of each row is recorded as `synthetic` or `real`. Category aliases such as `Study` are mapped to a canonical ML category for training only; the saved transaction in SQLite is not changed.

Training performs a stratified 25% hold-out evaluation and 3-fold stratified cross-validation, then fits the deployable model on all prepared rows. Metrics and environment versions are written to `models/category_classifier_metadata.json`. The model is written to `models/category_classifier.joblib`. The requirements pin scikit-learn 1.8.0 to match the bundled model's training version.

To run the hand-authored development smoke set (excluded from training, but used while refining keyword rules; not an independent benchmark):

```powershell
python -m ml.evaluate_classifier
```

The included dataset is small and mostly synthetic. The hold-out and cross-validation scores evaluate the ML model only, not the complete hybrid rule-plus-ML system. Evaluation scores can change as data changes and are not a promise of real-world performance. Do not treat synthetic examples as real student transactions. Keep `prepared_expenses.csv` private because it can contain descriptions from your local database.

## Data safety and storage

- SQLite is the primary store after the first successful browser-to-database migration.
- Browser `localStorage` is retained as a local backup/fallback.
- The application binds to `127.0.0.1` and is intended for local development/demo use.
- Do not expose this development server directly to the public internet.
- Before manually editing or moving `data/budget_buddy.db`, stop the server and make a copy of the database file.
- `/api/state` requires a complete state payload before replacing records. An incomplete request is rejected to prevent accidental clearing.
- The application does not reset the database during normal startup.
- Keep API keys in environment variables; never put them in browser JavaScript or commit them to source control.

Optional legacy `/api/insights` Gemini integration is separate from SmartSpend AI and requires `GEMINI_API_KEY`. The current Smart Spending Coach in the frontend uses local, rule-based analysis and does not require an external AI service.

## Tests

Run the backend/API tests:

```powershell
python -m unittest discover -s tests -v
```

The tests use temporary SQLite databases and do not intentionally alter the user's database. They cover health checks, persistence, validation, protection against incomplete state replacement, and SmartSpend AI category suggestions.

## Known limitations

- ML quality is limited by the size and synthetic-heavy nature of the training set.
- A category suggestion can be wrong; users should review it before saving.
- Probabilities are not calibrated correctness guarantees.
- The spending forecast is an estimate based on current-month records.
- The development server is local-only and is not hardened for production deployment.
