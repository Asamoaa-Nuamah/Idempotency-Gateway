# Stores previously processed requests
# Key   = Idempotency-Key
# Value = Saved response information
processed_requests = {}

# Import FastAPI framework
from fastapi import FastAPI, Header, HTTPException
from fastapi.responses import JSONResponse

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
    idempotency_key: str = Header(
        None,
        alias="Idempotency-Key"
    )
):
    """
    Process payment exactly once.

    If the same Idempotency-Key is received again,
    return the previously saved response instead
    of processing the payment a second time.
    """

    # Ensure header exists
    if not idempotency_key:
        raise HTTPException(
            status_code=400,
            detail="Idempotency-Key header is required"
        )

    # Check whether this request was processed before
    if idempotency_key in processed_requests:

        saved_data = processed_requests[idempotency_key]

        # Return cached response immediately
        return JSONResponse(
            status_code=saved_data["status_code"],
            content=saved_data["body"],
            headers={
                "X-Cache-Hit": "true"
            }
        )

    # Simulate payment processing
    time.sleep(2)

    # Create response
    response_body = {
        "message": f"Charged {payment.amount} {payment.currency}"
    }

    # Save response for future duplicate requests
    processed_requests[idempotency_key] = {
        "status_code": 201,
        "body": response_body
    }

    # First request should indicate it was not cached
    return JSONResponse(
        status_code=201,
        content=response_body,
        headers={
            "X-Cache-Hit": "false"
        }
    )

