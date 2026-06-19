import time
from threading import Event

from fastapi import HTTPException
from fastapi.responses import JSONResponse

from database import get_saved_record, save_record
from models import PaymentRequest

in_flight_requests = {}


def process_payment_request(payment: PaymentRequest, idempotency_key: str):
    if not idempotency_key:
        raise HTTPException(
            status_code=400,
            detail="Idempotency-Key header is required",
        )

    current_request = payment.model_dump()
    saved_data = get_saved_record(idempotency_key)
    if saved_data:
        if current_request != saved_data["request"]:
            raise HTTPException(
                status_code=409,
                detail="Idempotency key already used for a different request body.",
            )

        return JSONResponse(
            status_code=saved_data["status_code"],
            content=saved_data["body"],
            headers={"X-Cache-Hit": "true"},
        )

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

    event = Event()
    in_flight_requests[idempotency_key] = event

    time.sleep(2)
    response_body = {
        "message": f"Charged {payment.amount} {payment.currency}"
    }

    save_record(idempotency_key, current_request, 201, response_body)

    event.set()
    del in_flight_requests[idempotency_key]

    return JSONResponse(
        status_code=201,
        content=response_body,
        headers={"X-Cache-Hit": "false"},
    )
