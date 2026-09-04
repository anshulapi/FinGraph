"""Persistent SQLite audit trail for FinGraph pipeline events."""

from __future__ import annotations

import json
import sqlite3
from datetime import datetime
from typing import Any, Dict, List, Optional


class AuditStore:
    """Store and retrieve timestamped FinGraph audit events."""

    def __init__(self, database_path: str = "fingraph_audit.db") -> None:
        self.database_path = database_path
        self._initialize()

    def _connect(self) -> sqlite3.Connection:
        connection = sqlite3.connect(self.database_path)
        connection.row_factory = sqlite3.Row
        return connection

    def _initialize(self) -> None:
        with self._connect() as connection:
            connection.execute(
                """
                CREATE TABLE IF NOT EXISTS audit_events (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    timestamp TEXT NOT NULL,
                    stage TEXT NOT NULL,
                    event_type TEXT NOT NULL,
                    input_data TEXT,
                    decision TEXT,
                    reasoning TEXT,
                    output_data TEXT
                )
                """
            )
            connection.commit()

    def record_event(
        self,
        *,
        timestamp: datetime,
        stage: str,
        event_type: str,
        input_data: Optional[Dict[str, Any]] = None,
        decision: Optional[str] = None,
        reasoning: Optional[str] = None,
        output_data: Optional[Dict[str, Any]] = None,
    ) -> int:
        """Persist one audit event and return its database ID."""

        with self._connect() as connection:
            cursor = connection.execute(
                """
                INSERT INTO audit_events (
                    timestamp,
                    stage,
                    event_type,
                    input_data,
                    decision,
                    reasoning,
                    output_data
                )
                VALUES (?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    timestamp.isoformat(),
                    stage,
                    event_type,
                    json.dumps(input_data, default=str)
                    if input_data is not None
                    else None,
                    decision,
                    reasoning,
                    json.dumps(output_data, default=str)
                    if output_data is not None
                    else None,
                ),
            )
            connection.commit()
            return int(cursor.lastrowid)

    def list_events(self) -> List[Dict[str, Any]]:
        """Return audit events in chronological insertion order."""

        with self._connect() as connection:
            rows = connection.execute(
                """
                SELECT
                    id,
                    timestamp,
                    stage,
                    event_type,
                    input_data,
                    decision,
                    reasoning,
                    output_data
                FROM audit_events
                ORDER BY id ASC
                """
            ).fetchall()

        events: List[Dict[str, Any]] = []

        for row in rows:
            events.append(
                {
                    "id": row["id"],
                    "timestamp": row["timestamp"],
                    "stage": row["stage"],
                    "event_type": row["event_type"],
                    "input_data": (
                        json.loads(row["input_data"])
                        if row["input_data"] is not None
                        else None
                    ),
                    "decision": row["decision"],
                    "reasoning": row["reasoning"],
                    "output_data": (
                        json.loads(row["output_data"])
                        if row["output_data"] is not None
                        else None
                    ),
                }
            )

        return events