"""Run with: python -m unittest discover -s tests -v"""
import tempfile
import unittest
from unittest.mock import patch
from pathlib import Path

import server


class SQLiteApiTests(unittest.TestCase):
    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory()
        server.DB_PATH = Path(self.temp_dir.name) / "test_budget.db"
        server._classifier_cache = None
        server.init_db()
        self.client = server.app.test_client()

    def tearDown(self):
        self.temp_dir.cleanup()

    def sample_state(self):
        return {
            "allowance": 9500,
            "expenses": [{
                "id": "expense-1", "title": "Canteen lunch", "amount": 85,
                "category": "Food", "date": "2026-11-11"
            }],
            "incomes": [{
                "id": "income-1", "source": "Tutoring", "amount": 500,
                "date": "2026-11-10"
            }],
            "goal": {"name": "Laptop", "amount": 30000, "saved": 1500}
        }

    def test_health_and_first_run_state(self):
        health = self.client.get("/api/health")
        self.assertEqual(health.status_code, 200)
        self.assertEqual(health.get_json()["database"], "sqlite")
        state = self.client.get("/api/state")
        self.assertEqual(state.status_code, 200)
        self.assertFalse(state.get_json()["initialized"])

    def test_state_round_trip(self):
        saved = self.client.put("/api/state", json=self.sample_state())
        self.assertEqual(saved.status_code, 200)
        self.assertTrue(saved.get_json()["saved"])
        response = self.client.get("/api/state")
        self.assertTrue(response.get_json()["initialized"])
        state = response.get_json()["state"]
        self.assertEqual(state["allowance"], 9500)
        self.assertEqual(state["expenses"][0]["category"], "Food")
        self.assertEqual(state["incomes"][0]["source"], "Tutoring")
        self.assertEqual(state["goal"]["saved"], 1500)

    def test_invalid_payload_is_rejected(self):
        payload = self.sample_state()
        payload["allowance"] = -1
        response = self.client.put("/api/state", json=payload)
        self.assertEqual(response.status_code, 400)

    def test_invalid_expense_date_is_rejected(self):
        payload = self.sample_state()
        payload["expenses"][0]["date"] = "11/11/2026"
        response = self.client.put("/api/state", json=payload)
        self.assertEqual(response.status_code, 400)



    def test_classifier_rejects_empty_title(self):
        response = self.client.post("/api/ml/classify", json={"title": ""})
        self.assertEqual(response.status_code, 400)

    def test_classifier_returns_prediction_when_model_exists(self):
        from server import CLASSIFIER_PATH
        if not CLASSIFIER_PATH.exists():
            self.skipTest("Train the classifier before testing its prediction endpoint.")
        response = self.client.post("/api/ml/classify", json={"title": "college canteen lunch"})
        self.assertEqual(response.status_code, 200)
        result = response.get_json()
        self.assertIn(result["category"], ["Food", "Travel", "Education", "Shopping", "Entertainment", "Bills", "Other"])
        self.assertIn(result["match_type"], ["keyword_rule", "ml_probability"])
        if result["match_type"] == "ml_probability":
            self.assertGreaterEqual(result["confidence"], 0)
            self.assertLessEqual(result["confidence"], 1)
        else:
            self.assertIsNone(result["confidence"])

    def test_classifier_rejects_model_version_mismatch(self):
        metadata_path = Path(self.temp_dir.name) / "metadata.json"
        metadata_path.write_text(
            '{"scikit_learn_version": "0.0.0"}', encoding="utf-8"
        )
        with patch.object(server, "CLASSIFIER_METADATA_PATH", metadata_path):
            response = self.client.post(
                "/api/ml/classify", json={"title": "unusual campus expense"}
            )
        self.assertEqual(response.status_code, 503)

    def test_classifier_requires_trained_model(self):
        missing_model = Path(self.temp_dir.name) / "missing-model.joblib"
        with patch.object(server, "CLASSIFIER_PATH", missing_model):
            response = self.client.post(
                "/api/ml/classify", json={"title": "canteen lunch"}
            )
        self.assertEqual(response.status_code, 503)


    def test_incomplete_state_cannot_clear_existing_records(self):
        self.client.put("/api/state", json=self.sample_state())
        response = self.client.put("/api/state", json={"allowance": 12000})
        self.assertEqual(response.status_code, 400)
        state = self.client.get("/api/state").get_json()["state"]
        self.assertEqual(len(state["expenses"]), 1)
        self.assertEqual(state["expenses"][0]["title"], "Canteen lunch")

    def test_duplicate_record_ids_are_rejected(self):
        payload = self.sample_state()
        payload["expenses"].append({
            "id": "expense-1", "title": "Another lunch", "amount": 50,
            "category": "Food", "date": "2026-11-11"
        })
        response = self.client.put("/api/state", json=payload)
        self.assertEqual(response.status_code, 400)

    def test_classifier_rejects_non_text_title(self):
        response = self.client.post("/api/ml/classify", json={"title": ["lunch"]})
        self.assertEqual(response.status_code, 400)

    def test_classifier_short_description_rules_cover_all_categories(self):
        cases = {
            "books": "Education",
            "lunch": "Food",
            "bus": "Travel",
            "headphones": "Shopping",
            "movie": "Entertainment",
            "recharge": "Bills",
            "haircut": "Other",
        }
        for title, expected in cases.items():
            with self.subTest(title=title):
                response = self.client.post("/api/ml/classify", json={"title": title})
                self.assertEqual(response.status_code, 200)
                result = response.get_json()
                self.assertEqual(result["category"], expected)
                self.assertEqual(result["match_type"], "keyword_rule")
                self.assertIsNone(result["confidence"])
                self.assertFalse(result["needs_review"])

    def test_classifier_maps_generic_miscellaneous_expense_to_other(self):
        for title in ("miscellaneous expense", "misc expense", "other expense"):
            with self.subTest(title=title):
                response = self.client.post("/api/ml/classify", json={"title": title})
                self.assertEqual(response.status_code, 200)
                result = response.get_json()
                self.assertEqual(result["category"], "Other")
                self.assertEqual(result["match_type"], "keyword_rule")
                self.assertFalse(result["needs_review"])

    def test_classifier_disambiguates_metro_recharge_as_travel(self):
        response = self.client.post(
            "/api/ml/classify", json={"title": "metro recharge"}
        )
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.get_json()["category"], "Travel")

    def test_classifier_ml_result_has_review_metadata(self):
        response = self.client.post(
            "/api/ml/classify", json={"title": "miscellaneous campus purchase"}
        )
        self.assertEqual(response.status_code, 200)
        result = response.get_json()
        self.assertIn(result["match_type"], ["keyword_rule", "ml_probability"])
        if result["match_type"] == "ml_probability":
            self.assertGreaterEqual(result["confidence"], 0)
            self.assertLessEqual(result["confidence"], 1)
            self.assertIn("needs_review", result)

if __name__ == "__main__":
    unittest.main()
