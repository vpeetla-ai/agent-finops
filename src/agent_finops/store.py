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
    human_review_minutes REAL NOT NULL DEFAULT 0,
    verified_outcome TEXT NOT NULL DEFAULT 'unverified',
    recorded_at TEXT NOT NULL
);
CREATE INDEX IF NOT EXISTS ix_outcomes_tenant ON workflow_outcomes (tenant_id);
"""

VERIFIED_OUTCOME_VALUES = frozenset({"verified", "rejected", "unverified", "partial"})
DEFAULT_HUMAN_MINUTE_USD = 1.5


def _migrate_outcome_columns(conn: sqlite3.Connection) -> None:
    cols = {row[1] for row in conn.execute("PRAGMA table_info(workflow_outcomes)").fetchall()}
    if "human_review_minutes" not in cols:
        conn.execute(
            "ALTER TABLE workflow_outcomes ADD COLUMN human_review_minutes REAL NOT NULL DEFAULT 0"
        )
    if "verified_outcome" not in cols:
        conn.execute(
            "ALTER TABLE workflow_outcomes ADD COLUMN verified_outcome TEXT NOT NULL DEFAULT 'unverified'"
        )


_OUTCOME_PG_MIGRATIONS = (
    "ALTER TABLE workflow_outcomes ADD COLUMN IF NOT EXISTS human_review_minutes DOUBLE PRECISION NOT NULL DEFAULT 0",
    "ALTER TABLE workflow_outcomes ADD COLUMN IF NOT EXISTS verified_outcome TEXT NOT NULL DEFAULT 'unverified'",
)


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
        _migrate_outcome_columns(self._conn)
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
            for stmt in _OUTCOME_PG_MIGRATIONS:
                conn.execute(stmt)
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

_OUTCOME_INSERT_SQLITE = """
INSERT INTO workflow_outcomes
  (workflow_id, tenant_id, compliant_success, eval_pass, policy_deny,
   hitl_required, hitl_approved, budget_ok, total_cost_usd,
   human_review_minutes, verified_outcome, recorded_at)
VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
ON CONFLICT(workflow_id) DO UPDATE SET
  compliant_success=excluded.compliant_success,
  eval_pass=excluded.eval_pass,
  policy_deny=excluded.policy_deny,
  hitl_required=excluded.hitl_required,
  hitl_approved=excluded.hitl_approved,
  budget_ok=excluded.budget_ok,
  total_cost_usd=excluded.total_cost_usd,
  human_review_minutes=excluded.human_review_minutes,
  verified_outcome=excluded.verified_outcome,
  recorded_at=excluded.recorded_at
"""

_OUTCOME_INSERT_PG = """
INSERT INTO workflow_outcomes
  (workflow_id, tenant_id, compliant_success, eval_pass, policy_deny,
   hitl_required, hitl_approved, budget_ok, total_cost_usd,
   human_review_minutes, verified_outcome, recorded_at)
VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
ON CONFLICT(workflow_id) DO UPDATE SET
  compliant_success=EXCLUDED.compliant_success,
  eval_pass=EXCLUDED.eval_pass,
  policy_deny=EXCLUDED.policy_deny,
  hitl_required=EXCLUDED.hitl_required,
  hitl_approved=EXCLUDED.hitl_approved,
  budget_ok=EXCLUDED.budget_ok,
  total_cost_usd=EXCLUDED.total_cost_usd,
  human_review_minutes=EXCLUDED.human_review_minutes,
  verified_outcome=EXCLUDED.verified_outcome,
  recorded_at=EXCLUDED.recorded_at
"""


def record_workflow_outcome(store, row: dict) -> dict:
    verified = str(row.get("verified_outcome") or "unverified")
    if verified not in VERIFIED_OUTCOME_VALUES:
        raise ValueError(
            f"verified_outcome must be one of {sorted(VERIFIED_OUTCOME_VALUES)}; got {verified!r}"
        )
    params = (
        row["workflow_id"],
        row["tenant_id"],
        int(row["compliant_success"]),
        int(row["eval_pass"]),
        int(row["policy_deny"]),
        int(row["hitl_required"]),
        int(row["hitl_approved"]),
        int(row["budget_ok"]),
        float(row.get("total_cost_usd") or 0),
        float(row.get("human_review_minutes") or 0),
        verified,
        row["recorded_at"],
    )
    if hasattr(store, "_conn"):
        store._conn.execute(_OUTCOME_INSERT_SQLITE, params)
        store._conn.commit()
        return row
    if hasattr(store, "database_url"):
        with store._psycopg.connect(store.database_url) as conn:
            conn.execute(_OUTCOME_INSERT_PG, params)
            conn.commit()
        return row
    raise RuntimeError("unsupported finops store for workflow outcomes")


def cost_per_compliant_outcome(store, tenant_id: str | None = None) -> dict:
    human_rate = float(os.getenv("AGENTFINOPS_HUMAN_MINUTE_USD", str(DEFAULT_HUMAN_MINUTE_USD)))
    empty = {
        "tenant_id": tenant_id,
        "compliant_outcomes": 0,
        "total_cost_usd": 0.0,
        "cost_per_compliant_outcome": None,
        "verified_outcomes": 0,
        "cost_per_verified_outcome": None,
        "total_human_review_minutes": 0.0,
        "estimated_human_cost_usd": 0.0,
        "fully_loaded_cost_per_verified": None,
        "verified_outcome_enum": sorted(VERIFIED_OUTCOME_VALUES),
        "human_minute_usd": human_rate,
    }

    def _pack(compliant: int, verified: int, token_cost: float, human_minutes: float) -> dict:
        human_cost = round(human_minutes * human_rate, 6)
        return {
            "tenant_id": tenant_id,
            "compliant_outcomes": compliant,
            "total_cost_usd": token_cost,
            "cost_per_compliant_outcome": (token_cost / compliant) if compliant else None,
            "verified_outcomes": verified,
            "cost_per_verified_outcome": (token_cost / verified) if verified else None,
            "total_human_review_minutes": human_minutes,
            "estimated_human_cost_usd": human_cost,
            "fully_loaded_cost_per_verified": (
                (token_cost + human_cost) / verified if verified else None
            ),
            "verified_outcome_enum": sorted(VERIFIED_OUTCOME_VALUES),
            "human_minute_usd": human_rate,
        }

    if hasattr(store, "_conn"):
        if tenant_id:
            cur = store._conn.execute(
                """SELECT
                     SUM(CASE WHEN compliant_success = 1 THEN 1 ELSE 0 END),
                     SUM(CASE WHEN verified_outcome = 'verified' THEN 1 ELSE 0 END),
                     COALESCE(SUM(CASE WHEN compliant_success = 1 THEN total_cost_usd ELSE 0 END), 0),
                     COALESCE(SUM(human_review_minutes), 0)
                   FROM workflow_outcomes WHERE tenant_id = ?""",
                (tenant_id,),
            )
        else:
            cur = store._conn.execute(
                """SELECT
                     SUM(CASE WHEN compliant_success = 1 THEN 1 ELSE 0 END),
                     SUM(CASE WHEN verified_outcome = 'verified' THEN 1 ELSE 0 END),
                     COALESCE(SUM(CASE WHEN compliant_success = 1 THEN total_cost_usd ELSE 0 END), 0),
                     COALESCE(SUM(human_review_minutes), 0)
                   FROM workflow_outcomes"""
            )
        compliant, verified, cost, minutes = cur.fetchone()
    elif hasattr(store, "database_url"):
        with store._psycopg.connect(store.database_url) as conn:
            if tenant_id:
                row = conn.execute(
                    """SELECT
                         SUM(CASE WHEN compliant_success = 1 THEN 1 ELSE 0 END),
                         SUM(CASE WHEN verified_outcome = 'verified' THEN 1 ELSE 0 END),
                         COALESCE(SUM(CASE WHEN compliant_success = 1 THEN total_cost_usd ELSE 0 END), 0),
                         COALESCE(SUM(human_review_minutes), 0)
                       FROM workflow_outcomes WHERE tenant_id = %s""",
                    (tenant_id,),
                ).fetchone()
            else:
                row = conn.execute(
                    """SELECT
                         SUM(CASE WHEN compliant_success = 1 THEN 1 ELSE 0 END),
                         SUM(CASE WHEN verified_outcome = 'verified' THEN 1 ELSE 0 END),
                         COALESCE(SUM(CASE WHEN compliant_success = 1 THEN total_cost_usd ELSE 0 END), 0),
                         COALESCE(SUM(human_review_minutes), 0)
                       FROM workflow_outcomes"""
                ).fetchone()
        compliant, verified, cost, minutes = row
    else:
        return empty

    return _pack(
        int(compliant or 0),
        int(verified or 0),
        float(cost or 0),
        float(minutes or 0),
    )
