import json
import sqlite3
from pathlib import Path
from threading import Lock

from .schemas import DecisionReceipt


class ReceiptStore:
    def __init__(self, path: Path):
        path.parent.mkdir(parents=True, exist_ok=True)
        self.connection = sqlite3.connect(path, check_same_thread=False)
        self.lock = Lock()
        self.connection.execute(
            "CREATE TABLE IF NOT EXISTS receipts (id TEXT PRIMARY KEY, created_at TEXT NOT NULL, payload TEXT NOT NULL)"
        )
        self.connection.execute(
            "CREATE TABLE IF NOT EXISTS window_receipts "
            "(id TEXT PRIMARY KEY, created_at TEXT NOT NULL, payload TEXT NOT NULL)"
        )
        self.connection.execute(
            "CREATE TABLE IF NOT EXISTS v2_receipts "
            "(id TEXT PRIMARY KEY, created_at TEXT NOT NULL, payload TEXT NOT NULL)"
        )
        self.connection.commit()

    def save(self, receipt: DecisionReceipt) -> None:
        with self.lock:
            self.connection.execute(
                "INSERT OR REPLACE INTO receipts VALUES (?, ?, ?)",
                (
                    receipt.receipt_id,
                    receipt.timestamp.isoformat(),
                    json.dumps(receipt.model_dump(mode="json")),
                ),
            )
            self.connection.commit()

    def list_recent(self, limit: int = 50) -> list[dict]:
        with self.lock:
            rows = self.connection.execute(
                "SELECT payload FROM receipts ORDER BY created_at DESC LIMIT ?", (limit,)
            ).fetchall()
        return [json.loads(row[0]) for row in rows]

    def save_window(self, window_id: str, created_at: str, payload: dict) -> None:
        with self.lock:
            self.connection.execute(
                "INSERT OR REPLACE INTO window_receipts VALUES (?, ?, ?)",
                (window_id, created_at, json.dumps(payload)),
            )
            self.connection.commit()

    def update_window_execution(self, window_id: str, execution: dict) -> dict | None:
        with self.lock:
            row = self.connection.execute(
                "SELECT created_at, payload FROM window_receipts WHERE id = ?", (window_id,)
            ).fetchone()
            if row is None:
                return None
            payload = json.loads(row[1])
            payload["execution"] = execution
            self.connection.execute(
                "UPDATE window_receipts SET payload = ? WHERE id = ?",
                (json.dumps(payload), window_id),
            )
            self.connection.commit()
            return payload

    def list_recent_windows(self, limit: int = 50) -> list[dict]:
        with self.lock:
            rows = self.connection.execute(
                "SELECT payload FROM window_receipts ORDER BY created_at DESC LIMIT ?", (limit,)
            ).fetchall()
        return [json.loads(row[0]) for row in rows]

    def save_v2(self, decision_id: str, created_at: str, payload: dict) -> None:
        with self.lock:
            self.connection.execute(
                "INSERT OR REPLACE INTO v2_receipts VALUES (?, ?, ?)",
                (decision_id, created_at, json.dumps(payload)),
            )
            self.connection.commit()

    def list_recent_v2(self, limit: int = 50) -> list[dict]:
        with self.lock:
            rows = self.connection.execute(
                "SELECT payload FROM v2_receipts ORDER BY created_at DESC LIMIT ?", (limit,)
            ).fetchall()
        return [json.loads(row[0]) for row in rows]
