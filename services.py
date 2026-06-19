import time
from threading import Event

from fastapi import HTTPException
from fastapi.responses import JSONResponse

from database import get_saved_record, save_record
from models import PaymentRequest

# Tracks requests that are currently being processed.
# This avoids race conditions when the same idempotency key arrives simultaneously.
in_flight_requests = {}


def process_payment_request(payment: PaymentRequest, idempotency_key: str):
    """Handle an incoming payment request with idempotency enforcement."""
    if not idempotency_key:
        raise HTTPException(
            status_code=400,
            detail="Idempotency-Key header is required",
        )

    # Convert validated Pydantic model to raw dict for comparision/storage.
    current_request = payment.model_dump()

    # Check whether this key was already processed.
    saved_data = get_saved_record(idempotency_key)
    if saved_data:
        # Reject if the same key is re-used for a different request payload.
        if current_request != saved_data["request"]:
            raise HTTPException(
                status_code=409,
                detail="Idempotency key already used for a different request body.",
            )

        # Replay the saved response instead of processing again.
        return JSONResponse(
            status_code=saved_data["status_code"],
            content=saved_data["body"],
            headers={"X-Cache-Hit": "true"},
        )

    # If a request with the same key is currently being handled,
    # wait for the first one to complete and then return its result.
    if idempotency_key in in_flight_requests:
        event = in_flight_requests[idempotency_key]
        event.wait()

        saved_data = get_saved_record(idempotency_key)
        if not saved_data:
            raise HTTPException(
                status_code=500,
                detail="Idempotency record was not found after processing.",
            )

        return JSONResponse(
            status_code=saved_data["status_code"],
            content=saved_data["body"],
            headers={"X-Cache-Hit": "true"},
        )

    # Otherwise, reserve the key while this request is processing.
    event = Event()
    in_flight_requests[idempotency_key] = event

    # Simulate the external payment processing delay.
    time.sleep(2)
    response_body = {
        "message": f"Charged {payment.amount} {payment.currency}"
    }

    # Persist the successful response so duplicate requests can be replayed.
    save_record(idempotency_key, current_request, 201, response_body)

    # Notify any waiters that processing has finished.
    event.set()
    del in_flight_requests[idempotency_key]

    return JSONResponse(
        status_code=201,
        content=response_body,
        headers={"X-Cache-Hit": "false"},
    )
