# Smart Budget Buddy – Technical Audit & Delivery Notes

## Scope
This audit describes the uploaded Phase 1 project and the improvements made in the separate delivery copy. The original uploaded ZIP was not modified.

## Preserved application
- Monthly allowance and balance dashboard
- Monthly spending forecast and daily safe-spend estimate
- Spend Before You Buy calculator
- Expense and income create/edit/delete flows
- Transaction history and date/date-range filters
- Savings goal planner
- Local rule-based Smart Spending Coach
- Dark NeoFin styling with lime accent and responsive CSS
- Flask API and SQLite persistence
- Browser localStorage fallback/backup
- SmartSpend AI suggestions for all seven categories

## Changes
- Added explicit edit controls for expense and income transactions.
- Added stricter API validation, duplicate ID checks, and rejection of incomplete full-state requests.
- Removed the local database path from the health endpoint response.
- Added hybrid keyword-rule + TF-IDF word/character n-gram + Logistic Regression inference.
- Added low-confidence and low-margin review flags. Rule matches intentionally do not return a probability.
- Added canonical category aliases for training only; SQLite records are not rewritten.
- Added a reproducible data-preparation process that leaves the original CSV files and SQLite DB untouched.
- Added stratified hold-out evaluation and 3-fold stratified cross-validation.
- Added environment metadata and a scikit-learn version check at model load.
- Rewrote setup, training, testing and privacy documentation.

## Training data
- Prepared examples: 205 unique descriptions.
- Synthetic: 203; real SQLite-derived: 2.
- Category counts: Bills 29, Education 31, Entertainment 29, Food 30, Other 26, Shopping 30, Travel 30.
- The prepared CSV is excluded from the delivery ZIP because it contains user-derived descriptions; it is regenerated locally by `python -m ml.prepare_dataset`.
- Original `expenses_synthetic.csv` and `combined_expenses.csv` are retained unchanged.

## Model evaluation
- Model: word + character TF-IDF features with Logistic Regression.
- Stratified hold-out: 52 examples.
- Hold-out accuracy: 88.46%.
- Hold-out macro F1: 0.884.
- 3-fold cross-validation macro F1: 0.829 ± 0.053.
- These hold-out and cross-validation metrics evaluate the TF-IDF + Logistic Regression model only; the keyword rules are not included in those scores.
- Per-category hold-out recall:
  - Bills: 0.857
  - Education: 0.875
  - Entertainment: 1.000
  - Food: 0.750
  - Other: 0.833
  - Shopping: 0.875
  - Travel: 1.000
- The separate 35-case hand-authored development smoke set passes 35/35 after rule refinement. It was used while refining keyword rules and is not an independent or representative benchmark.
- Probabilities are not calibrated correctness guarantees.

## Verification performed
- Python source compilation: passed.
- JavaScript syntax check (`node --check`): passed.
- JavaScript DOM ID references: no missing IDs.
- Flask API/unit tests: 14 passed.
- SmartSpend AI API checks: all seven short-category examples passed; low-confidence metadata and model-version mismatch paths tested.
- Model training: passed.
- Development smoke set: passed.
- SQLite integrity check: `ok`.
- Original uploaded SQLite database SHA-256 matches the extracted delivery copy; record counts remain unchanged (2 expenses, 1 income, 1 savings goal).
- Flask health endpoint and API were exercised using the Flask test client and an isolated test database.

## Limitations not verified
- The runtime available for this build used Python 3.13.5, not Python 3.14. Scikit-learn 1.8 documents support for Python 3.11–3.14 and Flask supports Python 3.11+, but a full install/run on Python 3.14 was not executed here.
- Headless Chromium returned `ERR_BLOCKED_BY_ADMINISTRATOR` when navigating to the local Flask server. Frontend JavaScript syntax and DOM references were checked, but real browser interaction, visual rendering, and mobile layout were not fully verified.
- The training set is small and synthetic-heavy. Real-world category accuracy may differ substantially.
- The Flask development server is for local use, not public production deployment.


## Independent review update (2026-11-12)
- Reviewed the supplied delivery ZIP and its project files.
- Reproduced dataset preparation: 205 unique labelled examples (203 synthetic, 2 SQLite-derived), with all seven categories represented and no invalid labels or conflicting descriptions.
- Investigated the reported `miscellaneous expense` result. The original hybrid classifier had no generic miscellaneous/other rule, so this description fell through to the ML model.
- Added transparent Other-category rules for `miscellaneous expense`, `misc expense`, `other expense`, `unexpected expense`, and `unclassified expense`; added a regression API test for the generic miscellaneous/other descriptions. Existing user confirmation before saving an AI suggestion remains unchanged.
- Verified direct rule outputs for miscellaneous expense, misc expense, other expense, lunch, bus, recharge, books, movie ticket and shirt.
- Python source compilation passed; `node --check script.js` passed; SQLite `PRAGMA integrity_check` returned `ok`.
- Confirmed the supplied SQLite database still contains 2 expenses, 1 income and 1 savings goal. Dataset preparation did not modify it.
- **Full API/unit tests and model retraining could not be rerun in this review runtime** because Flask and the pinned ML dependencies are not installed and package-index network access is unavailable. The uploaded audit records a previous 14-test pass, but that is not a fresh test run of this revision.
- The model's reported metrics remain indicative only; this review does not claim 100% classification accuracy or full browser end-to-end verification.
