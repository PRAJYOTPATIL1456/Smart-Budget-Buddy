# 💰 Smart Budget Buddy – Student Edition

### Spend Smarter. Save Better. Live Stress-Free.

Smart Budget Buddy is a student-focused personal finance web application designed to help students manage their money, track daily expenses, monitor income, plan savings, and develop better financial habits.

It combines expense tracking, budgeting tools, personalised spending insights, and **SmartSpend AI**, a hybrid machine-learning-based expense category suggestion system.

---

## 🚀 Key Features

### 1. Smart Dashboard
- View your available balance.
- Monitor income and expenses.
- Track your overall financial activity.
- Get an overview of your spending habits.

### 2. Income and Expense Management
- Add and manage income records.
- Record daily expenses.
- View transaction history.
- Filter and delete transactions.
- Data is stored locally using SQLite.

### 3. SmartSpend AI
- Suggests suitable categories for expenses.
- Uses keyword-based rules and Machine Learning.
- Uses TF-IDF and Logistic Regression for text classification.
- Supports categories such as Food, Shopping, Travel, Education, Bills, Entertainment and Other.
- Allows users to verify suggestions before saving.

### 4. Smart Spending Coach
- Provides personalised, rule-based spending insights.
- Helps users understand their spending habits.
- Encourages responsible financial decisions.

### 5. Monthly Spending Forecast
- Estimates monthly spending based on recorded transactions.
- Helps students understand their current spending patterns.

### 6. Daily Safe Spending Calculator
- Helps users estimate how much money they can safely spend each day.

### 7. Spend Before You Buy
- Helps users evaluate a potential purchase before spending money.
- Encourages thoughtful purchasing decisions.

### 8. Savings Goals
- Create savings goals.
- Track progress towards financial targets.
- Monitor savings over time.

### 9. User-Friendly Interface
- Modern NeoFin-inspired design.
- Dark theme with lime-green accents.
- Responsive web interface.
- Local data persistence and backup support.

---

## 🧠 SmartSpend AI – Machine Learning

SmartSpend AI is the intelligent expense classification component of Smart Budget Buddy.

**Technologies used:**
- Python
- Scikit-learn
- TF-IDF Vectorization
- Logistic Regression
- Keyword-based classification rules

**How it works:**

1. The user enters an expense description.
2. SmartSpend AI analyses the description.
3. The classification system suggests an expense category.
4. The user reviews the suggested category.
5. After confirmation, the expense can be saved.

The system combines keyword-based rules with machine-learning predictions to improve category suggestions.

*Note: AI suggestions are recommendations and should be verified by the user.*

---

## 🛠️ Technology Stack

| Technology | Purpose |
|---|---|
| HTML5 | Webpage structure |
| CSS3 | Styling and responsive design |
| JavaScript | Frontend functionality |
| Python | Backend programming |
| Flask | Web application backend |
| SQLite | Local database |
| Scikit-learn | Machine Learning |
| TF-IDF | Text feature extraction |
| Logistic Regression | Expense classification |

---

## 🏗️ System Architecture

```text
              USER
                |
                v
       FRONTEND INTERFACE
       HTML / CSS / JavaScript
                |
                v
         FLASK BACKEND
             Python
                |
       +--------+---------+
       |                  |
       v                  v
  SMARTSPEND AI       SQLITE DATABASE
  TF-IDF + ML         Local Storage
       |                  |
       +--------+---------+
                |
                v
       UPDATED DASHBOARD
```

---

## 📁 Project Structure

```text
Smart_Budget_Buddy_Final/
│
├── index.html
├── style.css
├── script.js
├── server.py
├── requirements.txt
├── README.md
├── PROJECT_AUDIT.md
│
├── data/
│   └── budget_buddy.db
│
├── models/
│   └── category_classifier.joblib
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
└── Dataset CSV Files
```

---

## 💻 Installation and Setup

Follow these steps to run the project on your computer.

### Prerequisites

- Python installed on your computer.
- Visual Studio Code (recommended).
- pip package manager.

### Step 1: Download the Project

Download or clone the project repository.

```bash
git clone YOUR_GITHUB_REPOSITORY_LINK
```

Alternatively, download the ZIP and extract it.

### Step 2: Open the Project

Open the extracted project folder in Visual Studio Code.

### Step 3: Create a Virtual Environment

Open the VS Code terminal and run:

```bash
python -m venv .venv
```

### Step 4: Activate the Virtual Environment

For Windows PowerShell:

```powershell
.\.venv\Scripts\Activate.ps1
```

### Step 5: Install Dependencies

```bash
python -m pip install -r requirements.txt
```

### Step 6: Run the Application

```bash
python server.py
```

Open the local URL displayed in your terminal in your web browser.

---

## 🧪 Testing

The project includes automated backend tests to verify important application functionality.

Run the tests using:

```bash
python -m unittest discover -s tests -v
```

**Testing status:** 15 automated backend tests passed during project testing.

The tests cover areas such as:
- API health and first-run state.
- Expense and income validation.
- Transaction saving and retrieval.
- Database state persistence.
- SmartSpend AI classification.
- Missing or mismatched model handling.
- Invalid transaction data.

---

## 🔒 Data Storage and Privacy

- The project uses a local SQLite database.
- Financial records are stored locally by the application.
- Users should keep backups of their database.
- The project is designed for local use and demonstration.

---

## 🔮 Future Scope

Possible future improvements include:

- Dedicated mobile application.
- Improved ML classification using more real-world training data.
- Spending anomaly detection.
- More advanced spending prediction.
- Enhanced personalised financial recommendations.
- Additional visual reports and analytics.

---

## 🎯 Project Objective

The main objective of Smart Budget Buddy is to make personal finance management easier for students.

By combining budgeting tools, expense tracking, savings goals, and machine-learning-based expense suggestions, the project encourages students to become more financially aware and responsible.

---

## 👥 Team Information

**Project Name:** Smart Budget Buddy – Student Edition

**Team Name:** [Enter Your Team Name]

**Team Members:** [Enter Team Member Names]

**College Name:** [Enter College Name]

**Hackathon:** [Enter Hackathon Name]

---

## 🙌 Conclusion

Smart Budget Buddy is more than an expense tracker. It is a student-focused financial management solution that helps users understand their spending, manage their allowance, work towards savings goals, and make smarter financial decisions.

### Smart Budget Buddy – Spend Smarter. Save Better. 💚
