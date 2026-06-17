# Import FastAPI framework
from fastapi import FastAPI, Header, HTTPException

# Used to simulate payment processing delay
import time

# Used for request body validation
from pydantic import BaseModel


# Create FastAPI application instance
app = FastAPI(title="FinSafe Payment API",
    description="Idempotency Layer for Payment Processing",
    version="1.0.0")


# Define the structure of the JSON request body
class PaymentRequest(BaseModel):
    amount: float
    currency: str

#homepage endpoint
@app.get("/")
def home():
    return {
        "message": "FinSafe Payment API is running"
    }


# Create payment endpoint
@app.post("/process-payment", status_code=201)
def process_payment(
    payment: PaymentRequest,
    idempotency_key: str = Header(None)
):
    """
    Process a payment request.

    Parameters:
    - payment: JSON request body
    - idempotency_key: value from request header

    Returns:
    - Payment status message
    """

    # Ensure the header is present
    if not idempotency_key:
        raise HTTPException(
            status_code=400,
            detail="Idempotency-Key header is required"
        )

    # Simulate payment processing
    time.sleep(2)

    # Return success response
    return {
        "message": f"Charged {payment.amount} {payment.currency}"
    }