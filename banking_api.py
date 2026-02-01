# banking_api.py
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel

app = FastAPI(title="Mock Core Banking System")

# =============================================================================
# 1. MOCK DATABASE (The "Mainframe" Data)
# =============================================================================

# banking_api.py (Update the data dictionaries)

CUSTOMERS = {
    "user_123": {
        "name": "Alice Johnson",
        "income": 5000,
        "employment_status": "employed",
        "active_loans": 0,
    },
    "user_456": {
        "name": "Bob Smith",
        "income": 3000,
        "employment_status": "unemployed",
        "active_loans": 1,
    },
    "user_789": {
        "name": "Charlie Medium",
        "income": 4500,
        "employment_status": "self-employed",
        "active_loans": 0,
    },  # <--- NEW USER
}

CREDIT_SCORES = {
    "user_123": 750,  # Excellent
    "user_456": 580,  # Bad
    "user_789": 650,  # Medium (Requires Review) <--- NEW SCORE
}
# =============================================================================
# 2. ENDPOINTS
# =============================================================================


@app.get("/")
def read_root():
    return {"status": "System Online", "service": "Core Banking API"}


@app.get("/customer/{user_id}")
def get_customer_details(user_id: str):
    """Fetch customer KYC details from internal DB."""
    customer = CUSTOMERS.get(user_id)
    if not customer:
        raise HTTPException(status_code=404, detail="Customer not found")
    return customer


@app.get("/credit-score/{user_id}")
def get_credit_score(user_id: str):
    """Fetch credit score from external bureau."""
    score = CREDIT_SCORES.get(user_id)
    if not score:
        raise HTTPException(status_code=404, detail="Score not found")
    return {"user_id": user_id, "credit_score": score}


@app.post("/loan/disburse")
def disburse_loan(user_id: str, amount: float):
    """Simulate writing to Mainframe to deposit funds."""
    if user_id not in CUSTOMERS:
        raise HTTPException(status_code=404, detail="Customer not found")

    # In a real app, this would trigger a CICS transaction
    return {
        "status": "SUCCESS",
        "transaction_id": "TXN_9999",
        "message": f"Disbursed ${amount} to {user_id}",
    }


# To run this: uvicorn banking_api:app --reload --port 8000
