from fastapi import FastAPI, Header

from models import PaymentRequest
from services import process_payment_request

app = FastAPI(
    title="FinSafe Payment API",
    description="Idempotency Layer for Payment Processing",
    version="1.0.0",
)


@app.get("/health", status_code=200)
def health():
    return {"message": "FinSafe Payment API is running"}


@app.post("/process-payment", status_code=201)
def process_payment(
    payment: PaymentRequest,
    idempotency_key: str = Header(
        None,
        alias="Idempotency-Key",
    ),
):
    return process_payment_request(payment, idempotency_key)

