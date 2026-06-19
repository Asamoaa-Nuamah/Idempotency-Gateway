from pydantic import BaseModel


class PaymentRequest(BaseModel):
    """Pydantic model for validating incoming payment data."""

    amount: float
    currency: str
