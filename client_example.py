"""
Client Integration Example: Banking Fraud Detection API

Demonstrates how to integrate this Fraud Detection API into your backend
microservices, payment gateways, or web applications.
"""

import requests
import json
import time

API_BASE = "http://localhost:8000"
DETECT_URL = f"{API_BASE}/api/fraud-detection"
BATCH_URL = f"{API_BASE}/api/fraud-detection/batch"


def evaluate_transaction(transaction_data: dict) -> dict:
    """Calls the Fraud Detection API and returns the real-time verdict."""
    try:
        response = requests.post(DETECT_URL, json=transaction_data, timeout=5.0)
        response.raise_for_status()
        return response.json()
    except requests.exceptions.ConnectionError:
        print(f"Error: Could not connect to Fraud Detection API at {DETECT_URL}.")
        print("Please ensure the backend is running via: python run.py")
        return None
    except Exception as e:
        print(f"API Request Failed: {e}")
        return None


def evaluate_batch(transactions: list) -> dict:
    """Evaluates multiple transactions in a single batch request."""
    try:
        response = requests.post(BATCH_URL, json={"transactions": transactions}, timeout=10.0)
        response.raise_for_status()
        return response.json()
    except Exception as e:
        print(f"Batch API Request Failed: {e}")
        return None


def print_verdict(result: dict):
    """Formats and prints the assessment result clearly."""
    if not result:
        return

    verdict = result.get("verdict")
    is_fraud = result.get("is_fraud")
    risk_score = result.get("risk_percentage", 0.0)
    risk_level = result.get("risk_level")
    action = result.get("action")
    reasons = result.get("reasons", [])

    print("-" * 65)
    print(f"Transaction ID : {result.get('transaction_id')}")
    print(f"Type & Amount  : {result.get('transaction_type')} for ${result.get('amount'):,.2f}")
    
    if verdict == "FRAUD":
        print(f"VERDICT        : \033[91m[FRAUD] - TRANSACTION BLOCKED\033[0m")
    else:
        print(f"VERDICT        : \033[92m[GENUINE] - TRANSACTION APPROVED\033[0m")

    print(f"Fraud Risk     : {risk_score:.1f}% ({risk_level} RISK)")
    print(f"Enforced Action: {action}")
    print(f"Explanation    :")
    for r in reasons:
        print(f"   • {r}")
    print("-" * 65 + "\n")


if __name__ == "__main__":
    print("\n" + "=" * 65)
    print("  BANKING FRAUD DETECTION SYSTEM - API CLIENT TEST")
    print("=" * 65 + "\n")

    # Sample 1: Low-Risk Genuine Payment
    sample_genuine = {
        "account_id": "ACC-USER-1029",
        "recipient_id": "MCH-STARBUCKS-01",
        "transaction_type": "PAYMENT",
        "amount": 6.50,
        "old_balance_orig": 1250.00,
        "new_balance_orig": 1243.50,
        "velocity_1h": 1,
        "distance_from_home_km": 1.2,
        "is_foreign": False,
        "is_high_risk_merchant": False,
        "device_trust_score": 0.95
    }

    print(">>> Test 1: Submitting Normal In-Store Payment...")
    res1 = evaluate_transaction(sample_genuine)
    print_verdict(res1)

    # Sample 2: Fraudulent Balance Drain Transfer
    sample_fraud = {
        "account_id": "ACC-VICTIM-8841",
        "recipient_id": "ACC-MULE-9921",
        "transaction_type": "TRANSFER",
        "amount": 75000.00,
        "old_balance_orig": 75000.00,
        "new_balance_orig": 0.00,
        "velocity_1h": 5,
        "distance_from_home_km": 1400.0,
        "is_foreign": True,
        "is_high_risk_merchant": True,
        "device_trust_score": 0.15
    }

    print(">>> Test 2: Submitting High-Risk Balance Liquidation...")
    res2 = evaluate_transaction(sample_fraud)
    print_verdict(res2)

    # Sample 3: Batch Evaluation
    print(">>> Test 3: Submitting Batch Evaluation Request...")
    batch_res = evaluate_batch([sample_genuine, sample_fraud])
    if batch_res:
        print(f"Batch Evaluated : {batch_res['total_evaluated']} transactions")
        print(f"Genuine Count   : {batch_res['genuine_detected']}")
        print(f"Fraud Detected  : {batch_res['fraud_detected']} ({batch_res['fraud_rate_percentage']}%)")
        print(f"Prevented Loss  : ${batch_res['total_fraud_amount_prevented']:,.2f}")
    print("\n" + "=" * 65)
