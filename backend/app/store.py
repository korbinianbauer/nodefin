"""Minimal SQLite persistence for strategies and simulation runs.

Phase 1 of the scaling plan is single-process execution, so a local SQLite file
is enough and keeps the MVP dependency-free. The schema mirrors the tables
described in the design (strategies, simulation_runs, results).
"""
from __future__ import annotations

import json
import os
import sqlite3
import uuid
from datetime import datetime, timezone

DB_PATH = os.environ.get("NODEFIN_DB", os.path.join(os.path.dirname(__file__), "nodefin.db"))


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _connect() -> sqlite3.Connection:
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def init_db() -> None:
    with _connect() as conn:
        conn.executescript(
            """
            CREATE TABLE IF NOT EXISTS strategies (
                id TEXT PRIMARY KEY,
                name TEXT NOT NULL,
                description TEXT,
                graph TEXT NOT NULL,
                created_at TEXT NOT NULL,
                updated_at TEXT NOT NULL
            );
            CREATE TABLE IF NOT EXISTS simulation_runs (
                id TEXT PRIMARY KEY,
                strategy_id TEXT,
                status TEXT NOT NULL,
                created_at TEXT NOT NULL,
                results TEXT
            );
            """
        )


def create_strategy(name: str, graph: dict, description: str = "") -> dict:
    sid = str(uuid.uuid4())
    now = _now()
    with _connect() as conn:
        conn.execute(
            "INSERT INTO strategies VALUES (?,?,?,?,?,?)",
            (sid, name, description, json.dumps(graph), now, now),
        )
    return get_strategy(sid)


def get_strategy(sid: str) -> dict | None:
    with _connect() as conn:
        row = conn.execute("SELECT * FROM strategies WHERE id=?", (sid,)).fetchone()
    if not row:
        return None
    return _strategy_row(row)


def list_strategies() -> list[dict]:
    with _connect() as conn:
        rows = conn.execute(
            "SELECT * FROM strategies ORDER BY updated_at DESC"
        ).fetchall()
    return [_strategy_row(r) for r in rows]


def update_strategy(sid: str, name: str, graph: dict, description: str = "") -> dict | None:
    if not get_strategy(sid):
        return None
    with _connect() as conn:
        conn.execute(
            "UPDATE strategies SET name=?, description=?, graph=?, updated_at=? WHERE id=?",
            (name, description, json.dumps(graph), _now(), sid),
        )
    return get_strategy(sid)


def delete_strategy(sid: str) -> bool:
    with _connect() as conn:
        cur = conn.execute("DELETE FROM strategies WHERE id=?", (sid,))
    return cur.rowcount > 0


def _strategy_row(row: sqlite3.Row) -> dict:
    return {
        "id": row["id"],
        "name": row["name"],
        "description": row["description"] or "",
        "graph": json.loads(row["graph"]),
        "created_at": row["created_at"],
        "updated_at": row["updated_at"],
    }


def save_run(strategy_id: str | None, status: str, results: dict) -> str:
    rid = str(uuid.uuid4())
    with _connect() as conn:
        conn.execute(
            "INSERT INTO simulation_runs VALUES (?,?,?,?,?)",
            (rid, strategy_id, status, _now(), json.dumps(results)),
        )
    return rid


def get_run(rid: str) -> dict | None:
    with _connect() as conn:
        row = conn.execute("SELECT * FROM simulation_runs WHERE id=?", (rid,)).fetchone()
    if not row:
        return None
    return {
        "id": row["id"],
        "strategy_id": row["strategy_id"],
        "status": row["status"],
        "created_at": row["created_at"],
        "results": json.loads(row["results"]) if row["results"] else None,
    }
