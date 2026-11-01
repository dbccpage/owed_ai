"""Hosted admission boundary: verified OIDC claims, isolated stores, fixed provider."""

from __future__ import annotations

import json
import os
import time
from collections.abc import Mapping
from pathlib import Path
from urllib.parse import urlsplit

from pydantic import Field, JsonValue

from .domain import Record, RunSpec, canonical, digest, json_object
from .providers import ProviderConfig
from .storage import Store


def hosted_mode() -> bool:
    mode = os.getenv("WORKBENCH_MODE", "hosted" if os.getenv("RENDER") else "local")
    if mode not in ("local", "hosted") or (os.getenv("RENDER") and mode != "hosted"):
        raise ValueError("invalid_hosting_mode")
    return mode == "hosted"


def secure_url(value: str) -> bool:
    url = urlsplit(value)
    return bool(url.hostname) and not (url.username or url.password or url.query or url.fragment) and (
        url.scheme == "https"
        or (
            not os.getenv("RENDER")
            and url.scheme == "http"
            and url.hostname in ("localhost", "127.0.0.1")
        )
    )


class Principal(Record):
    owner: str
    expires: int


class HostedPolicy(Record):
    live_enabled: bool = False
    auth_enabled: bool = False
    issuer: str = ""
    subjects: tuple[str, ...] = ()
    model: str = "openai/gpt-4.1-mini"
    daily_requests: int = Field(default=120, ge=1, le=10000)
    user_daily_requests: int = Field(default=24, ge=1, le=1000)
    daily_microdollars: int = Field(default=2_000_000, ge=1)
    user_daily_microdollars: int = Field(default=500_000, ge=1)
    request_microdollars: int = Field(default=100_000, ge=1)
    concurrent_runs: int = Field(default=1, ge=1, le=4)

    @classmethod
    def from_env(cls) -> HostedPolicy:
        enabled = os.getenv("WORKBENCH_LIVE_ENABLED", "false")
        auth = os.getenv("WORKBENCH_AUTH_ENABLED", enabled)
        if enabled not in ("true", "false") or auth not in ("true", "false"):
            raise ValueError("invalid_live_switch")
        if enabled == "true" and auth != "true":
            raise ValueError("live_requires_auth")
        subjects = json.loads(os.getenv("WORKBENCH_ALLOWED_SUBJECTS", "[]"))
        if not isinstance(subjects, list) or any(
            not isinstance(s, str) or not s.strip() for s in subjects
        ):
            raise ValueError("subject_list_required")
        policy = cls(
            live_enabled=enabled == "true",
            auth_enabled=auth == "true",
            issuer=os.getenv("WORKBENCH_AUTH_ISSUER", ""),
            subjects=tuple(subjects),
            model=os.getenv("WORKBENCH_HOSTED_MODEL", "openai/gpt-4.1-mini"),
            **{
                field: int(os.getenv("WORKBENCH_" + field.upper(), str(default)))
                for field, default in (
                    ("daily_requests", 120), ("user_daily_requests", 24),
                    ("daily_microdollars", 2_000_000),
                    ("user_daily_microdollars", 500_000),
                    ("request_microdollars", 100_000), ("concurrent_runs", 1),
                )
            },
        )
        if (policy.auth_enabled and not secure_url(policy.issuer)) or (
            policy.live_enabled and not policy.model.strip()
        ):
            raise ValueError("hosted_auth_and_model_required")
        return policy

    def login_subject(self, logged_in: bool, claims: Mapping[str, object]) -> str:
        """Inspect Streamlit-verified identity without granting experiment authority."""
        subject, expiry = claims.get("sub"), claims.get("exp")
        if (
            not self.auth_enabled or not logged_in or claims.get("iss") != self.issuer
            or not isinstance(subject, str) or not subject.strip()
            or type(expiry) is not int or expiry <= time.time()
        ):
            raise ValueError("login_not_verified")
        return subject

    def authenticate(self, logged_in: bool, claims: Mapping[str, object]) -> Principal:
        """Only call with claims verified by Streamlit OIDC, never uploaded JSON/headers."""
        try:
            subject = self.login_subject(logged_in, claims)
        except ValueError:
            raise ValueError("live_access_denied") from None
        expiry = claims.get("exp")
        if not self.live_enabled or subject not in self.subjects or type(expiry) is not int:
            raise ValueError("live_access_denied")
        return Principal(owner=digest({"issuer": self.issuer, "subject": subject}), expires=expiry)

    def provider(self) -> ProviderConfig:
        # Hosted visitors cannot select a model, endpoint, credential, or fallback.
        config = ProviderConfig(
            "openrouter", self.model, "https://openrouter.ai/api/v1", "json_schema",
            "OPENROUTER_API_KEY", os.getenv("OPENROUTER_API_KEY", ""),
        )
        config.validate()
        return config

    def permits(self, principal: Principal) -> bool:
        return self.live_enabled and principal.expires > time.time() and any(
            principal.owner == digest({"issuer": self.issuer, "subject": subject})
            for subject in self.subjects
        )


def data_root() -> Path:
    return Path(os.getenv("WORKBENCH_DATA_DIR", "data")).resolve()


def private_store(principal: Principal) -> Store:
    if len(principal.owner) != 64 or any(c not in "0123456789abcdef" for c in principal.owner):
        raise ValueError("invalid_owner")
    if principal.expires <= time.time():
        raise ValueError("login_expired")
    return Store(data_root() / "users" / principal.owner)


def submit_hosted(principal: Principal, spec: RunSpec, request_id: str) -> str:
    from .spending import SpendLedger
    from .worker import launch

    policy = HostedPolicy.from_env()
    if not policy.permits(principal):
        raise ValueError("live_access_denied")
    if spec.limits.requests > 12 or spec.limits.seconds > 300 or spec.limits.output_tokens > 2048:
        raise ValueError("hosted_run_limit")
    if len(canonical(spec).encode()) > 32768:
        raise ValueError("hosted_input_limit")
    store = private_store(principal)
    store.recover()
    config: dict[str, JsonValue] = {
        **policy.provider().public(),
        "hosted": {"owner": principal.owner, "expires": principal.expires},
    }
    run_id = store.enqueue(request_id, json_object(spec), config)
    if store.get(run_id)["status"] != "queued":
        return run_id
    ledger = SpendLedger(data_root() / "control")
    try:
        if ledger.admit_run(run_id, principal.owner, policy, spec.limits.seconds):
            launch(store, run_id)
    except (ValueError, OSError):
        store.cancel(run_id)
        ledger.release_run(run_id)
        raise
    return run_id
