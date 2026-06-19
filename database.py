import json
import sqlite3
from datetime import datetime

# SQLite file path for durable idempotency storage.
DB_FILE = "idempotency_store.db"


def init_db():
    """Initialize the SQLite database and create the table if needed."""
    connection = sqlite3.connect(DB_FILE, check_same_thread=False)
    connection.row_factory = sqlite3.Row
    cursor = connection.cursor()
    cursor.execute(
        """
        CREATE TABLE IF NOT EXISTS idempotency_records (
            idempotency_key TEXT PRIMARY KEY,
            request_body TEXT NOT NULL,
            status_code INTEGER NOT NULL,
            response_body TEXT NOT NULL,
            created_at TEXT NOT NULL
        )
        """
    )
    connection.commit()
    return connection


# Open a long-lived database connection for the service.
db = init_db()


def get_saved_record(idempotency_key: str):
    """Return a stored idempotency record by key, or None if missing."""
    cursor = db.cursor()
    cursor.execute(
        "SELECT request_body, status_code, response_body FROM idempotency_records WHERE idempotency_key = ?",
        (idempotency_key,),
    )
    row = cursor.fetchone()
    if not row:
        return None

    return {
        "request": json.loads(row["request_body"]),
        "status_code": row["status_code"],
        "body": json.loads(row["response_body"]),
    }


def save_record(idempotency_key: str, request: dict, status_code: int, body: dict):
    """Persist an idempotency record for later replay of the same request."""
    cursor = db.cursor()
    cursor.execute(
        "INSERT OR REPLACE INTO idempotency_records (idempotency_key, request_body, status_code, response_body, created_at) VALUES (?, ?, ?, ?, ?)",
        (
            idempotency_key,
            json.dumps(request),
            status_code,
            json.dumps(body),
            datetime.utcnow().isoformat() + "Z",
        ),
    )
    db.commit()
