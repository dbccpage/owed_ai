"""Transactional single-run admission, append-only decisions, content-addressed artifacts."""

from __future__ import annotations

import json
import re
import sqlite3
import time
import uuid
from pathlib import Path
from typing import cast

from pydantic import JsonValue

from .domain import canonical, digest
from .providers import redact


class Store:
    def __init__(self, root: Path):
        self.root = root.resolve()
        self.root.mkdir(parents=True, exist_ok=True)
        (self.root / "artifacts").mkdir(exist_ok=True)
        with self.connection() as db:
            db.executescript("""
                PRAGMA journal_mode=WAL;
                CREATE TABLE IF NOT EXISTS runs (
                    id TEXT PRIMARY KEY, request_id TEXT UNIQUE NOT NULL,
                    spec_hash TEXT NOT NULL, config_hash TEXT NOT NULL,
                    status TEXT NOT NULL, created REAL NOT NULL, heartbeat REAL NOT NULL,
                    cancel INTEGER NOT NULL DEFAULT 0, receipt_hash TEXT, pid INTEGER
                );
                CREATE UNIQUE INDEX IF NOT EXISTS one_active_run ON runs((1))
                    WHERE status IN ('queued','running');
                CREATE TABLE IF NOT EXISTS events (
                    id INTEGER PRIMARY KEY, run_id TEXT NOT NULL, artifact_hash TEXT NOT NULL
                );
                CREATE TABLE IF NOT EXISTS decisions (
                    id INTEGER PRIMARY KEY, run_id TEXT NOT NULL, candidate_hash TEXT NOT NULL,
                    actor TEXT NOT NULL, decision TEXT NOT NULL, created REAL NOT NULL
                );
            """)

    def connection(self) -> sqlite3.Connection:
        db = sqlite3.connect(self.root / "runs.sqlite3", timeout=10)
        db.row_factory = sqlite3.Row
        return db

    def artifact(self, value: JsonValue) -> str:
        clean = json.loads(redact(canonical(value)))
        key = digest(clean)
        path = self.root / "artifacts" / (key + ".json")
        if not path.exists():
            # Unique temporary file and atomic replacement: readers never see partial JSON.
            temporary = path.with_suffix("." + uuid.uuid4().hex + ".tmp")
            temporary.write_text(canonical(clean), encoding="utf-8")
            temporary.replace(path)
        return key

    def read(self, key: str) -> dict[str, JsonValue]:
        if not re.fullmatch(r"[0-9a-f]{64}", key):
            raise ValueError("invalid_artifact_digest")
        value = json.loads((self.root / "artifacts" / (key + ".json")).read_text(encoding="utf-8"))
        if digest(value) != key:
            raise ValueError("artifact_integrity_failure")
        if not isinstance(value, dict):
            raise ValueError("object_artifact_required")
        return cast(dict[str, JsonValue], value)

    def enqueue(
        self, request_id: str, spec: dict[str, JsonValue], config: dict[str, JsonValue]
    ) -> str:
        if redact(canonical(spec)) != canonical(spec):
            raise ValueError("secret_in_input")
        spec_hash, config_hash = self.artifact(spec), self.artifact(config)
        now = time.time()
        with self.connection() as db:
            old = db.execute("SELECT * FROM runs WHERE request_id=?", (request_id,)).fetchone()
            if old:
                if (old["spec_hash"], old["config_hash"]) != (spec_hash, config_hash):
                    raise ValueError("request_id_conflict")
                return str(old["id"])
            run_id = uuid.uuid4().hex
            try:
                db.execute(
                    "INSERT INTO runs(id,request_id,spec_hash,config_hash,status,created,heartbeat) VALUES (?,?,?,?,?,?,?)",
                    (run_id, request_id, spec_hash, config_hash, "queued", now, now),
                )
            except sqlite3.IntegrityError:
                raise ValueError("another_run_is_active") from None
        return run_id

    def claim(self, run_id: str, pid: int) -> bool:
        with self.connection() as db:
            row = db.execute(
                "UPDATE runs SET status='running',pid=?,heartbeat=? WHERE id=? AND status='queued' AND cancel=0",
                (pid, time.time(), run_id),
            )
            return row.rowcount == 1

    def get(self, run_id: str) -> dict[str, JsonValue]:
        with self.connection() as db:
            row = db.execute("SELECT * FROM runs WHERE id=?", (run_id,)).fetchone()
        if row is None:
            raise ValueError("unknown_run")
        return dict(row)

    def list_runs(self) -> list[dict[str, JsonValue]]:
        with self.connection() as db:
            return [
                dict(r) for r in db.execute("SELECT * FROM runs ORDER BY created DESC LIMIT 100")
            ]

    def event(self, run_id: str, event: dict[str, JsonValue]) -> None:
        key = self.artifact(event)
        with self.connection() as db:
            db.execute("INSERT INTO events(run_id,artifact_hash) VALUES (?,?)", (run_id, key))
            db.execute("UPDATE runs SET heartbeat=? WHERE id=?", (time.time(), run_id))

    def events(self, run_id: str) -> list[dict[str, JsonValue]]:
        with self.connection() as db:
            keys = [
                r[0]
                for r in db.execute(
                    "SELECT artifact_hash FROM events WHERE run_id=? ORDER BY id", (run_id,)
                )
            ]
        return [self.read(key) for key in keys]

    def cancel(self, run_id: str) -> None:
        with self.connection() as db:
            db.execute(
                "UPDATE runs SET cancel=1,status=CASE WHEN status='queued' THEN 'cancelled' ELSE status END WHERE id=? AND status IN ('queued','running')",
                (run_id,),
            )

    def cancelled(self, run_id: str) -> bool:
        return bool(self.get(run_id)["cancel"])

    def finish(self, run_id: str, status: str, receipt: dict[str, JsonValue]) -> None:
        key = self.artifact(receipt)
        with self.connection() as db:
            db.execute(
                "UPDATE runs SET status=?,receipt_hash=?,heartbeat=? WHERE id=? AND status='running'",
                (status, key, time.time(), run_id),
            )

    def recover(self) -> int:
        """Never resubmit uncertain requests. Mark workers interrupted after their maximum deadline."""
        count = 0
        for row in self.list_runs():
            if row["status"] not in ("queued", "running"):
                continue
            spec = self.read(str(row["spec_hash"]))
            limits = cast(dict[str, JsonValue], spec["limits"])
            deadline = float(cast(float, row["created"])) + int(cast(int, limits["seconds"])) + 60
            if time.time() > deadline:
                with self.connection() as db:
                    count += db.execute(
                        "UPDATE runs SET status='interrupted' WHERE id=? AND status IN ('queued','running')",
                        (row["id"],),
                    ).rowcount
        return count

    def admit(self, run_id: str, actor: str) -> str:
        if actor != "operator":
            raise ValueError("operator_required")
        run = self.get(run_id)
        if run["status"] != "completed" or not run["receipt_hash"]:
            raise ValueError("completed_run_required")
        receipt = self.read(str(run["receipt_hash"]))
        result = cast(dict[str, JsonValue], receipt["result"])
        if result.get("eligible") is not True:
            raise ValueError("candidate_not_eligible")
        candidate = cast(dict[str, JsonValue], result["child"])
        key = self.artifact(candidate)
        with self.connection() as db:
            db.execute(
                "INSERT INTO decisions(run_id,candidate_hash,actor,decision,created) VALUES (?,?,?,?,?)",
                (run_id, key, actor, "admitted", time.time()),
            )
        return key

    def active_prompt(self) -> dict[str, JsonValue] | None:
        with self.connection() as db:
            row = db.execute(
                "SELECT candidate_hash FROM decisions WHERE decision='admitted' ORDER BY id DESC LIMIT 1"
            ).fetchone()
        return self.read(row[0]) if row else None
