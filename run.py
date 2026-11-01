"""
Banking Fraud Detection System Launcher
Runs FastAPI backend with Uvicorn server.
"""

import uvicorn
import os
import sys

# Ensure workspace root is in path
CURRENT_DIR = os.path.dirname(os.path.abspath(__file__))
if CURRENT_DIR not in sys.path:
    sys.path.insert(0, CURRENT_DIR)

if __name__ == "__main__":
    print("=" * 65)
    print("  BANKING FRAUD DETECTION SYSTEM")
    print("  Machine Learning & Heuristic Rule Engine")
    print("=" * 65)
    print("  -> Web Dashboard : http://localhost:8000/fraud-detection")
    print("  -> REST API Docs  : http://localhost:8000/docs")
    print("  -> Evaluate Route : POST http://localhost:8000/api/fraud-detection")
    print("=" * 65)
    
    uvicorn.run("app.main:app", host="127.0.0.1", port=8000, reload=True)
