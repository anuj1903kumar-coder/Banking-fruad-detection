"""
Automated Test Suite for Banking Fraud Detection System
Uses standard library unittest with FastAPI TestClient.
"""

import io
import os
import sys
import unittest

# Ensure workspace root is in sys.path
WORKSPACE_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if WORKSPACE_ROOT not in sys.path:
    sys.path.insert(0, WORKSPACE_ROOT)

from fastapi.testclient import TestClient

from app.main import app
from app.detector import detector


class FraudDetectionTestCase(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.client = TestClient(app)

    def test_01_health_check(self):
        response = self.client.get("/api/health")
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertEqual(data["status"], "healthy")
        self.assertTrue(data["model_loaded"])
        self.assertIn("XGBoost", data["engine"])

    def test_02_model_info(self):
        response = self.client.get("/api/model/info")
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertEqual(data["model_type"], "XGBoost")
        self.assertTrue(data["model_loaded"])
        self.assertIn("metrics", data)
        self.assertIn("feature_importance", data)
        self.assertGreater(len(data["feature_importance"]), 0)

    def test_03_evaluate_genuine_transaction(self):
        payload = {
            "account_id": "ACC-USER-01",
            "recipient_id": "MCH-GROCERY-01",
            "transaction_type": "PAYMENT",
            "amount": 12.50,
            "old_balance_orig": 1500.0,
            "new_balance_orig": 1487.50,
            "velocity_1h": 1,
            "distance_from_home_km": 2.5,
            "is_foreign": False,
            "is_high_risk_merchant": False,
            "device_trust_score": 0.95
        }
        response = self.client.post("/api/fraud-detection", json=payload)
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertEqual(data["verdict"], "GENUINE")
        self.assertFalse(data["is_fraud"])
        self.assertEqual(data["action"], "ALLOW")
        self.assertLess(data["risk_score"], 0.50)
        self.assertGreater(len(data["reasons"]), 0)

    def test_04_evaluate_fraud_transaction(self):
        payload = {
            "account_id": "ACC-VICTIM-99",
            "recipient_id": "REC-UNKNOWN-00",
            "transaction_type": "TRANSFER",
            "amount": 95000.0,
            "old_balance_orig": 95000.0,
            "new_balance_orig": 0.0,
            "velocity_1h": 5,
            "distance_from_home_km": 1200.0,
            "is_foreign": True,
            "is_high_risk_merchant": True,
            "device_trust_score": 0.10
        }
        response = self.client.post("/api/fraud-detection", json=payload)
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertEqual(data["verdict"], "FRAUD")
        self.assertTrue(data["is_fraud"])
        self.assertEqual(data["action"], "BLOCK")
        self.assertGreaterEqual(data["risk_score"], 0.70)
        self.assertTrue(any("drained" in r.lower() for r in data["reasons"]))

    def test_05_batch_evaluation(self):
        batch = {
            "transactions": [
                {
                    "account_id": "ACC-TEST-1",
                    "recipient_id": "MCH-TEST-1",
                    "transaction_type": "PAYMENT",
                    "amount": 25.0,
                    "old_balance_orig": 1000.0
                },
                {
                    "account_id": "ACC-TEST-2",
                    "recipient_id": "REC-TEST-2",
                    "transaction_type": "TRANSFER",
                    "amount": 80000.0,
                    "old_balance_orig": 80000.0,
                    "new_balance_orig": 0.0,
                    "velocity_1h": 6,
                    "device_trust_score": 0.15,
                    "is_high_risk_merchant": True
                }
            ]
        }
        response = self.client.post("/api/fraud-detection/batch", json=batch)
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertEqual(data["total_evaluated"], 2)
        self.assertEqual(data["fraud_detected"], 1)
        self.assertEqual(data["genuine_detected"], 1)
        self.assertEqual(len(data["results"]), 2)

    def test_06_csv_upload_evaluation(self):
        csv_data = (
            "account_id,recipient_id,transaction_type,amount,old_balance_orig,new_balance_orig,velocity_1h,device_trust_score,is_foreign,is_high_risk_merchant\n"
            "ACC-1,REC-1,PAYMENT,15.00,500.00,485.00,1,0.95,0,0\n"
            "ACC-2,REC-2,TRANSFER,60000.00,60000.00,0.00,5,0.15,1,1\n"
        )
        files = {"file": ("test.csv", io.BytesIO(csv_data.encode("utf-8")), "text/csv")}
        response = self.client.post("/api/fraud-detection/upload-csv", files=files)
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertEqual(data["status"], "success")
        self.assertEqual(data["total_rows"], 2)
        self.assertEqual(data["fraud_detected"], 1)
        self.assertEqual(data["genuine_detected"], 1)

    def test_07_simulation_endpoint(self):
        response = self.client.post("/api/simulate?count=4")
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertEqual(data["status"], "success")
        self.assertEqual(data["simulated_count"], 4)
        self.assertEqual(len(data["results"]), 4)

    def test_08_audit_log_and_export(self):
        res = self.client.get("/api/transactions?limit=10")
        self.assertEqual(res.status_code, 200)
        self.assertIsInstance(res.json(), list)

        stats = self.client.get("/api/stats")
        self.assertEqual(stats.status_code, 200)
        s_data = stats.json()
        self.assertIn("total_transactions", s_data)
        self.assertIn("fraud_count", s_data)

        export_res = self.client.get("/api/transactions/export-csv")
        self.assertEqual(export_res.status_code, 200)
        self.assertIn("text/csv", export_res.headers.get("content-type", ""))
        self.assertGreater(len(export_res.text), 0)

    def test_09_dataset_overview(self):
        res = self.client.get("/api/dataset/overview")
        self.assertEqual(res.status_code, 200)
        data = res.json()
        self.assertIn("dataset_name", data)
        self.assertIn("features_dictionary", data)
        self.assertIn("class_distribution", data)
        self.assertEqual(data["features_count"], 18)

    def test_10_analytics_detailed(self):
        res = self.client.get("/api/analytics/detailed")
        self.assertEqual(res.status_code, 200)
        data = res.json()
        self.assertIn("by_type", data)
        self.assertIn("by_risk_level", data)
        self.assertIn("risk_buckets", data)

    def test_11_report_summary(self):
        res = self.client.get("/api/report/summary")
        self.assertEqual(res.status_code, 200)
        data = res.json()
        self.assertIn("health_grade", data)
        self.assertIn("recommendations", data)
        self.assertIn("stats", data)


if __name__ == "__main__":
    unittest.main()
