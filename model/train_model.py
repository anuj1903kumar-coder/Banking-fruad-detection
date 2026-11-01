"""
Model Training Script for Banking Fraud Detection System
Trains a production-grade XGBoost classifier on banking transaction data
with realistic fraud patterns (balance draining, velocity spikes, geo-anomalies).
Saves model natively as JSON (portable, zero pickle dependencies).
"""

import os
import json
from datetime import datetime
import numpy as np
import pandas as pd
import xgboost as xgb
from sklearn.model_selection import train_test_split
from sklearn.metrics import classification_report, roc_auc_score, f1_score, precision_score, recall_score

# Output directories and files
MODEL_DIR = os.path.dirname(os.path.abspath(__file__))
MODEL_JSON_FILE = os.path.join(MODEL_DIR, "fraud_model.json")
MODEL_META_FILE = os.path.join(MODEL_DIR, "model_meta.json")

FEATURE_COLUMNS = [
    "amount",
    "old_balance_orig",
    "new_balance_orig",
    "old_balance_dest",
    "new_balance_dest",
    "balance_error_orig",      # amount - (old_balance_orig - new_balance_orig)
    "balance_error_dest",      # (new_balance_dest - old_balance_dest) - amount
    "is_transfer",
    "is_cash_out",
    "is_payment",
    "is_debit",
    "is_cash_in",
    "velocity_1h",
    "distance_from_home_km",
    "is_foreign",
    "is_high_risk_merchant",
    "device_trust_score",
    "hour_of_day"
]


def generate_synthetic_banking_data(n_samples=25000, random_state=42):
    """
    Generate realistic synthetic banking transactions with both genuine
    and fraudulent transaction patterns based on PaySim / financial benchmark distributions.
    """
    np.random.seed(random_state)

    # 1. Transaction Types
    types = np.random.choice(
        ["PAYMENT", "TRANSFER", "CASH_OUT", "DEBIT", "CASH_IN"],
        size=n_samples,
        p=[0.40, 0.20, 0.20, 0.10, 0.10]
    )

    # 2. Amounts & Balances
    amounts = np.random.lognormal(mean=4.2, sigma=1.3, size=n_samples)
    amounts = np.round(np.clip(amounts, 1.0, 500000.0), 2)

    old_balance_orig = np.random.exponential(scale=15000.0, size=n_samples)
    old_balance_orig = np.round(old_balance_orig, 2)

    new_balance_orig = np.maximum(0.0, old_balance_orig - amounts)
    old_balance_dest = np.random.exponential(scale=25000.0, size=n_samples)
    old_balance_dest = np.round(old_balance_dest, 2)
    new_balance_dest = old_balance_dest + amounts

    # Behavior features
    velocity_1h = np.random.poisson(lam=1.2, size=n_samples)
    distance_from_home_km = np.random.exponential(scale=12.0, size=n_samples)
    is_foreign = (np.random.rand(n_samples) < 0.05).astype(int)
    is_high_risk_merchant = (np.random.rand(n_samples) < 0.04).astype(int)
    device_trust_score = np.random.beta(a=8, b=2, size=n_samples)  # Mostly high trust (0.8-1.0)
    hour_of_day = np.random.randint(0, 24, size=n_samples)

    # Labels: 0 = Genuine, 1 = Fraud
    labels = np.zeros(n_samples, dtype=int)

    # Inject realistic fraud patterns (~8.5% of dataset)
    n_fraud = int(n_samples * 0.085)
    fraud_indices = np.random.choice(n_samples, size=n_fraud, replace=False)

    for idx in fraud_indices:
        labels[idx] = 1
        fraud_scenario = np.random.choice([
            "drain_balance", "huge_transfer", "velocity_burst", "foreign_cashout", "night_anomaly"
        ])

        if fraud_scenario == "drain_balance":
            # Draining the entire sender balance to 0 in TRANSFER or CASH_OUT
            types[idx] = np.random.choice(["TRANSFER", "CASH_OUT"])
            old_balance_orig[idx] = np.random.uniform(5000.0, 95000.0)
            amounts[idx] = old_balance_orig[idx]
            new_balance_orig[idx] = 0.0
            new_balance_dest[idx] = 0.0  # Money moved out immediately
            device_trust_score[idx] = np.random.uniform(0.05, 0.35)
            velocity_1h[idx] = np.random.randint(2, 6)

        elif fraud_scenario == "huge_transfer":
            # Massive single transfer to new unknown recipient / high risk merchant
            types[idx] = "TRANSFER"
            amounts[idx] = np.random.uniform(25000.0, 350000.0)
            old_balance_orig[idx] = amounts[idx] + np.random.uniform(100.0, 5000.0)
            new_balance_orig[idx] = old_balance_orig[idx] - amounts[idx]
            old_balance_dest[idx] = 0.0
            new_balance_dest[idx] = 0.0
            is_high_risk_merchant[idx] = 1
            distance_from_home_km[idx] = np.random.uniform(150.0, 2500.0)

        elif fraud_scenario == "velocity_burst":
            # Rapid fire transactions within an hour
            types[idx] = np.random.choice(["TRANSFER", "CASH_OUT", "PAYMENT"])
            velocity_1h[idx] = np.random.randint(6, 20)
            amounts[idx] = np.random.uniform(800.0, 4500.0)
            device_trust_score[idx] = np.random.uniform(0.1, 0.4)
            hour_of_day[idx] = np.random.choice([1, 2, 3, 4, 23])

        elif fraud_scenario == "foreign_cashout":
            # Cash out from distant country
            types[idx] = "CASH_OUT"
            is_foreign[idx] = 1
            distance_from_home_km[idx] = np.random.uniform(1000.0, 8000.0)
            amounts[idx] = np.random.uniform(3000.0, 30000.0)
            device_trust_score[idx] = np.random.uniform(0.0, 0.25)
            hour_of_day[idx] = np.random.choice([0, 1, 2, 3, 4])

        elif fraud_scenario == "night_anomaly":
            # Off-hours transfer to suspicious account
            types[idx] = "TRANSFER"
            amounts[idx] = np.random.uniform(15000.0, 80000.0)
            hour_of_day[idx] = np.random.choice([2, 3, 4])
            is_high_risk_merchant[idx] = 1
            device_trust_score[idx] = np.random.uniform(0.15, 0.45)

    df = pd.DataFrame({
        "type": types,
        "amount": amounts,
        "old_balance_orig": old_balance_orig,
        "new_balance_orig": new_balance_orig,
        "old_balance_dest": old_balance_dest,
        "new_balance_dest": new_balance_dest,
        "velocity_1h": velocity_1h,
        "distance_from_home_km": distance_from_home_km,
        "is_foreign": is_foreign,
        "is_high_risk_merchant": is_high_risk_merchant,
        "device_trust_score": device_trust_score,
        "hour_of_day": hour_of_day,
        "is_fraud": labels
    })

    return df


def engineer_features(df: pd.DataFrame) -> pd.DataFrame:
    """Compute derived indicators and binary flags for transaction types."""
    X = pd.DataFrame()
    X["amount"] = df["amount"].astype(float)
    X["old_balance_orig"] = df["old_balance_orig"].astype(float)
    X["new_balance_orig"] = df["new_balance_orig"].astype(float)
    X["old_balance_dest"] = df["old_balance_dest"].astype(float)
    X["new_balance_dest"] = df["new_balance_dest"].astype(float)

    # Balance discrepancy checks
    X["balance_error_orig"] = (df["amount"] - (df["old_balance_orig"] - df["new_balance_orig"])).astype(float)
    X["balance_error_dest"] = ((df["new_balance_dest"] - df["old_balance_dest"]) - df["amount"]).astype(float)

    # Transaction types
    X["is_transfer"] = (df["type"] == "TRANSFER").astype(int)
    X["is_cash_out"] = (df["type"] == "CASH_OUT").astype(int)
    X["is_payment"] = (df["type"] == "PAYMENT").astype(int)
    X["is_debit"] = (df["type"] == "DEBIT").astype(int)
    X["is_cash_in"] = (df["type"] == "CASH_IN").astype(int)

    X["velocity_1h"] = df["velocity_1h"].astype(int)
    X["distance_from_home_km"] = df["distance_from_home_km"].astype(float)
    X["is_foreign"] = df["is_foreign"].astype(int)
    X["is_high_risk_merchant"] = df["is_high_risk_merchant"].astype(int)
    X["device_trust_score"] = df["device_trust_score"].astype(float)
    X["hour_of_day"] = df["hour_of_day"].astype(int)

    return X[FEATURE_COLUMNS]


def train_and_save_model(n_samples=30000):
    print("=" * 60)
    print("  TRAINING XGBOOST BANKING FRAUD DETECTION MODEL")
    print("=" * 60)
    print(f"-> Generating synthetic banking fraud dataset ({n_samples:,} records)...", flush=True)
    df = generate_synthetic_banking_data(n_samples=n_samples)
    fraud_rate = df["is_fraud"].mean()
    print(f"Dataset generated. Genuine: {(df['is_fraud']==0).sum():,}, Fraud: {(df['is_fraud']==1).sum():,} ({fraud_rate:.2%})", flush=True)

    X = engineer_features(df)
    y = df["is_fraud"].values

    X_train, X_test, y_train, y_test = train_test_split(
        X, y, test_size=0.2, random_state=42, stratify=y
    )

    # Weight positive class to handle class imbalance
    scale_pos_weight = float((len(y_train) - sum(y_train)) / sum(y_train))

    print(f"-> Training XGBoost Classifier (scale_pos_weight={scale_pos_weight:.2f})...", flush=True)
    clf = xgb.XGBClassifier(
        n_estimators=120,
        max_depth=6,
        learning_rate=0.08,
        subsample=0.85,
        colsample_bytree=0.85,
        scale_pos_weight=scale_pos_weight,
        eval_metric="logloss",
        random_state=42,
        n_jobs=1
    )
    clf.fit(X_train, y_train)

    # Evaluation
    y_pred = clf.predict(X_test)
    y_prob = clf.predict_proba(X_test)[:, 1]

    auc = float(roc_auc_score(y_test, y_prob))
    prec = float(precision_score(y_test, y_pred))
    rec = float(recall_score(y_test, y_pred))
    f1 = float(f1_score(y_test, y_pred))

    print("\n--- Model Evaluation Results ---", flush=True)
    print(f"  ROC-AUC Score : {auc:.4f}")
    print(f"  Precision     : {prec:.4f}")
    print(f"  Recall        : {rec:.4f}")
    print(f"  F1 Score      : {f1:.4f}")
    print("\nDetailed Classification Report:")
    print(classification_report(y_test, y_pred, target_names=["Genuine", "Fraud"]))

    # Feature Importance
    importances = clf.feature_importances_
    feat_imp = sorted(zip(FEATURE_COLUMNS, importances), key=lambda x: x[1], reverse=True)
    print("\nTop 8 Most Predictive Features:")
    for feat, imp in feat_imp[:8]:
        print(f"  {feat:<24} : {imp*100:5.2f}%")

    # Save Model to Native JSON
    os.makedirs(MODEL_DIR, exist_ok=True)
    clf.save_model(MODEL_JSON_FILE)
    print(f"\n-> XGBoost model saved to: {MODEL_JSON_FILE}", flush=True)

    # Save Metadata & Feature Specs to JSON
    metadata = {
        "model_type": "XGBoost",
        "version": "2.0.0",
        "trained_at": datetime.utcnow().isoformat() + "Z",
        "dataset_size": n_samples,
        "feature_columns": FEATURE_COLUMNS,
        "metrics": {
            "roc_auc": round(auc, 4),
            "precision": round(prec, 4),
            "recall": round(rec, 4),
            "f1_score": round(f1, 4)
        },
        "feature_importance": {feat: round(float(imp), 4) for feat, imp in feat_imp}
    }

    with open(MODEL_META_FILE, "w", encoding="utf-8") as f:
        json.dump(metadata, f, indent=2)

    print(f"-> Model metadata saved to: {MODEL_META_FILE}", flush=True)
    print("=" * 60)
    print("  MODEL TRAINING COMPLETED SUCCESSFULLY!")
    print("=" * 60)


if __name__ == "__main__":
    train_and_save_model()
