"""Usage/budget persistence — SQLite (dev default) or Postgres (prod), selected
the same way AegisAI's own control-plane store factory does."""

from __future__ import annotations

import os
import sqlite3
from pathlib import Path
from typing import Protocol

from agent_finops.models import Budget, UsageEvent, UsageResult

_SCHEMA = """
CREATE TABLE IF NOT EXISTS usage_events (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    scope_type TEXT NOT NULL,
    scope_value TEXT NOT NULL,
    provider TEXT NOT NULL,
    model TEXT NOT NULL,
    prompt_tokens INTEGER NOT NULL,
    completion_tokens INTEGER NOT NULL,
    cost_usd REAL NOT NULL,
    recorded_at TEXT NOT NULL
);
CREATE INDEX IF NOT EXISTS ix_usage_events_scope ON usage_events (scope_type, scope_value);

CREATE TABLE IF NOT EXISTS budgets (
    scope_type TEXT NOT NULL,
    scope_value TEXT NOT NULL,
    budget_usd REAL NOT NULL,
    PRIMARY KEY (scope_type, scope_value)
);

CREATE TABLE IF NOT EXISTS workflow_outcomes (
    workflow_id TEXT PRIMARY KEY,
    tenant_id TEXT NOT NULL,
    compliant_success INTEGER NOT NULL,
    eval_pass INTEGER NOT NULL,
    policy_deny INTEGER NOT NULL,
    hitl_required INTEGER NOT NULL,
    hitl_approved INTEGER NOT NULL,
    budget_ok INTEGER NOT NULL,
    total_cost_usd REAL NOT NULL DEFAULT 0,
    recorded_at TEXT NOT NULL
);
CREATE INDEX IF NOT EXISTS ix_outcomes_tenant ON workflow_outcomes (tenant_id);
"""


class FinOpsStore(Protocol):
    def record_usage(self, event: UsageEvent) -> UsageResult: ...

    def get_budget(self, scope_type: str, scope_value: str) -> Budget | None: ...

    def set_budget(self, scope_type: str, scope_value: str, budget_usd: float) -> Budget: ...

    def total_cost(self, scope_type: str, scope_value: str) -> float: ...


class SQLiteFinOpsStore:
    def __init__(self, db_path: str | Path = ":memory:") -> None:
        self._db_path = str(db_path)
        # A single shared connection keeps :memory: databases alive across calls
        # (a fresh connection would otherwise get a fresh, empty in-memory db).
        self._conn = sqlite3.connect(self._db_path, check_same_thread=False)
        self._conn.executescript(_SCHEMA)
        self._conn.commit()

    def record_usage(self, event: UsageEvent) -> UsageResult:
        self._conn.execute(
            """INSERT INTO usage_events
               (scope_type, scope_value, provider, model, prompt_tokens, completion_tokens, cost_usd, recorded_at)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?)""",
            (
                event.scope_type,
                event.scope_value,
                event.provider,
                event.model,
                event.prompt_tokens,
                event.completion_tokens,
                event.cost_usd,
                event.recorded_at,
            ),
        )
        self._conn.commit()
        total = self.total_cost(event.scope_type, event.scope_value)
        budget = self.get_budget(event.scope_type, event.scope_value)
        budget_usd = budget.budget_usd if budget else None
        breached = budget_usd is not None and total > budget_usd
        return UsageResult(
            scope_type=event.scope_type,
            scope_value=event.scope_value,
            cost_usd=event.cost_usd,
            total_cost_usd=total,
            budget_usd=budget_usd,
            breached=breached,
        )

    def get_budget(self, scope_type: str, scope_value: str) -> Budget | None:
        row = self._conn.execute(
            "SELECT budget_usd FROM budgets WHERE scope_type = ? AND scope_value = ?",
            (scope_type, scope_value),
        ).fetchone()
        if row is None:
            return None
        return Budget(scope_type=scope_type, scope_value=scope_value, budget_usd=row[0])

    def set_budget(self, scope_type: str, scope_value: str, budget_usd: float) -> Budget:
        self._conn.execute(
            """INSERT INTO budgets (scope_type, scope_value, budget_usd) VALUES (?, ?, ?)
               ON CONFLICT (scope_type, scope_value) DO UPDATE SET budget_usd = excluded.budget_usd""",
            (scope_type, scope_value, budget_usd),
        )
        self._conn.commit()
        return Budget(scope_type=scope_type, scope_value=scope_value, budget_usd=budget_usd)

    def total_cost(self, scope_type: str, scope_value: str) -> float:
        row = self._conn.execute(
            "SELECT COALESCE(SUM(cost_usd), 0) FROM usage_events WHERE scope_type = ? AND scope_value = ?",
            (scope_type, scope_value),
        ).fetchone()
        return round(row[0], 8) if row else 0.0

    def aggregate_ops(self) -> dict:
        row = self._conn.execute(
            "SELECT COUNT(*), COALESCE(SUM(cost_usd), 0) FROM usage_events"
        ).fetchone()
        budget_count = self._conn.execute("SELECT COUNT(*) FROM budgets").fetchone()
        return {
            "usage_events": int(row[0] or 0),
            "total_cost_usd": round(float(row[1] or 0), 4),
            "budgets_configured": int(budget_count[0] or 0),
        }


class PostgresFinOpsStore:
    """Same schema and queries as SQLiteFinOpsStore, over a Postgres connection."""

    def __init__(self, database_url: str) -> None:
        import psycopg

        self._psycopg = psycopg
        self.database_url = database_url
        self._ensure_schema()

    def _ensure_schema(self) -> None:
        pg_schema = _SCHEMA.replace("INTEGER PRIMARY KEY AUTOINCREMENT", "SERIAL PRIMARY KEY")
        with self._psycopg.connect(self.database_url) as conn:
            conn.execute(pg_schema)
            conn.commit()

    def record_usage(self, event: UsageEvent) -> UsageResult:
        with self._psycopg.connect(self.database_url) as conn:
            conn.execute(
                """INSERT INTO usage_events
                   (scope_type, scope_value, provider, model, prompt_tokens, completion_tokens, cost_usd, recorded_at)
                   VALUES (%s, %s, %s, %s, %s, %s, %s, %s)""",
                (
                    event.scope_type,
                    event.scope_value,
                    event.provider,
                    event.model,
                    event.prompt_tokens,
                    event.completion_tokens,
                    event.cost_usd,
                    event.recorded_at,
                ),
            )
            conn.commit()
        total = self.total_cost(event.scope_type, event.scope_value)
        budget = self.get_budget(event.scope_type, event.scope_value)
        budget_usd = budget.budget_usd if budget else None
        breached = budget_usd is not None and total > budget_usd
        return UsageResult(
            scope_type=event.scope_type,
            scope_value=event.scope_value,
            cost_usd=event.cost_usd,
            total_cost_usd=total,
            budget_usd=budget_usd,
            breached=breached,
        )

    def get_budget(self, scope_type: str, scope_value: str) -> Budget | None:
        with self._psycopg.connect(self.database_url) as conn:
            row = conn.execute(
                "SELECT budget_usd FROM budgets WHERE scope_type = %s AND scope_value = %s",
                (scope_type, scope_value),
            ).fetchone()
        if row is None:
            return None
        return Budget(scope_type=scope_type, scope_value=scope_value, budget_usd=row[0])

    def set_budget(self, scope_type: str, scope_value: str, budget_usd: float) -> Budget:
        with self._psycopg.connect(self.database_url) as conn:
            conn.execute(
                """INSERT INTO budgets (scope_type, scope_value, budget_usd) VALUES (%s, %s, %s)
                   ON CONFLICT (scope_type, scope_value) DO UPDATE SET budget_usd = excluded.budget_usd""",
                (scope_type, scope_value, budget_usd),
            )
            conn.commit()
        return Budget(scope_type=scope_type, scope_value=scope_value, budget_usd=budget_usd)

    def total_cost(self, scope_type: str, scope_value: str) -> float:
        with self._psycopg.connect(self.database_url) as conn:
            row = conn.execute(
                "SELECT COALESCE(SUM(cost_usd), 0) FROM usage_events WHERE scope_type = %s AND scope_value = %s",
                (scope_type, scope_value),
            ).fetchone()
        return round(row[0], 8) if row else 0.0

    def aggregate_ops(self) -> dict:
        with self._psycopg.connect(self.database_url) as conn:
            row = conn.execute(
                "SELECT COUNT(*), COALESCE(SUM(cost_usd), 0) FROM usage_events"
            ).fetchone()
            budget_count = conn.execute("SELECT COUNT(*) FROM budgets").fetchone()
        return {
            "usage_events": int(row[0] or 0),
            "total_cost_usd": round(float(row[1] or 0), 4),
            "budgets_configured": int(budget_count[0] or 0),
        }


def build_store() -> FinOpsStore:
    """Select persistence backend: sqlite (dev/demo) or postgres (production)."""
    backend = os.getenv("AGENTFINOPS_DB_BACKEND", "sqlite").lower()
    if backend == "postgres":
        database_url = os.getenv("DATABASE_URL", "").strip()
        if not database_url:
            raise ValueError("DATABASE_URL is required when AGENTFINOPS_DB_BACKEND=postgres")
        return PostgresFinOpsStore(database_url)
    db_path = os.getenv("AGENTFINOPS_DB_PATH", ":memory:")
    return SQLiteFinOpsStore(db_path)


# --- Outcome KPI (ADR-029) ---
def _ensure_outcome_methods():
    pass


def record_workflow_outcome(store, row: dict) -> dict:
    if not hasattr(store, "_conn"):
        raise RuntimeError("workflow outcomes require SQLite store in v1")
    store._conn.execute(
        """INSERT INTO workflow_outcomes
           (workflow_id, tenant_id, compliant_success, eval_pass, policy_deny,
            hitl_required, hitl_approved, budget_ok, total_cost_usd, recorded_at)
           VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
           ON CONFLICT(workflow_id) DO UPDATE SET
             compliant_success=excluded.compliant_success,
             eval_pass=excluded.eval_pass,
             policy_deny=excluded.policy_deny,
             hitl_required=excluded.hitl_required,
             hitl_approved=excluded.hitl_approved,
             budget_ok=excluded.budget_ok,
             total_cost_usd=excluded.total_cost_usd,
             recorded_at=excluded.recorded_at
        """,
        (
            row["workflow_id"],
            row["tenant_id"],
            int(row["compliant_success"]),
            int(row["eval_pass"]),
            int(row["policy_deny"]),
            int(row["hitl_required"]),
            int(row["hitl_approved"]),
            int(row["budget_ok"]),
            float(row.get("total_cost_usd") or 0),
            row["recorded_at"],
        ),
    )
    store._conn.commit()
    return row


def cost_per_compliant_outcome(store, tenant_id: str | None = None) -> dict:
    if not hasattr(store, "_conn"):
        return {"tenant_id": tenant_id, "compliant_outcomes": 0, "total_cost_usd": 0.0, "cost_per_compliant_outcome": None}
    if tenant_id:
        cur = store._conn.execute(
            """SELECT COUNT(*), COALESCE(SUM(total_cost_usd), 0)
               FROM workflow_outcomes
               WHERE tenant_id = ? AND compliant_success = 1""",
            (tenant_id,),
        )
    else:
        cur = store._conn.execute(
            """SELECT COUNT(*), COALESCE(SUM(total_cost_usd), 0)
               FROM workflow_outcomes WHERE compliant_success = 1"""
        )
    count, cost = cur.fetchone()
    count = int(count or 0)
    cost = float(cost or 0)
    return {
        "tenant_id": tenant_id,
        "compliant_outcomes": count,
        "total_cost_usd": cost,
        "cost_per_compliant_outcome": (cost / count) if count else None,
    }
