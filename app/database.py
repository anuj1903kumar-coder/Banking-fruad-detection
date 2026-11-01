import sqlite3
import json
import os
import io
import csv
from datetime import datetime, timezone
from typing import List, Dict, Any, Optional

DB_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "fraud_detection.db")


def get_db_connection():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def init_db():
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS transactions (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            transaction_id TEXT UNIQUE NOT NULL,
            account_id TEXT NOT NULL,
            recipient_id TEXT NOT NULL,
            transaction_type TEXT NOT NULL,
            amount REAL NOT NULL,
            old_balance_orig REAL,
            new_balance_orig REAL,
            old_balance_dest REAL,
            new_balance_dest REAL,
            velocity_1h INTEGER,
            distance_from_home_km REAL,
            is_foreign INTEGER,
            is_high_risk_merchant INTEGER,
            device_trust_score REAL,
            verdict TEXT NOT NULL,
            is_fraud INTEGER NOT NULL,
            risk_score REAL NOT NULL,
            risk_level TEXT NOT NULL,
            action TEXT NOT NULL,
            reasons TEXT,
            timestamp TEXT NOT NULL
        )
    """)
    conn.commit()
    conn.close()


def save_transaction(data: Dict[str, Any]):
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("""
        INSERT OR REPLACE INTO transactions (
            transaction_id, account_id, recipient_id, transaction_type, amount,
            old_balance_orig, new_balance_orig, old_balance_dest, new_balance_dest,
            velocity_1h, distance_from_home_km, is_foreign, is_high_risk_merchant,
            device_trust_score, verdict, is_fraud, risk_score, risk_level, action,
            reasons, timestamp
        ) VALUES (
            ?, ?, ?, ?, ?,
            ?, ?, ?, ?,
            ?, ?, ?, ?,
            ?, ?, ?, ?, ?, ?,
            ?, ?
        )
    """, (
        data["transaction_id"],
        data["account_id"],
        data["recipient_id"],
        data["transaction_type"],
        float(data["amount"]),
        float(data.get("old_balance_orig", 0.0)),
        float(data.get("new_balance_orig", 0.0)),
        float(data.get("old_balance_dest", 0.0)),
        float(data.get("new_balance_dest", 0.0)),
        int(data.get("velocity_1h", 1)),
        float(data.get("distance_from_home_km", 0.0)),
        1 if data.get("is_foreign") else 0,
        1 if data.get("is_high_risk_merchant") else 0,
        float(data.get("device_trust_score", 1.0)),
        data["verdict"],
        1 if data["is_fraud"] else 0,
        float(data["risk_score"]),
        data["risk_level"],
        data["action"],
        json.dumps(data.get("reasons", [])),
        data.get("timestamp", datetime.now(timezone.utc).isoformat())
    ))
    conn.commit()
    conn.close()


def save_transactions_batch(transactions_list: List[Dict[str, Any]]):
    """Bulk inserts a list of transactions efficiently."""
    if not transactions_list:
        return

    conn = get_db_connection()
    cursor = conn.cursor()

    rows = []
    for data in transactions_list:
        rows.append((
            data["transaction_id"],
            data["account_id"],
            data["recipient_id"],
            data["transaction_type"],
            float(data["amount"]),
            float(data.get("old_balance_orig", 0.0)),
            float(data.get("new_balance_orig", 0.0)),
            float(data.get("old_balance_dest", 0.0)),
            float(data.get("new_balance_dest", 0.0)),
            int(data.get("velocity_1h", 1)),
            float(data.get("distance_from_home_km", 0.0)),
            1 if data.get("is_foreign") else 0,
            1 if data.get("is_high_risk_merchant") else 0,
            float(data.get("device_trust_score", 1.0)),
            data["verdict"],
            1 if data["is_fraud"] else 0,
            float(data["risk_score"]),
            data["risk_level"],
            data["action"],
            json.dumps(data.get("reasons", [])),
            data.get("timestamp", datetime.now(timezone.utc).isoformat())
        ))

    cursor.executemany("""
        INSERT OR REPLACE INTO transactions (
            transaction_id, account_id, recipient_id, transaction_type, amount,
            old_balance_orig, new_balance_orig, old_balance_dest, new_balance_dest,
            velocity_1h, distance_from_home_km, is_foreign, is_high_risk_merchant,
            device_trust_score, verdict, is_fraud, risk_score, risk_level, action,
            reasons, timestamp
        ) VALUES (
            ?, ?, ?, ?, ?,
            ?, ?, ?, ?,
            ?, ?, ?, ?,
            ?, ?, ?, ?, ?, ?,
            ?, ?
        )
    """, rows)
    conn.commit()
    conn.close()


def get_transactions(limit: int = 50, filter_verdict: Optional[str] = None) -> List[Dict[str, Any]]:
    conn = get_db_connection()
    cursor = conn.cursor()
    
    if filter_verdict and filter_verdict.upper() in ["FRAUD", "GENUINE"]:
        cursor.execute(
            "SELECT * FROM transactions WHERE verdict = ? ORDER BY id DESC LIMIT ?",
            (filter_verdict.upper(), limit)
        )
    else:
        cursor.execute("SELECT * FROM transactions ORDER BY id DESC LIMIT ?", (limit,))
        
    rows = cursor.fetchall()
    result = []
    for r in rows:
        item = dict(r)
        item["is_fraud"] = bool(item["is_fraud"])
        item["is_foreign"] = bool(item["is_foreign"])
        item["is_high_risk_merchant"] = bool(item["is_high_risk_merchant"])
        try:
            item["reasons"] = json.loads(item["reasons"]) if item["reasons"] else []
        except Exception:
            item["reasons"] = []
        result.append(item)
    conn.close()
    return result


def get_stats() -> Dict[str, Any]:
    conn = get_db_connection()
    cursor = conn.cursor()
    
    cursor.execute("SELECT COUNT(*) FROM transactions")
    total = cursor.fetchone()[0] or 0
    
    cursor.execute("SELECT COUNT(*) FROM transactions WHERE verdict = 'FRAUD'")
    fraud_count = cursor.fetchone()[0] or 0
    
    cursor.execute("SELECT COUNT(*) FROM transactions WHERE verdict = 'GENUINE'")
    genuine_count = cursor.fetchone()[0] or 0
    
    cursor.execute("SELECT SUM(amount) FROM transactions")
    total_amount = cursor.fetchone()[0] or 0.0
    
    cursor.execute("SELECT SUM(amount) FROM transactions WHERE verdict = 'FRAUD'")
    fraud_prevented = cursor.fetchone()[0] or 0.0
    
    conn.close()
    
    rate = round((fraud_count / total * 100), 2) if total > 0 else 0.0
    
    return {
        "total_transactions": total,
        "fraud_count": fraud_count,
        "genuine_count": genuine_count,
        "fraud_rate_percentage": rate,
        "total_amount_processed": round(total_amount, 2),
        "total_fraud_amount_prevented": round(fraud_prevented, 2)
    }


def clear_transactions() -> int:
    """Clears all audit trail records from the database. Returns count of deleted rows."""
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT COUNT(*) FROM transactions")
    count = cursor.fetchone()[0] or 0
    cursor.execute("DELETE FROM transactions")
    conn.commit()
    conn.close()
    return count


def export_transactions_as_csv() -> str:
    """Exports all stored transactions to a CSV string."""
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM transactions ORDER BY id DESC")
    rows = cursor.fetchall()

    output = io.StringIO()
    if rows:
        headers = list(rows[0].keys())
        writer = csv.DictWriter(output, fieldnames=headers)
        writer.writeheader()
        for r in rows:
            d = dict(r)
            writer.writerow(d)
    else:
        output.write("transaction_id,account_id,recipient_id,amount,verdict,is_fraud,risk_score,action,timestamp\n")

    conn.close()
    return output.getvalue()


def get_detailed_analytics() -> Dict[str, Any]:
    """Retrieves aggregated metrics for analytics and visualizations."""
    conn = get_db_connection()
    cursor = conn.cursor()

    # 1. Type Breakdown
    cursor.execute("""
        SELECT transaction_type, 
               COUNT(*) as total,
               SUM(CASE WHEN verdict = 'FRAUD' THEN 1 ELSE 0 END) as fraud_count,
               SUM(amount) as total_amount,
               SUM(CASE WHEN verdict = 'FRAUD' THEN amount ELSE 0 END) as fraud_amount
        FROM transactions
        GROUP BY transaction_type
    """)
    type_rows = cursor.fetchall()
    by_type = []
    for r in type_rows:
        by_type.append({
            "type": r["transaction_type"],
            "total": r["total"],
            "fraud_count": r["fraud_count"],
            "genuine_count": r["total"] - r["fraud_count"],
            "fraud_rate": round((r["fraud_count"] / r["total"] * 100), 2) if r["total"] else 0.0,
            "total_amount": round(r["total_amount"] or 0.0, 2),
            "fraud_amount": round(r["fraud_amount"] or 0.0, 2)
        })

    # 2. Risk Level Breakdown
    cursor.execute("""
        SELECT risk_level, COUNT(*) as count
        FROM transactions
        GROUP BY risk_level
    """)
    risk_rows = cursor.fetchall()
    by_risk = {r["risk_level"]: r["count"] for r in risk_rows}

    # 3. Action Breakdown
    cursor.execute("""
        SELECT action, COUNT(*) as count
        FROM transactions
        GROUP BY action
    """)
    action_rows = cursor.fetchall()
    by_action = {r["action"]: r["count"] for r in action_rows}

    # 4. Risk Score Buckets (0-20%, 20-40%, 40-60%, 60-80%, 80-100%)
    cursor.execute("""
        SELECT 
            SUM(CASE WHEN risk_score < 0.20 THEN 1 ELSE 0 END) as b_0_20,
            SUM(CASE WHEN risk_score >= 0.20 AND risk_score < 0.40 THEN 1 ELSE 0 END) as b_20_40,
            SUM(CASE WHEN risk_score >= 0.40 AND risk_score < 0.60 THEN 1 ELSE 0 END) as b_40_60,
            SUM(CASE WHEN risk_score >= 0.60 AND risk_score < 0.80 THEN 1 ELSE 0 END) as b_60_80,
            SUM(CASE WHEN risk_score >= 0.80 THEN 1 ELSE 0 END) as b_80_100
        FROM transactions
    """)
    bucket_row = cursor.fetchone()
    risk_buckets = {
        "0-20%": bucket_row["b_0_20"] or 0,
        "20-40%": bucket_row["b_20_40"] or 0,
        "40-60%": bucket_row["b_40_60"] or 0,
        "60-80%": bucket_row["b_60_80"] or 0,
        "80-100%": bucket_row["b_80_100"] or 0
    }

    # 5. Top Flagged Accounts
    cursor.execute("""
        SELECT account_id, COUNT(*) as flag_count, SUM(amount) as fraud_amount, MAX(risk_score) as max_risk
        FROM transactions
        WHERE verdict = 'FRAUD'
        GROUP BY account_id
        ORDER BY fraud_amount DESC
        LIMIT 5
    """)
    top_accounts = [dict(r) for r in cursor.fetchall()]

    # 6. Recent timeline for volume/fraud trend
    cursor.execute("""
        SELECT transaction_id, transaction_type, amount, risk_score, verdict, action, timestamp
        FROM transactions
        ORDER BY id DESC
        LIMIT 15
    """)
    recent_trend = [dict(r) for r in cursor.fetchall()]
    recent_trend.reverse()

    conn.close()

    return {
        "by_type": by_type,
        "by_risk_level": by_risk,
        "by_action": by_action,
        "risk_buckets": risk_buckets,
        "top_flagged_accounts": top_accounts,
        "recent_trend": recent_trend
    }


def get_report_summary() -> Dict[str, Any]:
    """Generates an executive fraud investigation & compliance summary."""
    stats = get_stats()
    analytics = get_detailed_analytics()

    conn = get_db_connection()
    cursor = conn.cursor()

    # Get recent critical fraud incidents
    cursor.execute("""
        SELECT transaction_id, account_id, recipient_id, transaction_type, amount, risk_score, action, reasons, timestamp
        FROM transactions
        WHERE verdict = 'FRAUD'
        ORDER BY amount DESC
        LIMIT 5
    """)
    critical_incidents = []
    for r in cursor.fetchall():
        item = dict(r)
        try:
            item["reasons"] = json.loads(item["reasons"]) if item["reasons"] else []
        except Exception:
            item["reasons"] = []
        critical_incidents.append(item)

    conn.close()

    # Determine security posture grade
    fraud_rate = stats.get("fraud_rate_percentage", 0.0)
    if fraud_rate < 5.0:
        health_grade = "OPTIMAL (Tier 1 Protection)"
    elif fraud_rate < 15.0:
        health_grade = "ELEVATED VIGILANCE (Tier 2)"
    else:
        health_grade = "HIGH THREAT ACTIVITY (Tier 3)"

    return {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "stats": stats,
        "health_grade": health_grade,
        "critical_incidents": critical_incidents,
        "by_action": analytics.get("by_action", {}),
        "by_risk_level": analytics.get("by_risk_level", {}),
        "recommendations": [
            "Mandate 2FA biometric verification for all TRANSFER/CASH_OUT events exceeding $10,000.",
            "Quarantine and prompt step-up authentication on devices with trust scores below 0.30.",
            "Enforce automatic temporary hold on accounts draining >90% of their available balance in midnight hours.",
            "Review transaction velocity thresholds for accounts initiating >4 transfers per hour."
        ]
    }


def get_dataset_overview() -> Dict[str, Any]:
    """Returns dataset schema, reference distribution, and sample benchmark records."""
    csv_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "sample_transactions.csv")
    samples = []
    if os.path.exists(csv_path):
        try:
            with open(csv_path, "r", encoding="utf-8") as f:
                reader = csv.DictReader(f)
                for row in reader:
                    samples.append(row)
        except Exception as e:
            print("Failed to read sample csv:", e)

    return {
        "dataset_name": "Banking Transaction Hybrid Benchmark (PaySim & Production Synthesis)",
        "total_records": 30000,
        "features_count": 18,
        "class_distribution": {
            "genuine": 27450,
            "genuine_percentage": 91.5,
            "fraud": 2550,
            "fraud_percentage": 8.5,
            "class_imbalance_ratio": "10.76 : 1"
        },
        "transaction_types_breakdown": {
            "PAYMENT": 40.0,
            "TRANSFER": 20.0,
            "CASH_OUT": 20.0,
            "DEBIT": 10.0,
            "CASH_IN": 10.0
        },
        "features_dictionary": [
            {"name": "transaction_id", "type": "String", "description": "Unique cryptographic identifier of the transaction", "category": "Identifier"},
            {"name": "account_id", "type": "String", "description": "Originating bank account number / wallet ID", "category": "Entity"},
            {"name": "recipient_id", "type": "String", "description": "Destination account or merchant terminal ID", "category": "Entity"},
            {"name": "transaction_type", "type": "Categorical", "description": "Transaction category: TRANSFER, CASH_OUT, PAYMENT, DEBIT, CASH_IN", "category": "Financial"},
            {"name": "amount", "type": "Float ($)", "description": "Transaction currency amount evaluated", "category": "Financial"},
            {"name": "old_balance_orig", "type": "Float ($)", "description": "Initial balance of sender account prior to transaction", "category": "Financial"},
            {"name": "new_balance_orig", "type": "Float ($)", "description": "Remaining balance of sender account post transaction", "category": "Financial"},
            {"name": "old_balance_dest", "type": "Float ($)", "description": "Initial balance of recipient before transaction", "category": "Financial"},
            {"name": "new_balance_dest", "type": "Float ($)", "description": "Balance of recipient after transaction", "category": "Financial"},
            {"name": "balance_error_orig", "type": "Float ($)", "description": "Derived discrepancy: amount - (old_balance_orig - new_balance_orig)", "category": "Derived / Anomaly"},
            {"name": "balance_error_dest", "type": "Float ($)", "description": "Derived discrepancy: (new_balance_dest - old_balance_dest) - amount", "category": "Derived / Anomaly"},
            {"name": "velocity_1h", "type": "Integer", "description": "Frequency count of transactions from this account in past 60 minutes", "category": "Behavioral"},
            {"name": "distance_from_home_km", "type": "Float (km)", "description": "Geographical distance from cardholder registered residential address", "category": "Spatial"},
            {"name": "is_foreign", "type": "Boolean (0/1)", "description": "Flag indicating cross-border or foreign country IP / terminal", "category": "Spatial / Network"},
            {"name": "is_high_risk_merchant", "type": "Boolean (0/1)", "description": "Flag indicating known risky merchant category (Crypto, gambling, offshore)", "category": "Risk Indicator"},
            {"name": "device_trust_score", "type": "Float (0-1)", "description": "Hardware fingerprint reputation score based on device telemetry", "category": "Device Trust"},
            {"name": "hour_of_day", "type": "Integer (0-23)", "description": "Hour of transaction execution (local time)", "category": "Temporal"}
        ],
        "sample_records": samples
    }
