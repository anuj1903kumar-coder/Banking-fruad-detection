from pydantic import BaseModel, Field
from typing import Optional, List, Dict, Any


class TransactionRequest(BaseModel):
    transaction_id: Optional[str] = Field(default=None, description="Unique transaction ID. If omitted, will be auto-generated.")
    account_id: str = Field(..., description="Sender account number or customer ID", example="ACC-89104")
    recipient_id: str = Field(..., description="Recipient account or merchant ID", example="REC-44120")
    transaction_type: str = Field(..., description="TRANSFER, CASH_OUT, PAYMENT, DEBIT, or CASH_IN", example="TRANSFER")
    amount: float = Field(..., gt=0, description="Transaction amount in currency units", example=14500.0)
    old_balance_orig: float = Field(default=0.0, ge=0, description="Sender balance prior to transaction", example=15000.0)
    new_balance_orig: Optional[float] = Field(default=None, ge=0, description="Sender balance after transaction. If null, computed as max(0, old_balance - amount)")
    old_balance_dest: float = Field(default=0.0, ge=0, description="Recipient balance prior to transaction", example=200.0)
    new_balance_dest: Optional[float] = Field(default=None, ge=0, description="Recipient balance after transaction")
    
    # Behavioral & Contextual features
    velocity_1h: int = Field(default=1, ge=0, description="Transactions conducted by this account in past 1 hour", example=1)
    distance_from_home_km: float = Field(default=5.0, ge=0, description="Distance from customer's usual home / billing location in km", example=12.5)
    is_foreign: bool = Field(default=False, description="Flag if transaction originates from a foreign IP/country")
    is_high_risk_merchant: bool = Field(default=False, description="Flag if recipient/merchant is in a high-risk category (e.g. gambling, crypto)")
    device_trust_score: float = Field(default=0.95, ge=0.0, le=1.0, description="Device trust score between 0.0 (untrusted/spoofed) to 1.0 (verified device)")
    hour_of_day: Optional[int] = Field(default=None, ge=0, le=23, description="Hour of transaction (0-23). Defaults to current hour")
    notes: Optional[str] = Field(default=None, description="Optional description or metadata")


class RiskFactor(BaseModel):
    rule: str
    severity: str  # LOW, MEDIUM, HIGH, CRITICAL
    description: str


class FraudDetectionResponse(BaseModel):
    transaction_id: str
    account_id: str
    recipient_id: str
    amount: float
    transaction_type: str
    
    # Verdict output
    verdict: str  # "FRAUD" or "GENUINE"
    is_fraud: bool
    risk_score: float  # 0.00 to 1.00
    risk_percentage: float  # e.g. 88.5%
    risk_level: str  # "LOW", "MEDIUM", "HIGH", "CRITICAL"
    action: str  # "ALLOW", "CHALLENGE_2FA", "FLAG_REVIEW", "BLOCK"
    
    # Explainability
    confidence: float
    reasons: List[str]
    risk_factors: List[RiskFactor]
    timestamp: str


class BatchTransactionRequest(BaseModel):
    transactions: List[TransactionRequest] = Field(..., description="List of transactions to evaluate")
    threshold: Optional[float] = Field(default=0.50, ge=0.1, le=0.9, description="Custom classification threshold (default: 0.50)")


class BatchTransactionResponse(BaseModel):
    total_evaluated: int
    fraud_detected: int
    genuine_detected: int
    fraud_rate_percentage: float
    total_amount_evaluated: float
    total_fraud_amount_prevented: float
    results: List[FraudDetectionResponse]


class SystemStatsResponse(BaseModel):
    total_transactions: int
    genuine_count: int
    fraud_count: int
    fraud_rate_percentage: float
    total_amount_processed: float
    total_fraud_amount_prevented: float
    recent_transactions: Optional[List[dict]] = None


class ModelInfoResponse(BaseModel):
    model_type: str
    model_loaded: bool
    version: str
    trained_at: str
    dataset_size: int
    metrics: Dict[str, Any]
    feature_importance: Dict[str, float]
