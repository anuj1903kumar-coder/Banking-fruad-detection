/**
 * Client Example (Node.js): How to connect your project with the Banking Fraud Detection API
 * Run with: node client_example.js
 */

const API_URL = "http://localhost:8000/api/fraud-detection";

async function evaluateTransaction(transaction) {
  try {
    const response = await fetch(API_URL, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(transaction)
    });

    if (!response.ok) {
      throw new Error(`HTTP Error: ${response.status}`);
    }

    return await response.json();
  } catch (error) {
    console.error("Error communicating with Fraud Detection API:", error.message);
    console.error("Make sure the server is running with 'python run.py'");
    return null;
  }
}

function displayVerdict(res) {
  if (!res) return;

  console.log("------------------------------------------------------------");
  console.log(`Transaction ID : ${res.transaction_id}`);
  console.log(`Amount         : $${res.amount.toFixed(2)} (${res.transaction_type})`);
  
  if (res.verdict === "FRAUD" || res.is_fraud) {
    console.log(`VERDICT        : \x1b[31m[FRAUD] - TRANSACTION BLOCKED\x1b[0m`);
  } else {
    console.log(`VERDICT        : \x1b[32m[GENUINE] - TRANSACTION APPROVED\x1b[0m`);
  }

  console.log(`Fraud Risk     : ${res.risk_percentage}% (${res.risk_level} RISK)`);
  console.log(`Action Taken   : ${res.action}`);
  console.log("Reasons        :");
  res.reasons.forEach(r => console.log(`   • ${r}`));
  console.log("------------------------------------------------------------\n");
}

async function main() {
  console.log("\n============================================================");
  console.log("  Node.js Client: Testing Banking Fraud Detection API");
  console.log("============================================================\n");

  // 1. Genuine Payment
  const genuineTxn = {
    account_id: "ACC-USER-1029",
    recipient_id: "MCH-STORE-55",
    transaction_type: "PAYMENT",
    amount: 14.50,
    old_balance_orig: 800.00,
    new_balance_orig: 785.50,
    velocity_1h: 1,
    distance_from_home_km: 3.5,
    is_foreign: false,
    is_high_risk_merchant: false,
    device_trust_score: 0.95
  };

  console.log("Submitting Genuine Transaction...");
  const res1 = await evaluateTransaction(genuineTxn);
  displayVerdict(res1);

  // 2. Fraudulent Transfer
  const fraudTxn = {
    account_id: "ACC-VICTIM-8841",
    recipient_id: "ACC-UNKNOWN-710",
    transaction_type: "TRANSFER",
    amount: 92000.00,
    old_balance_orig: 92000.00,
    new_balance_orig: 0.00,
    velocity_1h: 6,
    distance_from_home_km: 2500.0,
    is_foreign: true,
    is_high_risk_merchant: true,
    device_trust_score: 0.10
  };

  console.log("Submitting Fraudulent Transfer...");
  const res2 = await evaluateTransaction(fraudTxn);
  displayVerdict(res2);
}

main();
