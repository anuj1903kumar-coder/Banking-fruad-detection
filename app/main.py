import os
import io
import csv
import uuid
import random
from datetime import datetime, timezone
from contextlib import asynccontextmanager
from typing import Optional, List

from fastapi import FastAPI, HTTPException, Query, Request, UploadFile, File, Response
from fastapi.responses import HTMLResponse, JSONResponse, FileResponse, PlainTextResponse
from fastapi.staticfiles import StaticFiles
from fastapi.middleware.cors import CORSMiddleware
import pandas as pd

from app.models import (
    TransactionRequest,
    FraudDetectionResponse,
    BatchTransactionRequest,
    BatchTransactionResponse,
    SystemStatsResponse,
    ModelInfoResponse
)
from app.detector import detector
from app.database import (
    init_db,
    save_transaction,
    save_transactions_batch,
    get_transactions,
    get_stats,
    clear_transactions,
    export_transactions_as_csv,
    get_detailed_analytics,
    get_report_summary,
    get_dataset_overview
)


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup: ensure DB and Model are loaded
    init_db()
    detector._load_model()
    print("Banking Fraud Detection System initialized successfully.")
    yield


app = FastAPI(
    title="Banking Fraud Detection API",
    description="Enterprise-grade Real-Time Fraud Detection Engine for Banking & Financial Transactions. Powered by XGBoost Machine Learning and Heuristic Financial Defense Rules.",
    version="2.0.0",
    docs_url="/docs",
    redoc_url="/redoc",
    lifespan=lifespan
)

# Enable CORS for external project integration
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Setup directories
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
STATIC_DIR = os.path.join(BASE_DIR, "static")
TEMPLATES_DIR = os.path.join(BASE_DIR, "templates")
INDEX_HTML = os.path.join(TEMPLATES_DIR, "index.html")

os.makedirs(STATIC_DIR, exist_ok=True)
os.makedirs(TEMPLATES_DIR, exist_ok=True)

app.mount("/static", StaticFiles(directory=STATIC_DIR), name="static")


# --- UI Pages ---

@app.get("/", response_class=FileResponse)
@app.get("/fraud-detection", response_class=FileResponse)
async def serve_fraud_detection_page():
    """Serves the interactive banking fraud detection dashboard."""
    return FileResponse(INDEX_HTML, media_type="text/html")


# --- API Endpoints ---

@app.post("/api/fraud-detection", response_model=FraudDetectionResponse, summary="Detect Fraud in Transaction")
@app.post("/api/predict", response_model=FraudDetectionResponse, summary="Alias for fraud prediction")
async def analyze_transaction(payload: TransactionRequest, threshold: float = Query(default=0.50, ge=0.1, le=0.9)):
    """
    Evaluates a financial transaction in real-time.
    
    Returns:
    - **verdict**: 'FRAUD' or 'GENUINE'
    - **is_fraud**: boolean (true if fraud, false if genuine)
    - **risk_score**: float between 0.00 and 1.00
    - **risk_level**: 'LOW', 'MEDIUM', 'HIGH', or 'CRITICAL'
    - **action**: 'ALLOW', 'CHALLENGE_2FA', 'FLAG_REVIEW', 'BLOCK'
    - **reasons**: explainability statements detailing why the transaction was flagged
    """
    try:
        response = detector.evaluate(payload, threshold=threshold)
        # Persist audit record
        save_transaction(response.model_dump())
        return response
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Fraud evaluation failed: {str(e)}")


@app.post("/api/fraud-detection/batch", response_model=BatchTransactionResponse, summary="Batch evaluate multiple transactions")
async def analyze_batch_transactions(batch: BatchTransactionRequest):
    """Evaluates an array of transactions in high-throughput batch mode."""
    if not batch.transactions:
        raise HTTPException(status_code=400, detail="Transaction list cannot be empty.")

    results: List[FraudDetectionResponse] = []
    audit_data: List[dict] = []
    fraud_count = 0
    genuine_count = 0
    total_amount = 0.0
    fraud_amount = 0.0

    threshold = batch.threshold or 0.50

    for txn in batch.transactions:
        res = detector.evaluate(txn, threshold=threshold)
        results.append(res)
        audit_data.append(res.model_dump())
        total_amount += res.amount
        if res.is_fraud:
            fraud_count += 1
            fraud_amount += res.amount
        else:
            genuine_count += 1

    # Bulk save to database
    save_transactions_batch(audit_data)

    rate = round((fraud_count / len(results) * 100), 2) if results else 0.0

    return BatchTransactionResponse(
        total_evaluated=len(results),
        fraud_detected=fraud_count,
        genuine_detected=genuine_count,
        fraud_rate_percentage=rate,
        total_amount_evaluated=round(total_amount, 2),
        total_fraud_amount_prevented=round(fraud_amount, 2),
        results=results
    )


@app.post("/api/fraud-detection/upload-csv", summary="Upload CSV file of transactions for bulk evaluation")
async def upload_csv_transactions(file: UploadFile = File(...), threshold: float = Query(default=0.50)):
    """
    Processes a CSV file containing transactions, performs fraud evaluation on every row,
    stores results in the audit database, and returns summary metrics along with the annotated rows.
    """
    if not file.filename.lower().endswith(".csv"):
        raise HTTPException(status_code=400, detail="Only CSV files are supported.")

    try:
        contents = await file.read()
        df = pd.read_csv(io.StringIO(contents.decode("utf-8", errors="ignore")))

        # Check required columns
        req_cols = ["account_id", "recipient_id", "transaction_type", "amount"]
        missing = [c for c in req_cols if c not in df.columns]
        if missing:
            raise HTTPException(status_code=400, detail=f"CSV is missing required columns: {missing}")

        results: List[dict] = []
        audit_records: List[dict] = []
        fraud_count = 0
        total_prevented = 0.0

        for _, row in df.iterrows():
            req = TransactionRequest(
                transaction_id=str(row.get("transaction_id")) if pd.notna(row.get("transaction_id")) else None,
                account_id=str(row.get("account_id")),
                recipient_id=str(row.get("recipient_id")),
                transaction_type=str(row.get("transaction_type")),
                amount=float(row.get("amount")),
                old_balance_orig=float(row.get("old_balance_orig", 0.0)) if pd.notna(row.get("old_balance_orig")) else 0.0,
                new_balance_orig=float(row.get("new_balance_orig")) if pd.notna(row.get("new_balance_orig")) else None,
                old_balance_dest=float(row.get("old_balance_dest", 0.0)) if pd.notna(row.get("old_balance_dest")) else 0.0,
                new_balance_dest=float(row.get("new_balance_dest")) if pd.notna(row.get("new_balance_dest")) else None,
                velocity_1h=int(row.get("velocity_1h", 1)) if pd.notna(row.get("velocity_1h")) else 1,
                distance_from_home_km=float(row.get("distance_from_home_km", 0.0)) if pd.notna(row.get("distance_from_home_km")) else 0.0,
                is_foreign=bool(row.get("is_foreign", False)) if pd.notna(row.get("is_foreign")) else False,
                is_high_risk_merchant=bool(row.get("is_high_risk_merchant", False)) if pd.notna(row.get("is_high_risk_merchant")) else False,
                device_trust_score=float(row.get("device_trust_score", 1.0)) if pd.notna(row.get("device_trust_score")) else 1.0
            )

            res = detector.evaluate(req, threshold=threshold)
            res_dict = res.model_dump()
            results.append(res_dict)
            audit_records.append(res_dict)

            if res.is_fraud:
                fraud_count += 1
                total_prevented += res.amount

        # Bulk save
        save_transactions_batch(audit_records)

        return {
            "status": "success",
            "filename": file.filename,
            "total_rows": len(results),
            "fraud_detected": fraud_count,
            "genuine_detected": len(results) - fraud_count,
            "fraud_rate_percentage": round((fraud_count / len(results) * 100), 2) if results else 0.0,
            "total_fraud_amount_prevented": round(total_prevented, 2),
            "evaluated_records": results[:100]  # Return preview of up to 100
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"CSV processing failed: {str(e)}")


@app.get("/api/model/info", response_model=ModelInfoResponse, summary="Get ML Model Metadata & Feature Importance")
async def get_model_information():
    """Returns architecture, training metrics, and feature importance of the active ML model."""
    return detector.get_model_info()


@app.get("/api/transactions", summary="List recent analyzed transactions")
async def list_transactions(
    limit: int = Query(default=50, ge=1, le=500),
    verdict: Optional[str] = Query(default=None, description="Filter by 'FRAUD' or 'GENUINE'")
):
    """Fetches recent transactions processed by the fraud engine."""
    return get_transactions(limit=limit, filter_verdict=verdict)


@app.get("/api/transactions/export-csv", summary="Export audit log to CSV")
async def export_transactions_csv():
    """Streams the complete audit trail as a downloadable CSV file."""
    csv_content = export_transactions_as_csv()
    filename = f"fraud_detection_audit_{datetime.now(timezone.utc).strftime('%Y%m%d_%H%M%S')}.csv"
    return Response(
        content=csv_content,
        media_type="text/csv",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'}
    )


@app.delete("/api/transactions", summary="Reset / clear audit log")
async def reset_transactions():
    """Deletes all audit records from database (useful for resetting demos)."""
    count = clear_transactions()
    return {"status": "success", "message": f"Cleared {count} audit records.", "deleted_count": count}


@app.get("/api/stats", summary="System-wide fraud metrics & analytics")
async def get_system_stats():
    """Returns analytics: total scanned, fraud counts, fraud rate %, and amount saved."""
    return get_stats()


@app.get("/api/analytics/detailed", summary="Aggregated analytics, distributions, and risk buckets")
async def get_analytics_detailed():
    """Returns aggregated transaction metrics by type, risk buckets, actions, and recent trends."""
    return get_detailed_analytics()


@app.get("/api/dataset/overview", summary="Dataset schema, class balance, and benchmark samples")
async def get_dataset_metadata():
    """Returns dataset overview, feature dictionary, class imbalance details, and sample transactions."""
    return get_dataset_overview()


@app.get("/api/report/summary", summary="Executive fraud investigation & compliance report")
async def get_audit_report():
    """Generates an executive fraud investigation and regulatory audit brief."""
    return get_report_summary()


@app.post("/api/simulate", summary="Simulate live transaction traffic")
async def simulate_transactions(count: int = Query(default=5, ge=1, le=50)):
    """
    Generates synthetic real-time transactions with realistic fraud mix
    and evaluates them through the pipeline.
    """
    simulated_results = []
    audit_data = []

    fraud_templates = [
        {"type": "TRANSFER", "amount_range": (35000, 95000), "drain": True, "high_risk": True, "trust": (0.05, 0.30), "foreign": False},
        {"type": "CASH_OUT", "amount_range": (8000, 25000), "drain": True, "high_risk": True, "trust": (0.10, 0.35), "foreign": True},
        {"type": "TRANSFER", "amount_range": (15000, 60000), "drain": False, "high_risk": True, "trust": (0.20, 0.40), "foreign": False}
    ]

    genuine_templates = [
        {"type": "PAYMENT", "amount_range": (4, 150), "drain": False, "high_risk": False, "trust": (0.90, 1.0), "foreign": False},
        {"type": "TRANSFER", "amount_range": (50, 800), "drain": False, "high_risk": False, "trust": (0.85, 0.98), "foreign": False},
        {"type": "CASH_IN", "amount_range": (500, 3500), "drain": False, "high_risk": False, "trust": (0.95, 1.0), "foreign": False},
        {"type": "DEBIT", "amount_range": (20, 250), "drain": False, "high_risk": False, "trust": (0.92, 1.0), "foreign": False}
    ]

    for _ in range(count):
        # 15% fraud probability in simulation
        is_sim_fraud = random.random() < 0.20
        tmpl = random.choice(fraud_templates if is_sim_fraud else genuine_templates)

        amt = round(random.uniform(*tmpl["amount_range"]), 2)
        if tmpl["drain"]:
            old_orig = amt
            new_orig = 0.0
        else:
            old_orig = round(amt + random.uniform(500, 25000), 2)
            new_orig = round(old_orig - amt, 2)

        req = TransactionRequest(
            account_id=f"ACC-{random.randint(100000, 999999)}",
            recipient_id=f"REC-{random.randint(100000, 999999)}",
            transaction_type=tmpl["type"],
            amount=amt,
            old_balance_orig=old_orig,
            new_balance_orig=new_orig,
            velocity_1h=random.randint(4, 9) if is_sim_fraud else random.randint(1, 2),
            distance_from_home_km=round(random.uniform(500, 5000) if tmpl["foreign"] else random.uniform(0.5, 30), 1),
            is_foreign=tmpl["foreign"],
            is_high_risk_merchant=tmpl["high_risk"],
            device_trust_score=round(random.uniform(*tmpl["trust"]), 2)
        )

        res = detector.evaluate(req)
        simulated_results.append(res)
        audit_data.append(res.model_dump())

    save_transactions_batch(audit_data)

    return {
        "status": "success",
        "simulated_count": count,
        "results": simulated_results
    }


@app.get("/api/health", summary="Health Check")
async def health_check():
    """Returns system status and model readiness."""
    return {
        "status": "healthy",
        "service": "Banking Fraud Detection System",
        "version": "2.0.0",
        "model_loaded": detector.model_loaded,
        "model_type": detector.model_meta.get("model_type", "XGBoost"),
        "engine": "Hybrid Ensemble (XGBoost ML + Heuristic Banking Rules)"
    }


@app.get("/api/sample-scenarios", summary="Predefined scenarios for testing")
async def get_sample_scenarios():
    """Provides test payloads representing common legitimate and fraudulent patterns."""
    return [
        {
            "name": "☕ Normal Coffee / Grocery Payment",
            "expected": "GENUINE",
            "payload": {
                "account_id": "ACC-100249",
                "recipient_id": "MCH-STARBUCKS-88",
                "transaction_type": "PAYMENT",
                "amount": 5.75,
                "old_balance_orig": 3420.50,
                "new_balance_orig": 3414.75,
                "old_balance_dest": 125000.0,
                "new_balance_dest": 125005.75,
                "velocity_1h": 1,
                "distance_from_home_km": 2.3,
                "is_foreign": False,
                "is_high_risk_merchant": False,
                "device_trust_score": 0.98,
                "hour_of_day": 14,
                "notes": "Daily morning coffee payment"
            }
        },
        {
            "name": "⚠️ Balance Drain Transfer ($89,500)",
            "expected": "FRAUD",
            "payload": {
                "account_id": "ACC-904128",
                "recipient_id": "REC-UNKNOWN-719",
                "transaction_type": "TRANSFER",
                "amount": 89500.0,
                "old_balance_orig": 89500.0,
                "new_balance_orig": 0.0,
                "old_balance_dest": 0.0,
                "new_balance_dest": 0.0,
                "velocity_1h": 4,
                "distance_from_home_km": 185.0,
                "is_foreign": False,
                "is_high_risk_merchant": True,
                "device_trust_score": 0.20,
                "hour_of_day": 3,
                "notes": "Midnight total balance liquidation"
            }
        },
        {
            "name": "🌐 Overseas ATM Cash-Out Anomaly",
            "expected": "FRAUD",
            "payload": {
                "account_id": "ACC-552109",
                "recipient_id": "ATM-FOREIGN-401",
                "transaction_type": "CASH_OUT",
                "amount": 9500.0,
                "old_balance_orig": 12000.0,
                "new_balance_orig": 2500.0,
                "old_balance_dest": 0.0,
                "new_balance_dest": 9500.0,
                "velocity_1h": 6,
                "distance_from_home_km": 6800.0,
                "is_foreign": True,
                "is_high_risk_merchant": True,
                "device_trust_score": 0.12,
                "hour_of_day": 2,
                "notes": "Suspicious overseas ATM cash-out with untrusted device"
            }
        },
        {
            "name": "💼 Monthly Corporate Payroll Deposit",
            "expected": "GENUINE",
            "payload": {
                "account_id": "CORP-PAYROLL-99",
                "recipient_id": "ACC-774102",
                "transaction_type": "CASH_IN",
                "amount": 4250.0,
                "old_balance_orig": 250000.0,
                "new_balance_orig": 245750.0,
                "old_balance_dest": 1150.0,
                "new_balance_dest": 5400.0,
                "velocity_1h": 1,
                "distance_from_home_km": 0.0,
                "is_foreign": False,
                "is_high_risk_merchant": False,
                "device_trust_score": 1.0,
                "hour_of_day": 10,
                "notes": "Verified bi-weekly corporate payroll"
            }
        },
        {
            "name": "⚡ Rapid Velocity Burst Spike",
            "expected": "FRAUD",
            "payload": {
                "account_id": "ACC-883921",
                "recipient_id": "REC-CRYPTO-554",
                "transaction_type": "TRANSFER",
                "amount": 2800.0,
                "old_balance_orig": 14000.0,
                "new_balance_orig": 11200.0,
                "velocity_1h": 9,
                "distance_from_home_km": 45.0,
                "is_foreign": False,
                "is_high_risk_merchant": True,
                "device_trust_score": 0.35,
                "hour_of_day": 1,
                "notes": "Multiple rapid-fire transfers to crypto merchant"
            }
        }
    ]
