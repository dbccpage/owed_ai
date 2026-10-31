"""Process-safe reservations shared across tenants; uncertain calls keep their charge."""

from __future__ import annotations

import math
import sqlite3
import time
import uuid
from datetime import UTC, datetime
from decimal import ROUND_CEILING, Decimal
from pathlib import Path

from pydantic import JsonValue

from .domain import ModelProvider, ModelReply, ProviderFailure
from .hosting import HostedPolicy, Principal


class SpendLedger:
    def __init__(self, root: Path):
        root.mkdir(parents=True, exist_ok=True)
        self.path = root / "spending.sqlite3"
        with self.connection() as db:
            db.executescript("""
                PRAGMA journal_mode=WAL;
                CREATE TABLE IF NOT EXISTS leases (
                    run TEXT PRIMARY KEY, owner TEXT NOT NULL, deadline REAL NOT NULL
                );
                CREATE TABLE IF NOT EXISTS charges (
                    id TEXT PRIMARY KEY, run TEXT NOT NULL, owner TEXT NOT NULL,
                    day TEXT NOT NULL, reserved INTEGER NOT NULL, charged INTEGER NOT NULL,
                    state TEXT NOT NULL DEFAULT 'reserved'
                );
                CREATE TABLE IF NOT EXISTS circuit (id INTEGER PRIMARY KEY, halted INTEGER NOT NULL);
                INSERT OR IGNORE INTO circuit VALUES (1,0);
            """)

    def connection(self) -> sqlite3.Connection:
        db = sqlite3.connect(self.path, timeout=10)
        db.row_factory = sqlite3.Row
        return db

    def admit_run(self, run: str, owner: str, policy: HostedPolicy, seconds: int) -> bool:
        with self.connection() as db:
            db.execute("BEGIN IMMEDIATE")
            if db.execute("SELECT 1 FROM leases WHERE run=?", (run,)).fetchone():
                return False
            count = db.execute("SELECT COUNT(*) FROM leases WHERE deadline>?", (time.time(),)).fetchone()[0]
            if count >= policy.concurrent_runs:
                raise ValueError("hosted_concurrency_limit")
            db.execute("INSERT INTO leases VALUES (?,?,?)", (run, owner, time.time() + seconds + 65))
        return True

    def release_run(self, run: str) -> None:
        with self.connection() as db:
            db.execute("DELETE FROM leases WHERE run=?", (run,))

    def reserve(self, run: str, owner: str, policy: HostedPolicy) -> str:
        day = datetime.now(UTC).date().isoformat()
        with self.connection() as db:
            db.execute("BEGIN IMMEDIATE")
            if db.execute("SELECT halted FROM circuit WHERE id=1").fetchone()[0]:
                raise ProviderFailure("spending_halted")
            if not db.execute(
                "SELECT 1 FROM leases WHERE run=? AND owner=? AND deadline>?",
                (run, owner, time.time()),
            ).fetchone():
                raise ProviderFailure("hosted_lease_required")
            for clause, params, requests, budget in (
                ("day=?", (day,), policy.daily_requests, policy.daily_microdollars),
                ("day=? AND owner=?", (day, owner), policy.user_daily_requests, policy.user_daily_microdollars),
            ):
                row = db.execute(
                    "SELECT COUNT(*),COALESCE(SUM(charged),0) FROM charges WHERE " + clause, params
                ).fetchone()
                if row[0] >= requests or row[1] + policy.request_microdollars > budget:
                    raise ProviderFailure("shared_spending_limit")
            key = uuid.uuid4().hex
            db.execute(
                "INSERT INTO charges(id,run,owner,day,reserved,charged) VALUES (?,?,?,?,?,?)",
                (key, run, owner, day, policy.request_microdollars, policy.request_microdollars),
            )
        return key

    def settle(self, key: str, cost: float | None) -> None:
        # Never refund an uncertain timeout/refusal, missing usage, or killed process.
        if cost is None:
            return
        with self.connection() as db:
            db.execute("BEGIN IMMEDIATE")
            row = db.execute("SELECT * FROM charges WHERE id=?", (key,)).fetchone()
            if row is None or row["state"] != "reserved":
                raise ValueError("reservation_missing_or_settled")
            if not math.isfinite(cost) or cost < 0:
                db.execute("UPDATE circuit SET halted=1 WHERE id=1")
                return
            actual = int((Decimal(str(cost)) * 1_000_000).to_integral_value(rounding=ROUND_CEILING))
            db.execute("UPDATE charges SET charged=?,state='reported' WHERE id=?", (actual, key))
            if actual > row["reserved"]:
                db.execute("UPDATE circuit SET halted=1 WHERE id=1")

    def usage(self, owner: str) -> dict[str, JsonValue]:
        day = datetime.now(UTC).date().isoformat()
        with self.connection() as db:
            row = db.execute(
                "SELECT COUNT(*),COALESCE(SUM(charged),0),COALESCE(SUM(state='reserved'),0) "
                "FROM charges WHERE day=? AND owner=?", (day, owner),
            ).fetchone()
            halted = bool(db.execute("SELECT halted FROM circuit WHERE id=1").fetchone()[0])
        return {"utc_day": day, "requests": row[0], "charged_microdollars": row[1],
                "uncertain_reservations": row[2], "halted": halted}


class MeteredProvider:
    def __init__(self, provider: ModelProvider, ledger: SpendLedger, run: str, principal: Principal):
        self.provider, self.ledger, self.run, self.principal = provider, ledger, run, principal

    def generate(
        self, system: str, user: str, schema: dict[str, JsonValue], max_tokens: int, timeout: float
    ) -> ModelReply:
        policy = HostedPolicy.from_env()
        if not policy.permits(self.principal):
            raise ProviderFailure("live_access_expired_or_disabled")
        key = self.ledger.reserve(self.run, self.principal.owner, policy)
        reply = self.provider.generate(system, user, schema, max_tokens, timeout)
        self.ledger.settle(key, reply.cost)
        return reply
