"""Hybrid, local expense classifier: transparent keyword rules + TF-IDF model."""
import re
import unicodedata

CATEGORIES = ("Food", "Travel", "Education", "Shopping", "Entertainment", "Bills", "Other")

# High-signal student expense terms. These rules help with short inputs where TF-IDF
# has little context; they are suggestions, not a substitute for user confirmation.
KEYWORDS = {
    "Food": {"lunch", "breakfast", "dinner", "canteen", "mess", "snack", "snacks",
             "food", "meal", "meals", "vada", "pav", "coffee", "tea", "chai", "pizza",
             "burger", "sandwich", "grocery", "vegetables", "fruit", "juice"},
    "Travel": {"bus", "train", "metro", "auto", "rickshaw", "cab", "taxi", "fare",
               "petrol", "parking", "commute", "travel", "ticket", "pass", "ride"},
    "Education": {"book", "books", "textbook", "textbooks", "notebook", "notebooks",
                  "stationery", "stationary", "exam", "tuition", "course", "assignment",
                  "photocopy", "lecture", "lab", "semester", "notes", "manual",
                  "calculator", "printing", "project", "college"},
    "Shopping": {"shopping", "bought", "purchase", "headphones", "earbuds", "backpack",
                 "shirt", "shoes", "jeans", "charger", "bottle", "watch", "uniform",
                 "case", "umbrella", "keyboard", "socks", "flask", "raincoat", "sandals"},
    "Entertainment": {"movie", "cinema", "game", "gaming", "music", "concert", "outing",
                      "arcade", "streaming", "netflix", "bowling", "fest", "party",
                      "subscription", "museum"},
    "Bills": {"recharge", "mobile", "phone", "internet", "wifi", "electricity", "water",
              "bill", "data", "plan", "maintenance", "rent", "gas", "utility"},
    "Other": {"haircut", "medicine", "pharmacy", "doctor", "gift", "courier", "bank",
              "donation", "repair", "emergency", "passport", "delivery", "fee", "medical", "prescription",
              "miscellaneous", "misc"},
}

PHRASE_RULES = (
    ("metro card", "Travel"), ("metro recharge", "Travel"),
    ("bus pass", "Travel"), ("bus ticket", "Travel"),
    ("movie ticket", "Entertainment"), ("concert ticket", "Entertainment"),
    ("mobile recharge", "Bills"), ("phone recharge", "Bills"),
    ("data pack", "Bills"), ("internet bill", "Bills"),
    ("wifi bill", "Bills"), ("electricity bill", "Bills"),
    ("water bill", "Bills"), ("college canteen", "Food"),
    ("evening chai", "Food"), ("water flask", "Shopping"),
    ("medical prescription", "Other"), ("engineering textbook", "Education"),
    ("semester books", "Education"), ("class notes", "Education"),
    ("birthday gift", "Other"), ("miscellaneous expense", "Other"),
    ("misc expense", "Other"), ("other expense", "Other"),
    ("unexpected expense", "Other"), ("unclassified expense", "Other"),
)


def normalise_text(value):
    value = unicodedata.normalize("NFKC", str(value or "")).casefold()
    return " ".join(re.findall(r"[a-z0-9]+", value))


def rule_prediction(text):
    cleaned = normalise_text(text)
    if not cleaned:
        return None
    for phrase, category in PHRASE_RULES:
        if phrase in cleaned:
            return category

    tokens = cleaned.split()
    if len(tokens) == 1:
        single_word = {
            "book": "Education", "books": "Education", "textbook": "Education",
            "textbooks": "Education", "notebook": "Education", "notes": "Education",
            "stationery": "Education", "exam": "Education",
            "lunch": "Food", "breakfast": "Food", "dinner": "Food",
            "canteen": "Food", "snack": "Food", "snacks": "Food", "food": "Food",
            "bus": "Travel", "train": "Travel", "metro": "Travel",
            "rickshaw": "Travel", "taxi": "Travel", "recharge": "Bills",
            "mobile": "Bills", "wifi": "Bills", "internet": "Bills",
            "haircut": "Other", "medicine": "Other", "pharmacy": "Other",
            "movie": "Entertainment", "cinema": "Entertainment", "gaming": "Entertainment",
            "headphones": "Shopping", "earbuds": "Shopping", "backpack": "Shopping",
            "shoes": "Shopping", "shirt": "Shopping",
        }
        if tokens[0] in single_word:
            return single_word[tokens[0]]

    scores = {}
    for category, words in KEYWORDS.items():
        scores[category] = sum(2 if token in {"book", "books", "bus", "lunch", "recharge"} else 1
                               for token in tokens if token in words)

    ranked = sorted(scores.items(), key=lambda item: item[1], reverse=True)
    if ranked[0][1] >= 2 and ranked[0][1] > ranked[1][1]:
        return ranked[0][0]
    return None


def classify_text(text, model):
    """Return prediction metadata; ML probability is not a correctness guarantee."""
    rule = rule_prediction(text)
    if rule:
        return {
            "category": rule,
            "confidence": None,
            "confidence_percent": None,
            "needs_review": False,
            "match_type": "keyword_rule",
            "top_alternatives": [],
        }

    probabilities = model.predict_proba([text])[0]
    classes = list(model.classes_)
    ranked = sorted(zip(classes, probabilities), key=lambda item: item[1], reverse=True)
    category, probability = ranked[0]
    second_probability = float(ranked[1][1]) if len(ranked) > 1 else 0.0
    margin = float(probability) - second_probability
    needs_review = float(probability) < 0.55 or margin < 0.15
    return {
        "category": str(category),
        "confidence": round(float(probability), 4),
        "confidence_percent": round(float(probability) * 100, 1),
        "needs_review": needs_review,
        "match_type": "ml_probability",
        "margin": round(margin, 4),
        "top_alternatives": [
            {"category": str(label), "probability": round(float(score), 4)}
            for label, score in ranked[1:3]
        ],
    }
