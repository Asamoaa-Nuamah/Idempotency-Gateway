# FinSafe Idempotency Gateway

A simple payment API that guarantees each request is processed only once by using an `Idempotency-Key` header.

## Project Summary
This service implements a payment processing gateway with first-class idempotency support.
It accepts payment requests with a unique `Idempotency-Key`, persists the request and response to SQLite, and ensures duplicate retries return the same saved result instead of re-processing the payment.

The service also handles concurrent duplicate requests by tracking in-flight processing and waiting for the first request to finish before returning the replayed response.

## Project Structure
- `main.py`: FastAPI application and route definitions.
- `models.py`: Request schema for payment validation.
- `database.py`: SQLite persistence for idempotency records.
- `services.py`: Business logic for idempotency enforcement and in-flight request coordination.

## Setup and Run
1. Clone the repository and change directory:
   ```bash
   git clone <your-repo-url>
   cd Idempotency-Gateway
   ```

2. Create and activate a Python virtual environment:
   ```bash
   python3 -m venv .venv
   source .venv/bin/activate
   ```

3. Install dependencies:
   ```bash
   pip install -r requirements.txt
   ```

4. Start the application:
   ```bash
   uvicorn main:app --reload
   ```

5. Verify the service is running:
   ```bash
   curl http://127.0.0.1:8000/health
   ```

## API Endpoints

### GET /health
Returns the service health status.

Response:
```json
{
  "message": "FinSafe Payment API is running"
}
```

### POST /process-payment
Processes a payment request and enforces idempotency.

Request headers:
- `Idempotency-Key`: unique key to identify the logical transaction.

Request body:
```json
{
  "amount": 100,
  "currency": "GHS"
}
```

Successful response on first request:
- Status: `201 Created`
- Body:
```json
{
  "message": "Charged 100 GHS"
}
```
- Header: `X-Cache-Hit: false`

Duplicate request with the same key and payload:
- Status: `201 Created`
- Body:
```json
{
  "message": "Charged 100 GHS"
}
```
- Header: `X-Cache-Hit: true`

Error cases:
- Missing `Idempotency-Key` header:
  - `400 Bad Request`
  - `{ "detail": "Idempotency-Key header is required" }`
- Same key with different payload:
  - `409 Conflict`
  - `{ "detail": "Idempotency key already used for a different request body." }`

### Example curl request
```bash
curl -X POST http://127.0.0.1:8000/process-payment \
  -H "Content-Type: application/json" \
  -H "Idempotency-Key: abc123" \
  -d '{"amount": 100, "currency": "GHS"}'
```

## Design Decisions

### Durable persistence
Instead of keeping idempotency state only in memory, this service persists records in SQLite.
That means the idempotency history survives server restarts and avoids duplicate processing after a crash or redeploy.

### Clear module separation
The application logic is separated into:
- `main.py` for API routing
- `models.py` for request validation
- `database.py` for storage and retrieval
- `services.py` for idempotency behavior and response replay

### Concurrent duplicate handling
The service uses an in-memory `in_flight_requests` map and `threading.Event` to coordinate simultaneous requests with the same key.
If a second identical request arrives while the first is still processing, it waits and receives the same saved response.

## Developer's Choice Feature
Implemented SQLite-backed idempotency storage.

Why it matters:
- Real payment systems must preserve idempotency across restarts and deployments.
- In-memory state alone is not enough for reliability in production.

## Notes
- The database file `idempotency_store.db` is created automatically.
- This project is a simulation and can be extended to use Redis, PostgreSQL, or distributed locking in a production environment.
