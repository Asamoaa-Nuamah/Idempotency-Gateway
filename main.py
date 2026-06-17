# Stores previously processed requests
# Key   = Idempotency-Key
# Value = Saved response information

from threading import Event

# Stores completed requests
processed_requests = {}

# Stores requests currently being processed
in_flight_requests = {}

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
    
    # Convert incoming request into a dictionary
    current_request = payment.model_dump()

    if idempotency_key in processed_requests:

       saved_data = processed_requests[idempotency_key]

    # Compare current request with original request
       if current_request != saved_data["request"]:

          raise HTTPException(
            status_code=409,
            detail="Idempotency key already used for a different request body."
        )
       

    # Request matches original request
       return JSONResponse(
        status_code=saved_data["status_code"],
        content=saved_data["body"],
        headers={
            "X-Cache-Hit": "true"
        }
    )

#Bonus story
# Another request with this key is currently processing
    if idempotency_key in in_flight_requests:

        event = in_flight_requests[idempotency_key]

        # Wait until first request finishes
        event.wait()

        saved_data = processed_requests[idempotency_key]

        return JSONResponse(
            status_code=saved_data["status_code"],
            content=saved_data["body"],
            headers={
                "X-Cache-Hit": "true"
            }
        )

    # MARK REQUEST AS IN PROGRESS
    event = Event()
    in_flight_requests[idempotency_key] = event


    # Simulate payment processing
    time.sleep(2)

    # Create response
    response_body = {
        "message": f"Charged {payment.amount} {payment.currency}"
    }

    processed_requests[idempotency_key] = {
    "request": current_request,
    "status_code": 201,
    "body": response_body
}

    # Notify waiting requests that processing is complete
    event.set()

    # Remove from active processing list
    del in_flight_requests[idempotency_key]
    
    # First request should indicate it was not cached
    return JSONResponse(
        status_code=201,
        content=response_body,
        headers={
            "X-Cache-Hit": "false"
        }
    )

