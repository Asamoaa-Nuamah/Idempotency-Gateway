import sqlite3

import pytest
from fastapi.testclient import TestClient

import database
import main
import services
from models import PaymentRequest


@pytest.fixture(autouse=True)
def in_memory_db(monkeypatch):
    connection = sqlite3.connect(":memory:", check_same_thread=False)
    connection.row_factory = sqlite3.Row
    cursor = connection.cursor()
    cursor.execute(
        """
        CREATE TABLE idempotency_records (
            idempotency_key TEXT PRIMARY KEY,
            request_body TEXT NOT NULL,
            status_code INTEGER NOT NULL,
            response_body TEXT NOT NULL,
            created_at TEXT NOT NULL
        )
        """
    )
    connection.commit()

    monkeypatch.setattr(database, "db", connection)
    yield connection
    connection.close()


@pytest.fixture(autouse=True)
def clear_state(monkeypatch):
    services.in_flight_requests.clear()
    monkeypatch.setattr(services.time, "sleep", lambda seconds: None)


@pytest.fixture
def client():
    with TestClient(main.app) as client:
        yield client


def build_payload(amount=100, currency="GHS"):
    return {"amount": amount, "currency": currency}


def log_condition(message: str):
    print(f"PASS: {message}")


def test_health_endpoint(client):
    response = client.get("/health")

    assert response.status_code == 200, "Health endpoint should return status code 200"
    log_condition("Health endpoint returned status code 200")

    assert response.json() == {"message": "FinSafe Payment API is running"}, "Health endpoint returned unexpected JSON body"
    log_condition("Health endpoint returned expected JSON body")


def test_payment_requires_idempotency_key(client):
    response = client.post("/process-payment", json=build_payload())

    assert response.status_code == 400, "Missing Idempotency-Key should return 400"
    log_condition("Payment endpoint returned 400 on missing Idempotency-Key")

    assert response.json()["detail"] == "Idempotency-Key header is required", "Error detail message should describe missing Idempotency-Key"
    log_condition("Payment endpoint returned correct missing Idempotency-Key error detail")


def test_process_payment_creates_new_record_and_returns_cache_miss(client):
    response = client.post(
        "/process-payment",
        json=build_payload(amount=100, currency="GHS"),
        headers={"Idempotency-Key": "test-key-1"},
    )

    assert response.status_code == 201, "First payment request should return 201"
    log_condition("First payment request returned 201")

    assert response.headers["X-Cache-Hit"] == "false", "First payment request should not be a cache hit"
    log_condition("First payment request returned X-Cache-Hit false")

    assert response.json() == {"message": "Charged 100.0 GHS"}, "Response body should confirm the charged amount and currency"
    log_condition("First payment request returned expected response body")


def test_duplicate_request_with_same_payload_replays_cached_response(client):
    key = "same-payload-key"
    payload = build_payload(amount=20.5, currency="USD")

    first_response = client.post(
        "/process-payment",
        json=payload,
        headers={"Idempotency-Key": key},
    )
    second_response = client.post(
        "/process-payment",
        json=payload,
        headers={"Idempotency-Key": key},
    )

    assert first_response.status_code == 201, "Original request should succeed"
    log_condition("Original duplicate-key request succeeded")

    assert second_response.status_code == 201, "Repeated request with same payload should also return 201"
    log_condition("Repeated request with same payload returned 201")

    assert second_response.headers["X-Cache-Hit"] == "true", "Repeated request should be served from cache"
    log_condition("Repeated request returned X-Cache-Hit true")

    assert second_response.json() == first_response.json(), "Repeated request should return the same body as the first request"
    log_condition("Repeated request returned the same response body as first request")


def test_duplicate_request_with_different_payload_returns_conflict(client):
    key = "different-payload-key"

    first_response = client.post(
        "/process-payment",
        json=build_payload(amount=50, currency="EUR"),
        headers={"Idempotency-Key": key},
    )
    assert first_response.status_code == 201, "First request with unique key should succeed"
    log_condition("First request with unique key succeeded")

    response = client.post(
        "/process-payment",
        json=build_payload(amount=75, currency="EUR"),
        headers={"Idempotency-Key": key},
    )

    assert response.status_code == 409, "Reusing an idempotency key with different payload should return 409"
    log_condition("Duplicate key with different payload returned 409")

    assert response.json()["detail"] == "Idempotency key already used for a different request body.", "Error detail should explain conflicting payload"
    log_condition("Duplicate key with different payload returned expected error detail")


def test_persisted_record_matches_request_body():
    payment = PaymentRequest(amount=12.99, currency="GHS")
    result = services.process_payment_request(payment, "persist-key")

    assert result.status_code == 201, "Persisted payment request should return 201"
    log_condition("Persisted payment request returned 201")

    assert result.headers["X-Cache-Hit"] == "false", "First persisted request should not be a cache hit"
    log_condition("Persisted payment request returned X-Cache-Hit false")

    saved = database.get_saved_record("persist-key")
    assert saved is not None, "Saved idempotency record should exist"
    log_condition("Saved idempotency record exists")

    assert saved["request"] == {"amount": 12.99, "currency": "GHS"}, "Stored request payload should match the original request"
    log_condition("Stored request payload matches original")

    assert saved["status_code"] == 201, "Stored status code should be 201"
    log_condition("Stored status code is 201")

    assert saved["body"] == {"message": "Charged 12.99 GHS"}, "Stored response body should match the generated response"
    log_condition("Stored response body matches generated response")
