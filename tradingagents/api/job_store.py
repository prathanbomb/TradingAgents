"""SQLite-backed job store for analysis job tracking.

Reuses WAL mode pattern from tradingagents.observability.storage.sqlite_backend.
"""

import json
import sqlite3
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional

from pydantic import BaseModel

# Valid state transitions: current_status -> set of allowed next statuses
VALID_TRANSITIONS: Dict[str, set] = {
    "pending": {"running", "cancelled"},
    "running": {"completed", "failed", "cancelled"},
    "completed": set(),
    "failed": set(),
    "cancelled": set(),
}


class JobRecord(BaseModel):
    job_id: str
    ticker: str
    trade_date: str
    status: str  # pending, running, completed, failed, cancelled
    submitted_at: Optional[str] = None
    started_at: Optional[str] = None
    completed_at: Optional[str] = None
    result: Optional[Dict[str, Any]] = None
    reports: Optional[Dict[str, Any]] = None
    error: Optional[str] = None
    config_snapshot: Optional[Dict[str, Any]] = None
    idempotency_key: Optional[str] = None
    analysts: Optional[List[str]] = None


class JobStore:
    """SQLite-backed store for analysis job records."""

    def __init__(self, db_path: str = "./data/jobs.db"):
        self.db_path = db_path
        self._initialize_db()

    def _get_connection(self) -> sqlite3.Connection:
        Path(self.db_path).parent.mkdir(parents=True, exist_ok=True)
        conn = sqlite3.connect(self.db_path, check_same_thread=False)
        conn.execute("PRAGMA journal_mode=WAL")
        conn.execute("PRAGMA synchronous=NORMAL")
        conn.execute("PRAGMA temp_store=MEMORY")
        conn.execute("PRAGMA cache_size=-10000")
        conn.row_factory = sqlite3.Row
        return conn

    def _initialize_db(self):
        conn = self._get_connection()

        # Drop legacy table if schema doesn't match
        cols = [row[1] for row in conn.execute("PRAGMA table_info(jobs)").fetchall()]
        if cols and "status" not in cols:
            conn.execute("DROP TABLE jobs")
            conn.commit()

        conn.execute("""
            CREATE TABLE IF NOT EXISTS jobs (
                job_id TEXT PRIMARY KEY,
                ticker TEXT NOT NULL,
                trade_date TEXT NOT NULL,
                status TEXT NOT NULL DEFAULT 'pending',
                submitted_at TEXT,
                started_at TEXT,
                completed_at TEXT,
                result TEXT,
                reports TEXT,
                error TEXT,
                config_snapshot TEXT,
                idempotency_key TEXT,
                analysts TEXT
            )
        """)
        conn.execute(
            "CREATE INDEX IF NOT EXISTS idx_jobs_status ON jobs(status)"
        )
        conn.execute(
            "CREATE INDEX IF NOT EXISTS idx_jobs_ticker ON jobs(ticker)"
        )
        conn.execute(
            "CREATE INDEX IF NOT EXISTS idx_jobs_submitted ON jobs(submitted_at DESC)"
        )
        conn.execute(
            "CREATE UNIQUE INDEX IF NOT EXISTS idx_jobs_idempotency ON jobs(idempotency_key)"
            " WHERE idempotency_key IS NOT NULL"
        )
        conn.commit()
        conn.close()

    def _row_to_record(self, row: sqlite3.Row) -> JobRecord:
        d = dict(row)
        for field in ("result", "reports", "config_snapshot"):
            if d.get(field):
                d[field] = json.loads(d[field])
        if d.get("analysts"):
            d["analysts"] = json.loads(d["analysts"])
        return JobRecord(**d)

    def create(
        self,
        job_id: str,
        ticker: str,
        trade_date: str,
        config_snapshot: Optional[Dict] = None,
        idempotency_key: Optional[str] = None,
        analysts: Optional[List[str]] = None,
    ) -> JobRecord:
        now = datetime.now(timezone.utc).isoformat()
        conn = self._get_connection()
        try:
            conn.execute(
                """INSERT INTO jobs
                   (job_id, ticker, trade_date, status, submitted_at, config_snapshot,
                    idempotency_key, analysts)
                   VALUES (?, ?, ?, 'pending', ?, ?, ?, ?)""",
                (
                    job_id,
                    ticker,
                    trade_date,
                    now,
                    json.dumps(config_snapshot) if config_snapshot else None,
                    idempotency_key,
                    json.dumps(analysts) if analysts else None,
                ),
            )
            conn.commit()
            return self.get(job_id)
        finally:
            conn.close()

    def get(self, job_id: str) -> Optional[JobRecord]:
        conn = self._get_connection()
        try:
            row = conn.execute("SELECT * FROM jobs WHERE job_id = ?", (job_id,)).fetchone()
            return self._row_to_record(row) if row else None
        finally:
            conn.close()

    def find_by_idempotency_key(self, key: str) -> Optional[JobRecord]:
        conn = self._get_connection()
        try:
            row = conn.execute(
                "SELECT * FROM jobs WHERE idempotency_key = ?", (key,)
            ).fetchone()
            return self._row_to_record(row) if row else None
        finally:
            conn.close()

    def list_jobs(
        self,
        status: Optional[str] = None,
        ticker: Optional[str] = None,
        trade_date: Optional[str] = None,
        limit: int = 50,
        offset: int = 0,
    ) -> tuple[List[JobRecord], int]:
        conn = self._get_connection()
        try:
            where = "WHERE 1=1"
            params: list = []
            if status:
                where += " AND status = ?"
                params.append(status)
            if ticker:
                where += " AND ticker = ?"
                params.append(ticker)
            if trade_date:
                where += " AND trade_date = ?"
                params.append(trade_date)

            total = conn.execute(
                f"SELECT COUNT(*) FROM jobs {where}", params
            ).fetchone()[0]

            rows = conn.execute(
                f"SELECT * FROM jobs {where} ORDER BY submitted_at DESC LIMIT ? OFFSET ?",
                params + [limit, offset],
            ).fetchall()
            return [self._row_to_record(r) for r in rows], total
        finally:
            conn.close()

    def validate_transition(self, job_id: str, new_status: str) -> Optional[str]:
        """Check if transition is valid. Returns error message or None."""
        job = self.get(job_id)
        if not job:
            return f"Job '{job_id}' not found"
        allowed = VALID_TRANSITIONS.get(job.status, set())
        if new_status not in allowed:
            return f"Cannot transition job '{job_id}' from '{job.status}' to '{new_status}'"
        return None

    def update_status(
        self,
        job_id: str,
        status: str,
        error: Optional[str] = None,
        result: Optional[Dict] = None,
        reports: Optional[Dict] = None,
    ):
        now = datetime.now(timezone.utc).isoformat()
        conn = self._get_connection()
        try:
            sets = ["status = ?"]
            params: list = [status]

            if status == "running":
                sets.append("started_at = ?")
                params.append(now)
            elif status in ("completed", "failed", "cancelled"):
                sets.append("completed_at = ?")
                params.append(now)

            if error is not None:
                sets.append("error = ?")
                params.append(error)
            if result is not None:
                sets.append("result = ?")
                params.append(json.dumps(result))
            if reports is not None:
                sets.append("reports = ?")
                params.append(json.dumps(reports))

            params.append(job_id)
            conn.execute(
                f"UPDATE jobs SET {', '.join(sets)} WHERE job_id = ?", params
            )
            conn.commit()
        finally:
            conn.close()

    def cancel(self, job_id: str) -> bool:
        conn = self._get_connection()
        try:
            row = conn.execute(
                "SELECT status FROM jobs WHERE job_id = ?", (job_id,)
            ).fetchone()
            if not row or row["status"] not in ("pending", "running"):
                return False
            self.update_status(job_id, "cancelled")
            return True
        finally:
            conn.close()

    def delete(self, job_id: str) -> bool:
        conn = self._get_connection()
        try:
            cursor = conn.execute("DELETE FROM jobs WHERE job_id = ?", (job_id,))
            conn.commit()
            return cursor.rowcount > 0
        finally:
            conn.close()

    def mark_stale_running(self, timeout_seconds: int = 3600) -> int:
        """Mark running jobs older than timeout as failed (for startup sweep)."""
        conn = self._get_connection()
        try:
            cutoff = datetime.now(timezone.utc).isoformat()
            cursor = conn.execute(
                """UPDATE jobs SET status = 'failed', error = 'Job timed out (stale running)',
                   completed_at = ?
                   WHERE status = 'running' AND started_at < datetime(?, '-' || ? || ' seconds')""",
                (cutoff, cutoff, timeout_seconds),
            )
            conn.commit()
            return cursor.rowcount
        finally:
            conn.close()
