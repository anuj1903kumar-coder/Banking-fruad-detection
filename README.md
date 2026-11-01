# 🛡️ Enterprise Banking Fraud Detection System

A production-grade, real-time **Banking Transaction Fraud Detection System** powered by a hybrid ensemble of **XGBoost Machine Learning** and an **Expert Financial Heuristics Rule Engine**. 

The system analyzes financial transactions in milliseconds, determines an explicit verdict of **`FRAUD`** (Blocked/Flagged) or **`GENUINE`** (Approved), computes exact fraud risk scores (0–100%), enforces automated actions (`ALLOW`, `CHALLENGE_2FA`, `FLAG_REVIEW`, `BLOCK`), and outputs human-readable explainability statements.

---

## 🚀 Key Features

- **⚡ Sub-Millisecond Real-Time Scoring**: Evaluates incoming transaction payloads via high-speed REST API (`POST /api/fraud-detection`).
- **🎯 Clear Binary Verdicts & Directives**: 
  - Verdict: **`FRAUD`** vs. **`GENUINE`**
  - Action Directives: `ALLOW`, `CHALLENGE_2FA` (trigger SMS/OTP challenge), `FLAG_REVIEW`, or `BLOCK`.
- **🧠 Hybrid AI Ensemble Defense**:
  - **XGBoost Classifier**: Trained on 30,000+ realistic transaction distributions with class imbalance optimization (`scale_pos_weight=10.76`).
  - **Domain Financial Heuristics**: Balance draining detection, velocity spikes, foreign geolocation anomalies, hardware/device trust fingerprinting, off-hours night transactions, and balance calculation discrepancies.
  - **Portable JSON Model Artifact**: Zero pickle security vulnerabilities and 100% cross-platform compatibility.
- **📦 High-Throughput Batch & CSV Evaluation**:
  - `POST /api/fraud-detection/batch`: Process lists of transactions in one round-trip.
  - `POST /api/fraud-detection/upload-csv`: Drag-and-drop or upload transaction CSV files with real-time analytics.
- **📊 Interactive Fintech Dashboard**:
  - Dark-mode responsive operations dashboard at `http://localhost:8000/fraud-detection`.
  - Quick-test benchmark scenarios (Coffee Purchase, Balance Drain, Overseas ATM, Corporate Payroll, Velocity Burst).
  - Live Transaction Traffic Simulator (`Simulate 5 Txns` and auto-streaming toggle).
  - Model Insights & Explainability tab with feature importance rankings and ROC-AUC metrics.
- **📜 Audit Trail & Data Export**:
  - SQLite database tracking all processed transactions, prevented fraud losses ($), and fraud rates (%).
  - Downloadable CSV audit exports (`GET /api/transactions/export-csv`).
- **📖 Auto-Generated OpenAPI / Swagger Docs**:
  - Full interactive API specification at `http://localhost:8000/docs`.

---

## 📁 Project Architecture

```
Banking Fruad Detection/
├── app/
│   ├── __init__.py
│   ├── main.py                    # FastAPI application, REST endpoints & static routes
│   ├── detector.py                # Hybrid ensemble engine (XGBoost + Heuristic rules)
│   ├── models.py                  # Pydantic schemas (Request, Verdict, Batch, Stats, ModelInfo)
│   ├── database.py                # SQLite database audit trail, batch insert & CSV export
│   ├── static/
│   │   ├── css/
│   │   │   └── style.css          # Fintech dashboard styling, widgets & animations
│   │   └── js/
│   │       └── app.js             # Live UI, simulator stream, CSV upload & async fetching
│   └── templates/
│       └── index.html             # Multi-tab single-page web dashboard
├── model/
│   ├── __init__.py
│   ├── train_model.py             # XGBoost model training script with evaluation
│   ├── fraud_model.json           # Native trained XGBoost model artifact (JSON format)
│   └── model_meta.json            # Model hyperparameters, metrics & feature importances
├── tests/
│   ├── __init__.py
│   └── test_fraud_detection.py    # Automated test suite (8 integration & unit tests)
├── client_example.py              # Python client integration example (single & batch)
├── client_example.js              # Node.js / JavaScript client integration example
├── sample_transactions.csv        # Pre-loaded benchmark CSV for bulk testing
├── test_transactions.json         # Benchmark JSON scenarios
├── requirements.txt               # Project dependencies
├── run.py                         # One-click server launcher
└── README.md                      # Complete system documentation
```

---

## ⚡ Quick Start

### 1. Install Dependencies
```bash
pip install -r requirements.txt
```

### 2. Launch the Server
```bash
python run.py
```

Open your browser to:
- **Web Dashboard**: [http://localhost:8000/fraud-detection](http://localhost:8000/fraud-detection) (or [http://localhost:8000](http://localhost:8000))
- **Interactive Swagger Docs**: [http://localhost:8000/docs](http://localhost:8000/docs)
- **ReDoc API Spec**: [http://localhost:8000/redoc](http://localhost:8000/redoc)

### 3. Run Automated Tests
```bash
python -m unittest tests/test_fraud_detection.py -v
```

---

## 🔌 API Reference & Integration Guide

### 1. Single Transaction Evaluation
- **Method**: `POST`
- **URL**: `http://localhost:8000/api/fraud-detection` (or `/api/predict`)
- **Query Parameter (Optional)**: `threshold=0.50` (custom decision boundary)

#### Request Payload:
```json
{
  "account_id": "ACC-904128",
  "recipient_id": "REC-UNKNOWN-719",
  "transaction_type": "TRANSFER",
  "amount": 89500.0,
  "old_balance_orig": 89500.0,
  "new_balance_orig": 0.0,
  "velocity_1h": 4,
  "distance_from_home_km": 185.0,
  "is_foreign": false,
  "is_high_risk_merchant": true,
  "device_trust_score": 0.20
}
```

#### Response Payload:
```json
{
  "transaction_id": "TXN-8A91F4B02E",
  "account_id": "ACC-904128",
  "recipient_id": "REC-UNKNOWN-719",
  "amount": 89500.0,
  "transaction_type": "TRANSFER",
  "verdict": "FRAUD",
  "is_fraud": true,
  "risk_score": 0.85,
  "risk_percentage": 85.0,
  "risk_level": "CRITICAL",
  "action": "BLOCK",
  "confidence": 0.85,
  "reasons": [
    "Sender account drained from $89,500.00 to $0.00 (100.0% drained)",
    "Elevated velocity: 4 transactions in the past hour",
    "Untrusted or spoofed device fingerprint (trust score: 0.20)",
    "Transaction directed to a high-risk merchant or unregulated platform"
  ],
  "risk_factors": [
    {
      "rule": "BALANCE_DRAINING",
      "severity": "CRITICAL",
      "description": "Sender account drained from $89,500.00 to $0.00 (100.0% drained)"
    }
  ],
  "timestamp": "2026-10-23T17:09:15.123456Z"
}
```

---

### 2. High-Throughput Batch Evaluation
- **Method**: `POST`
- **URL**: `http://localhost:8000/api/fraud-detection/batch`

#### Request Payload:
```json
{
  "threshold": 0.50,
  "transactions": [
    {
      "account_id": "ACC-101",
      "recipient_id": "MCH-STORE",
      "transaction_type": "PAYMENT",
      "amount": 14.50,
      "old_balance_orig": 800.00
    },
    {
      "account_id": "ACC-102",
      "recipient_id": "REC-CRYPTO",
      "transaction_type": "TRANSFER",
      "amount": 50000.00,
      "old_balance_orig": 50000.00,
      "new_balance_orig": 0.00,
      "velocity_1h": 5,
      "device_trust_score": 0.15
    }
  ]
}
```

#### Response Summary:
```json
{
  "total_evaluated": 2,
  "fraud_detected": 1,
  "genuine_detected": 1,
  "fraud_rate_percentage": 50.0,
  "total_amount_evaluated": 50014.5,
  "total_fraud_amount_prevented": 50000.0,
  "results": [...]
}
```

---

### 3. CSV File Upload Evaluation
- **Method**: `POST`
- **URL**: `http://localhost:8000/api/fraud-detection/upload-csv`
- **Content-Type**: `multipart/form-data`
- **Field**: `file` (`.csv`)

You can test this endpoint directly in the web dashboard's **Batch & CSV** tab or upload [`sample_transactions.csv`](sample_transactions.csv) via cURL:
```bash
curl -X POST "http://localhost:8000/api/fraud-detection/upload-csv" \
     -F "file=@sample_transactions.csv"
```

---

### 4. Code Integration Examples

#### Python (`client_example.py`)
```python
import requests

API_URL = "http://localhost:8000/api/fraud-detection"

transaction = {
    "account_id": "ACC-100249",
    "recipient_id": "REC-994102",
    "transaction_type": "TRANSFER",
    "amount": 75000.00,
    "old_balance_orig": 75000.00,
    "new_balance_orig": 0.00,
    "velocity_1h": 5,
    "is_foreign": True,
    "is_high_risk_merchant": True,
    "device_trust_score": 0.15
}

response = requests.post(API_URL, json=transaction)
result = response.json()

if result["verdict"] == "FRAUD":
    print(f"Transaction Blocked! Reasons: {result['reasons']}")
else:
    print(f"Transaction Approved! Risk score: {result['risk_percentage']}%")
```

#### Node.js / JavaScript (`client_example.js`)
```javascript
const API_URL = "http://localhost:8000/api/fraud-detection";

async function verifyTransaction(transactionData) {
  const response = await fetch(API_URL, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(transactionData)
  });

  const result = await response.json();

  if (result.verdict === "FRAUD" || result.is_fraud) {
    console.warn("FRAUD ALERT - Transaction Rejected!", result.reasons);
    return { success: false, action: result.action };
  } else {
    console.log("Transaction Genuine - Proceeding with payment.");
    return { success: true, riskScore: result.risk_percentage };
  }
}
```

---

## 🧠 Retraining the XGBoost Model

To retrain the model with customized synthetic parameters or custom transaction datasets:
```bash
python model/train_model.py
```
This script:
1. Synthesizes 30,000+ realistic transaction scenarios with class-imbalanced fraud distribution.
2. Performs feature engineering (balance discrepancy, velocity indicators, device trust, geolocation distance).
3. Trains an XGBoost classifier with `scale_pos_weight` class balancing.
4. Validates metrics (ROC-AUC, Precision, Recall, F1).
5. Exports the model to `model/fraud_model.json` and updates feature importances in `model/model_meta.json`.

---

## 🛡️ Heuristic Financial Rules Summary

| Rule Code | Trigger Condition | Severity | Action |
| :--- | :--- | :---: | :---: |
| `BALANCE_DRAINING` | >95% or complete sender liquidation via `TRANSFER` or `CASH_OUT` | CRITICAL | Enforce Risk Spike / Block |
| `VELOCITY_SPIKE` | 5+ transactions initiated within past 1 hour | HIGH / CRITICAL | Flag for Review / Challenge |
| `UNTRUSTED_DEVICE` | Device trust score < 0.40 (emulators, proxy spoofing) | HIGH | Challenge 2FA / Block |
| `GEO_LOCATION_ANOMALY` | Foreign cross-border origin > 1,000 km from billing home | HIGH | Flag Review / Challenge |
| `HIGH_RISK_MERCHANT` | Crypto exchange, offshore gambling, or unregulated entity | HIGH | Heightened Risk Weight |
| `OFF_HOURS_HIGH_VALUE` | Transaction > $10,000 executed during off-peak hours (1:00-4:00 AM UTC) | MEDIUM | Risk Penalty |
| `BALANCE_DISCREPANCY` | Arithmetic inconsistency: `amount != old_balance - new_balance` | MEDIUM | Anomaly Flag |
