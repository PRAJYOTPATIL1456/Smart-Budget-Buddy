
const KEY = "budgetBuddyStudentV2";

const $ = id => document.getElementById(id);

const money = n =>
  "₹" + Math.abs(Number(n) || 0).toLocaleString("en-IN", {
    maximumFractionDigits: 2
  });

function localDateString(date = new Date()) {
  const year = date.getFullYear();
  const month = String(date.getMonth() + 1).padStart(2, "0");
  const day = String(date.getDate()).padStart(2, "0");
  return `${year}-${month}-${day}`;
}

function monthKeyFromDate(date) {
  return String(date || "").slice(0, 7);
}

function getMonthKey(record) {
  const date = normalizeDate(record.date);
  return date ? monthKeyFromDate(date) : null;
}

function normalizeDate(value) {
  const date = String(value || "").trim();

  let match = date.match(/^(\d{4})-(\d{1,2})-(\d{1,2})$/);

  if (match) {
    return `${match[1]}-${String(match[2]).padStart(2, "0")}-${String(match[3]).padStart(2, "0")}`;
  }

  match = date.match(/^(\d{1,2})[/-](\d{1,2})[/-](\d{4})$/);

  if (match) {
    return `${match[3]}-${String(match[2]).padStart(2, "0")}-${String(match[1]).padStart(2, "0")}`;
  }

  return null;
}

function isValidIsoDate(value) {
  if (!/^\d{4}-\d{2}-\d{2}$/.test(value)) return false;
  const parsed = new Date(`${value}T00:00:00Z`);
  return !Number.isNaN(parsed.getTime()) && parsed.toISOString().slice(0, 10) === value;
}

function esc(value) {
  return String(value).replace(/[&<>"']/g, c => ({
    "&": "&amp;",
    "<": "&lt;",
    ">": "&gt;",
    '"': "&quot;",
    "'": "&#39;"
  }[c]));
}

function loadState() {
  try {
    const saved = JSON.parse(localStorage.getItem(KEY) || "null");

    if (saved && typeof saved === "object") {
      return saved;
    }
  } catch (error) {
    console.error("Could not load saved budget data:", error);
  }

  return {
    allowance: 8000,
    expenses: [],
    incomes: [],
    goal: null
  };
}

let state = loadState();

state.allowance =
  Number(state.allowance) > 0 ? Number(state.allowance) : 8000;

state.expenses = Array.isArray(state.expenses) ? state.expenses : [];
state.incomes = Array.isArray(state.incomes) ? state.incomes : [];

state.expenses.forEach(expense => {
  expense.date = normalizeDate(expense.date) || localDateString();
  expense.monthKey = getMonthKey(expense);
});

state.incomes.forEach(income => {
  income.date = normalizeDate(income.date) || localDateString();
  income.monthKey = getMonthKey(income);
});

if (state.goal && typeof state.goal === "object") {
  state.goal.saved = Math.max(0, Number(state.goal.saved) || 0);
}

const today = new Date();
const currentMonthKey = monthKeyFromDate(localDateString());

function currentExpenses() {
  return state.expenses.filter(
    expense => getMonthKey(expense) === currentMonthKey
  );
}

function currentIncomes() {
  return state.incomes.filter(
    income => getMonthKey(income) === currentMonthKey
  );
}

function totalOf(records) {
  return records.reduce(
    (total, record) => total + (Number(record.amount) || 0),
    0
  );
}

function spent() {
  return totalOf(currentExpenses());
}

function extraIncome() {
  return totalOf(currentIncomes());
}

function remainingBalance() {
  return state.allowance + extraIncome() - spent();
}

function leftDays() {
  const lastDay = new Date(
    today.getFullYear(),
    today.getMonth() + 1,
    0
  ).getDate();

  return Math.max(1, lastDay - today.getDate() + 1);
}

let databaseReady = false;
let saveQueue = Promise.resolve();

function showStorageStatus(message, statusClass = "") {
  const element = $("storageStatus");
  if (!element) return;
  element.textContent = message;
  element.className = "storage-status" + (statusClass ? " " + statusClass : "");
}

function save() {
  // Keep a browser backup so work is not lost if the local server is stopped.
  localStorage.setItem(KEY, JSON.stringify(state));
  render();

  if (databaseReady) {
    const snapshot = JSON.stringify(state);
    saveQueue = saveQueue.then(async () => {
      const response = await fetch("/api/state", {
        method: "PUT",
        headers: { "Content-Type": "application/json" },
        body: snapshot
      });
      if (!response.ok) {
        const result = await response.json().catch(() => ({}));
        throw new Error(result.error || "Could not save to SQLite.");
      }
      showStorageStatus("SQLite connected · changes saved", "connected");
    }).catch(error => {
      console.error("SQLite save failed:", error);
      showStorageStatus("SQLite save failed · browser backup kept", "error");
    });
  }
}

function normaliseLoadedState(loaded) {
  const safe = loaded && typeof loaded === "object" ? loaded : {};
  safe.allowance = Number(safe.allowance) > 0 ? Number(safe.allowance) : 8000;
  safe.expenses = Array.isArray(safe.expenses) ? safe.expenses : [];
  safe.incomes = Array.isArray(safe.incomes) ? safe.incomes : [];
  safe.expenses.forEach(expense => {
    expense.date = normalizeDate(expense.date) || localDateString();
    expense.monthKey = getMonthKey(expense);
  });
  safe.incomes.forEach(income => {
    income.date = normalizeDate(income.date) || localDateString();
    income.monthKey = getMonthKey(income);
  });
  if (safe.goal && typeof safe.goal === "object") {
    safe.goal.saved = Math.max(0, Number(safe.goal.saved) || 0);
  } else {
    safe.goal = null;
  }
  return safe;
}

async function initialiseDatabase() {
  showStorageStatus("Connecting to SQLite...");
  try {
    const response = await fetch("/api/state");
    if (!response.ok) throw new Error("Flask database endpoint is unavailable.");
    const result = await response.json();

    if (result.initialized) {
      // SQLite is the primary source after the first successful migration.
      state = normaliseLoadedState(result.state);
    } else {
      // First run: migrate the user's existing browser data into SQLite.
      state = normaliseLoadedState(state);
      const migration = await fetch("/api/state", {
        method: "PUT",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(state)
      });
      if (!migration.ok) throw new Error("Could not migrate browser data into SQLite.");
    }

    localStorage.setItem(KEY, JSON.stringify(state));
    databaseReady = true;
    render();
    showStorageStatus("SQLite connected · changes saved", "connected");
  } catch (error) {
    console.error("Database initialisation failed:", error);
    showStorageStatus("SQLite unavailable · using browser backup", "error");
  }
}

function signedMoney(value) {
  return value < 0 ? "−" + money(value) : money(value);
}

// Dashboard
function renderDashboard() {
  $("monthLabel").textContent = today.toLocaleDateString("en-IN", {
    month: "long",
    year: "numeric"
  });

  const monthlyExpenses = currentExpenses();
  const totalSpent = spent();
  const totalIncome = extraIncome();
  const remaining = remainingBalance();
  const daily = Math.max(0, remaining) / leftDays();

  $("allowanceDisplay").textContent = money(state.allowance);
  $("spentDisplay").textContent = money(totalSpent);
  $("remainingDisplay").textContent = signedMoney(remaining);
  $("dailyDisplay").textContent = money(daily);
  $("allowanceInput").value = state.allowance;

  $("spentHint").textContent =
    `${monthlyExpenses.length} expenses this month`;

  $("remainingHint").textContent =
    remaining < 0
      ? "You are over your available budget"
      : `${money(totalIncome)} extra income included`;

  const percentage = state.allowance > 0
    ? totalSpent / state.allowance * 100
    : 0;

  $("budgetProgress").style.width =
    Math.min(100, percentage) + "%";

  $("budgetPercent").textContent = Math.round(percentage) + "%";

  const daysPassed = today.getDate();

  const daysInMonth = new Date(
    today.getFullYear(),
    today.getMonth() + 1,
    0
  ).getDate();

  const projectedSpending =
    (totalSpent / Math.max(1, daysPassed)) * daysInMonth;

  const projection =
    state.allowance + totalIncome - projectedSpending;

  $("forecastDisplay").textContent = signedMoney(projection);

  $("forecastText").textContent =
    projection < 0
      ? "At this pace, you may spend more than your available monthly budget."
      : "At the current pace, this is your estimated month-end balance.";

  $("smartTip").textContent =
    remaining < 0
      ? "You have exceeded your available budget. Review optional expenses."
      : daily < 100
        ? "Your daily safe-spend estimate is low. Prioritise essentials."
        : `Try to stay near ${money(daily)} per day until month end.`;
}

// Transaction history
function allTransactions() {
  const expenses = state.expenses.map(record => ({
    ...record,
    type: "expense",
    displayName: record.title,
    date: normalizeDate(record.date)
  }));

  const incomes = state.incomes.map(record => ({
    ...record,
    type: "income",
    displayName: record.source,
    date: normalizeDate(record.date)
  }));

  return [...expenses, ...incomes].sort((a, b) => {
    if (a.date !== b.date) {
      return String(b.date).localeCompare(String(a.date));
    }

    return Number(b.id) - Number(a.id);
  });
}

function getFilteredTransactions() {
  const mode = $("filterMode").value;
  let records = allTransactions();

  if (mode === "date") {
    const selectedDate = $("singleDateFilter").value;

    if (!selectedDate) {
      return [];
    }

    records = records.filter(record => record.date === selectedDate);
  }

  if (mode === "range") {
    const start = $("startDateFilter").value;
    const end = $("endDateFilter").value;

    if (start && end && start > end) {
      $("filterSummary").textContent =
        "Start date cannot be later than end date.";
      return null;
    }

    if (start) {
      records = records.filter(record => record.date >= start);
    }

    if (end) {
      records = records.filter(record => record.date <= end);
    }
  }

  return records;
}

function renderFilters() {
  const mode = $("filterMode").value;

  $("singleDateGroup").style.display =
    mode === "date" ? "flex" : "none";

  $("startDateGroup").style.display =
    mode === "range" ? "flex" : "none";

  $("endDateGroup").style.display =
    mode === "range" ? "flex" : "none";

  renderTransactions();
}

function renderTransactions() {
  const records = getFilteredTransactions();
  const list = $("transactionList");

  if (records === null) {
    list.innerHTML =
      '<p class="empty-state muted">Please correct the date range.</p>';
    return;
  }

  const mode = $("filterMode").value;

  if (mode === "date" && !$("singleDateFilter").value) {
    $("filterSummary").textContent = "Select a date to view transactions.";
  } else if (mode === "range") {
    $("filterSummary").textContent =
      "Showing transactions within the selected date range.";
  } else {
    $("filterSummary").textContent =
      `Showing ${records.length} transaction(s).`;
  }

  if (!records.length) {
    list.innerHTML =
      '<p class="empty-state muted">No transactions found for this selection.</p>';
    return;
  }

  list.innerHTML = records.map(record => {
    const isIncome = record.type === "income";
    const sign = isIncome ? "+" : "−";
    const amountClass = isIncome ? "income-amount" : "expense-amount";
    const label = isIncome ? "Income" : esc(record.category || "Other");

    return `
      <div class="transaction">
        <div>
          <b>${esc(record.displayName || "Transaction")}</b>
          <small>${label} · ${esc(record.date)}</small>
        </div>

        <div class="transaction-actions">
          <strong class="${amountClass}">
            ${sign}${money(record.amount)}
          </strong>

          <button
            type="button"
            class="edit-btn"
            data-edit-type="${record.type}"
            data-id="${esc(record.id)}"
            aria-label="Edit transaction"
          >Edit</button>
          <button
            type="button"
            class="delete-btn"
            data-delete-type="${record.type}"
            data-id="${esc(record.id)}"
            aria-label="Delete transaction"
          >Delete</button>
        </div>
      </div>
    `;
  }).join("");
}

// Saving goal
function renderGoal() {
  $("goalCard").innerHTML = state.goal
    ? (() => {
        const target = Number(state.goal.amount) || 0;

        const saved = Math.min(
          target,
          Math.max(0, Number(state.goal.saved) || 0)
        );

        const progress = target > 0
          ? Math.min(100, saved / target * 100)
          : 0;

        return `
          <b>${esc(state.goal.name)}</b>
          <p class="muted">
            Target: ${money(target)} · Saved: ${money(saved)}
          </p>

          <div class="progress-track">
            <div class="progress-fill" style="width:${progress}%"></div>
          </div>

          <p class="muted">
            ${Math.round(progress)}% completed ·
            Suggested monthly saving: ${money(target / 6)}
          </p>

          <button type="button" data-goal-update>
            Update saved amount
          </button>
        `;
      })()
    : `
        <b>No goal set yet</b>
        <p class="muted">Create a goal and keep moving towards it.</p>
      `;
}

function render() {
  renderDashboard();
  renderFilters();
  renderGoal();
}

// Allowance form
$("allowanceForm").addEventListener("submit", event => {
  event.preventDefault();

  const amount = Number($("allowanceInput").value);

  if (!Number.isFinite(amount) || amount <= 0) {
    return alert("Enter a valid allowance.");
  }

  state.allowance = amount;
  save();
});

// SmartSpend AI: suggest a category from the expense description.
$("suggestCategoryButton").addEventListener("click", async () => {
  const title = $("expenseTitle").value.trim();
  const button = $("suggestCategoryButton");
  const message = $("categorySuggestion");
  if (!title) {
    message.textContent = "Enter an expense name first, then ask AI to suggest a category.";
    return;
  }
  button.disabled = true;
  button.textContent = "Analysing expense...";
  message.textContent = "SmartSpend AI is checking the description...";
  try {
    const response = await fetch("/api/ml/classify", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ title })
    });
    const result = await response.json().catch(() => ({}));
    if (!response.ok) throw new Error(result.error || "Could not get an AI suggestion.");
    const categorySelect = $("expenseCategory");
    const optionExists = Array.from(categorySelect.options).some(option => option.value === result.category);
    if (optionExists) categorySelect.value = result.category;
    if (result.needs_review) {
      message.textContent =
        `SmartSpend AI suggests ${result.category} (${result.confidence_percent}% model probability), ` +
        `but the result is uncertain. Your current category was not changed. ` +
        "Please choose the correct category yourself.";
    } else if (result.match_type === "keyword_rule") {
      message.textContent =
        `SmartSpend AI matched a common expense keyword: ${result.category}. ` +
        "This is a rule-based suggestion, not a probability. Please verify before saving.";
    } else {
      message.textContent =
        `Suggested category: ${result.category} (${result.confidence_percent}% model probability). ` +
        "This is an estimate, not a guarantee. Please verify before saving.";
    }
  } catch (error) {
    message.textContent = error.message;
  } finally {
    button.disabled = false;
    button.textContent = "✦ Suggest with SmartSpend AI";
  }
});

// Add expense with a selected date
$("expenseForm").addEventListener("submit", event => {
  event.preventDefault();

  const title = $("expenseTitle").value.trim();
  const amount = Number($("expenseAmount").value);
  const category = $("expenseCategory").value;
  const date = $("expenseDate").value;

  if (!title || !Number.isFinite(amount) || amount <= 0 || !date) {
    return alert("Enter valid expense details.");
  }

  state.expenses.push({
    id: Date.now() + Math.random(),
    title,
    amount,
    category,
    date,
    monthKey: monthKeyFromDate(date)
  });

  event.target.reset();
  $("expenseDate").value = localDateString();

  save();
});

// Add extra income
$("incomeForm").addEventListener("submit", event => {
  event.preventDefault();

  const source = $("incomeSource").value.trim();
  const amount = Number($("incomeAmount").value);
  const date = $("incomeDate").value;

  if (!source || !Number.isFinite(amount) || amount <= 0 || !date) {
    return alert("Enter valid income details.");
  }

  state.incomes.push({
    id: Date.now() + Math.random(),
    source,
    amount,
    date,
    monthKey: monthKeyFromDate(date)
  });

  event.target.reset();
  $("incomeDate").value = localDateString();

  save();
});

// Delete expense or income
$("transactionList").addEventListener("click", event => {
  const editButton = event.target.closest("[data-edit-type]");
  if (editButton) {
    const id = editButton.dataset.id;
    const type = editButton.dataset.editType;
    const collection = type === "expense" ? state.expenses : state.incomes;
    const record = collection.find(item => String(item.id) === String(id));
    if (!record) return;

    if (type === "expense") {
      const title = prompt("Expense name:", record.title);
      if (title === null) return;
      const amountText = prompt("Amount (₹):", record.amount);
      if (amountText === null) return;
      const amount = Number(amountText);
      const category = prompt(
        "Category (Food, Travel, Education, Shopping, Entertainment, Bills, Other):",
        record.category || "Other"
      );
      if (category === null) return;
      const date = prompt("Date (YYYY-MM-DD):", record.date);
      if (date === null) return;
      if (!title.trim() || !Number.isFinite(amount) || amount <= 0 ||
          !isValidIsoDate(date) ||
          (!["Food", "Travel", "Education", "Shopping", "Entertainment", "Bills", "Other"].includes(category) &&
           category !== record.category)) {
        return alert("Invalid details. Check the name, positive amount, category and YYYY-MM-DD date.");
      }
      record.title = title.trim();
      record.amount = amount;
      record.category = category;
      record.date = date;
      record.monthKey = monthKeyFromDate(date);
    } else {
      const source = prompt("Income source:", record.source);
      if (source === null) return;
      const amountText = prompt("Amount (₹):", record.amount);
      if (amountText === null) return;
      const amount = Number(amountText);
      const date = prompt("Date (YYYY-MM-DD):", record.date);
      if (date === null) return;
      if (!source.trim() || !Number.isFinite(amount) || amount <= 0 ||
          !isValidIsoDate(date)) {
        return alert("Invalid details. Check the source, positive amount and YYYY-MM-DD date.");
      }
      record.source = source.trim();
      record.amount = amount;
      record.date = date;
      record.monthKey = monthKeyFromDate(date);
    }
    save();
    return;
  }

  const button = event.target.closest("[data-delete-type]");
  if (!button) return;
  const id = button.dataset.id;
  const type = button.dataset.deleteType;

  if (type === "expense") {
    state.expenses = state.expenses.filter(
      record => String(record.id) !== String(id)
    );
  }

  if (type === "income") {
    state.incomes = state.incomes.filter(
      record => String(record.id) !== String(id)
    );
  }

  save();
});

// Date filters
$("filterMode").addEventListener("change", renderFilters);

$("singleDateFilter").addEventListener("change", renderTransactions);
$("startDateFilter").addEventListener("change", renderTransactions);
$("endDateFilter").addEventListener("change", renderTransactions);

// Update saving progress
$("goalCard").addEventListener("click", event => {
  if (!event.target.closest("[data-goal-update]") || !state.goal) {
    return;
  }

  const entered = prompt(
    "Enter the total amount you have saved towards this goal:",
    state.goal.saved || 0
  );

  if (entered === null) return;

  const saved = Number(entered);

  if (!Number.isFinite(saved) || saved < 0) {
    return alert("Enter a valid saved amount.");
  }

  state.goal.saved = saved;
  save();
});

// Purchase checker
$("checkPurchase").addEventListener("click", () => {
  const name = $("purchaseName").value.trim() || "This purchase";
  const price = Number($("purchasePrice").value);
  const remaining = remainingBalance();
  const daily = Math.max(0, remaining) / leftDays();
  const output = $("decisionResult");

  if (!Number.isFinite(price) || price <= 0) {
    output.className = "decision-result result-warn";
    output.textContent = "Enter a valid purchase amount.";
    return;
  }

  const after = remaining - price;
  const share = price / Math.max(1, state.allowance) * 100;

  let className;
  let title;
  let message;

  if (after < 0) {
    className = "result-bad";
    title = "Budget warning";
    message =
      `${name} would put you ${money(-after)} below zero. ` +
      "Consider delaying it or choosing a cheaper option.";
  } else if (price > daily * 3 || share > 20) {
    className = "result-warn";
    title = "Think it through";
    message =
      "This purchase uses a noticeable part of your available money. " +
      `You would have ${money(after)} left. Check essentials first.`;
  } else {
    className = "result-good";
    title = "Looks manageable";
    message =
      "This purchase appears manageable from the numbers entered. " +
      `You would have ${money(after)} left. Remember upcoming essentials.`;
  }

  output.className = "decision-result " + className;

  output.innerHTML = `
    <b>${esc(title)}</b><br>
    ${esc(message)}<br>
    <small>Price: ${money(price)} · ${Math.round(share)}% of allowance</small>
  `;
});

// Create saving goal
$("saveGoal").addEventListener("click", () => {
  const name = $("goalName").value.trim();
  const amount = Number($("goalAmount").value);

  if (!name || !Number.isFinite(amount) || amount <= 0) {
    return alert("Enter a goal name and valid target.");
  }

  const previousSaved =
    state.goal && state.goal.name === name
      ? Number(state.goal.saved) || 0
      : 0;

  state.goal = { name, amount, saved: previousSaved };
  save();
});

// Local rule-based spending insights
function localInsights() {
  const expenses = currentExpenses();
  const total = spent();
  const income = extraIncome();
  const remaining = remainingBalance();
  const groups = {};

  expenses.forEach(expense => {
    const category = expense.category || "Other";
    groups[category] =
      (groups[category] || 0) + Number(expense.amount);
  });

  const top = Object.entries(groups).sort((a, b) => b[1] - a[1])[0];
  const advice = [];

  if (!expenses.length) {
    advice.push(
      "Add some expenses this month to build a useful spending profile."
    );

    if (income > 0) {
      advice.push(`You have recorded ${money(income)} in extra income this month.`);
    }

    return advice;
  }

  if (top) {
    advice.push(
      `Your largest category is ${top[0]} at ${money(top[1])}. Review it first for possible savings.`
    );
  }

  const percentage = total / Math.max(1, state.allowance) * 100;

  advice.push(
    percentage > 100
      ? `You have spent ${Math.round(percentage)}% of your allowance. Review optional spending.`
      : percentage > 75
        ? `You have spent ${Math.round(percentage)}% of your allowance. Reduce optional spending.`
        : `You have spent ${Math.round(percentage)}% of your allowance. Keep tracking your expenses.`
  );

  if (income > 0) {
    advice.push(
      `You have received ${money(income)} in extra income this month.`
    );
  }

  advice.push(
    remaining >= 0
      ? `Your remaining balance is ${money(remaining)}, around ${money(remaining / leftDays())} per day until month end.`
      : `You are ${money(-remaining)} below zero. Consider adjusting your plan.`
  );

  if (top && top[1] > state.allowance * 0.3) {
    advice.push(
      `${top[0]} uses over 30% of your allowance. Try a weekly limit for this category.`
    );
  }

  return advice;
}

// Smart Spending Coach
$("getInsights").addEventListener("click", () => {
  const button = $("getInsights");
  const output = $("aiInsights");

  button.disabled = true;
  button.textContent = "Analysing...";

  try {
    const insights = localInsights();

    output.innerHTML =
      '<span class="eyebrow">SMART SPENDING ANALYSIS</span>' +
      insights.map(item =>
        `<p class="tip-box">${esc(item)}</p>`
      ).join("") +
      '<small class="muted">Personalised, rule-based analysis using your recorded expenses and income. No external AI service is used.</small>';
  } finally {
    button.disabled = false;
    button.textContent = "Analyse my spending";
  }
});

// Set default dates
$("expenseDate").value = localDateString();
$("incomeDate").value = localDateString();

// Render immediately from the browser backup, then connect/migrate to SQLite.
localStorage.setItem(KEY, JSON.stringify(state));
render();
initialiseDatabase();
