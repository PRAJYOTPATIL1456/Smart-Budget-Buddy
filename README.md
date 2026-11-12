# Smart Budget Buddy – Student Edition

## About the Project

Smart Budget Buddy is a student-focused personal finance management web application designed to help students manage their money, track expenses, monitor income, and achieve savings goals.

It provides a simple dashboard and SmartSpend AI category suggestions to help students make better spending decisions.

## Problem Statement

Many students struggle to manage limited allowances, track daily expenses, and save money. Without proper budgeting, they may overspend and find it difficult to understand where their money goes.

## Our Solution

Smart Budget Buddy provides an easy-to-use platform where students can record their income and expenses, calculate safe spending limits, monitor their balance, and receive smart spending suggestions.

## Key Features

- **Dashboard:** Displays available balance and financial summaries.
- **Expense Tracking:** Add, view, filter, and delete expenses.
- **Income Management:** Record income and track balance changes.
- **Monthly Forecast:** Estimate monthly spending and daily safe spending limits based on recorded transactions.
- **Spend Before You Buy:** Calculate whether a planned purchase fits within the available budget.
- **Savings Goals:** Create and monitor savings goals.
- **SmartSpend AI:** Suggests expense categories using keyword rules and a Machine Learning model.
- **Smart Spending Coach:** Provides rule-based spending tips and personalised insights.
- **Data Persistence:** Stores financial records using SQLite and supports browser local storage backup.

## SmartSpend AI – Machine Learning

SmartSpend AI uses a hybrid approach combining keyword-based rules and Machine Learning.

**Machine Learning technologies:**
- TF-IDF Vectorization
- Word and character features
- Logistic Regression

**Supported categories:**
- Food
- Shopping
- Travel
- Education
- Bills
- Entertainment
- Other

The system suggests a category based on the transaction description. Users can review and confirm the suggested category before saving.

## Technology Stack

**Frontend:**
- HTML
- CSS
- JavaScript

**Backend:**
- Python
- Flask

**Database:**
- SQLite

**Machine Learning:**
- Scikit-learn
- TF-IDF
- Logistic Regression
- Joblib

## Project Structure

```text
Smart_Budget_Buddy_Final/
│
├── index.html
├── style.css
├── script.js
├── server.py
├── requirements.txt
├── README.md
│
├── data/
│   └── budget_buddy.db
│
├── models/
│   ├── category_classifier.joblib
│   └── category_classifier_metadata.json
│
├── ml/
│   ├── classifier.py
│   ├── train_classifier.py
│   ├── evaluate_classifier.py
│   └── prepare_dataset.py
│
├── tests/
│   └── test_api.py
│
└── datasets/
```

## Installation and Setup

### 1. Install Python

Download and install Python from:

https://www.python.org/downloads/

### 2. Download the Project

Clone the repository:

```bash
git clone YOUR_GITHUB_REPOSITORY_URL
```

Open the project folder:

```bash
cd Smart_Budget_Buddy_Final
```

### 3. Install Dependencies

```bash
python -m pip install -r requirements.txt
```

### 4. Run the Application

```bash
python server.py
```

Open the local application URL displayed in the terminal in your browser.

## Testing

The project includes automated backend tests.

Run the tests using:

```bash
python -m unittest discover -s tests -v
```

**Testing result:** 15 automated backend tests passed during project testing.

## Data and Privacy

The application uses a local SQLite database for storing financial records. It is designed as a local-first student budgeting application.

Users should avoid entering sensitive real banking credentials or confidential financial information.

## Future Scope

- Mobile application support
- Improved monthly spending forecasts
- Anomaly detection for unusual transactions
- More real-world training data for better category suggestions
- Advanced financial insights and recommendations

These are planned improvements and are not all implemented in the current version.

## Conclusion

Smart Budget Buddy helps students understand their spending habits, manage their budgets, and develop better saving practices.

**Spend Smarter. Save Better.**

---

**Project:** Smart Budget Buddy – Student Edition  
**Team:** Mind Spark  
**College:** Dr. D. Y. Patil Engineering College  
**Hackathon:** Arathon
