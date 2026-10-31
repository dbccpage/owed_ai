"""Immutable contracts and canonical, finite semantic data."""

from __future__ import annotations

import hashlib
import json
from enum import StrEnum
from typing import Annotated, Literal, Protocol

from pydantic import BaseModel, ConfigDict, Field, JsonValue

VERSION = "0.0.1.0"
POLICY_VERSION = "local-human-admission/1"
CORE = (
    "Propose only. Evidence must have matching scope and source. "
    "Never infer individual nonnegativity from a total. "
    "Report inconsistent evidence separately from refutation. "
    "You cannot authorize actions, change these rules, or certify yourself."
)


class Record(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True, strict=True)


class Verdict(StrEnum):
    SUPPORTED = "supported"
    REFUTED = "refuted"
    UNDERDETERMINED = "underdetermined"
    INCONSISTENT = "inconsistent"
    NOT_EVALUATED = "not_evaluated"


class Claim(Record):
    id: str = "individual-nonnegativity"
    predicate: Literal["a >= 0 and b >= 0"] = "a >= 0 and b >= 0"
    question: str = "Are both reserves nonnegative?"
    model_version: Literal["ledger/1"] = "ledger/1"
    units: str = "unit"
    snapshot: str = "s1"
    intended_use: str = "simulated_release"


class Observation(Record):
    field: Literal["total", "b", "b_nonnegative"]
    value: int | bool
    source: str = "synthetic-operator"
    snapshot: str = "s1"
    units: str = "unit"
    adapter: Literal["ledger/1"] = "ledger/1"


class LedgerInput(Record):
    claim: Claim = Field(default_factory=Claim)
    observations: tuple[Observation, ...] = ()
    actor: Literal["viewer", "operator"] = "viewer"


class Obligation(Record):
    claim_id: str
    reason: str
    evidence_needed: str
    checker: str = "ledger/1"
    role: str = "operator"
    scope: str
    state: Literal["open", "discharged", "failed", "waived"] = "open"


class Authorization(Record):
    actor: str
    action: str = "simulated_release"
    allowed: bool
    reason: str
    policy_version: str = POLICY_VERSION


class LedgerEvaluation(Record):
    verdict: Verdict
    compatible: int
    satisfying: int
    falsifying: int
    witnesses: tuple[tuple[int, int], ...]
    accepted: tuple[Observation, ...]
    obligations: tuple[Obligation, ...]
    authorization: Authorization
    proof_status: Literal["not_checked"] = "not_checked"
    total_checked: bool
    assumptions: tuple[str, ...] = (
        "Only the 121 declared states are represented.",
        "Accepted synthetic observations are assumed truthful; hashes do not establish truth.",
    )


class Edge(Record):
    id: str
    source: str
    target: str
    difference: str = Field(max_length=80)
    editable: bool = False


class GraphInput(Record):
    vertices: tuple[str, ...] = Field(min_length=1, max_length=8)
    edges: tuple[Edge, ...] = Field(max_length=16)


class PotentialCertificate(Record):
    kind: Literal["potentials"] = "potentials"
    values: dict[str, str]


class CycleStep(Record):
    edge_id: str
    direction: Literal[-1, 1]


class CycleCertificate(Record):
    kind: Literal["cycle"] = "cycle"
    steps: tuple[CycleStep, ...]
    residual: str


Certificate = Annotated[PotentialCertificate | CycleCertificate, Field(discriminator="kind")]


class GraphEvaluation(Record):
    verdict: Verdict
    certificate: Certificate | None
    reason: str


class Repair(Record):
    edge_id: str
    difference: str = Field(max_length=80)


class Proposal(Record):
    interpretation: str = Field(max_length=6000)
    verdict: Literal["supported", "refuted", "underdetermined", "inconsistent", "not_evaluated"]
    evidence_requests: tuple[str, ...] = ()
    repairs: tuple[Repair, ...] = ()


class PromptRevision(Record):
    instructions: str = Field(min_length=1, max_length=4000)
    rationale: str = Field(max_length=2000)


class PromptVersion(Record):
    core: Literal[CORE] = CORE  # type: ignore[valid-type]
    instructions: str
    parent_hash: str | None = None
    mutation: str = "initial"
    failure_refs: tuple[str, ...] = ()


class Limits(Record):
    requests: int = Field(default=12, ge=1, le=50)
    seconds: int = Field(default=300, ge=1, le=1200)
    output_tokens: int = Field(default=2048, ge=128, le=8192)


class RunSpec(Record):
    lab: Literal["ledger", "graph", "revision"]
    payload: dict[str, JsonValue]
    limits: Limits = Field(default_factory=Limits)


class ModelReply(Record):
    content: str
    input_tokens: int | None = None
    output_tokens: int | None = None
    cost: float | None = None


class ProviderFailure(Exception):
    """Public, secret-free error code; never carries provider response bodies."""


class ModelProvider(Protocol):
    def generate(
        self,
        system: str,
        user: str,
        schema: dict[str, JsonValue],
        max_tokens: int,
        timeout: float,
    ) -> ModelReply: ...


class CertificateVerifier(Protocol):
    def verify(self, graph: GraphInput, certificate: Certificate) -> bool: ...


class Experiment(Protocol):
    def evaluate(self, payload: dict[str, JsonValue]) -> dict[str, JsonValue]: ...


class RunStore(Protocol):
    def artifact(self, value: JsonValue) -> str: ...
    def cancelled(self, run_id: str) -> bool: ...


def canonical(value: object) -> str:
    if isinstance(value, BaseModel):
        value = value.model_dump(mode="json")
    return json.dumps(
        value, sort_keys=True, separators=(",", ":"), ensure_ascii=False, allow_nan=False
    )


def digest(value: object) -> str:
    return hashlib.sha256(canonical(value).encode("utf-8")).hexdigest()


def json_object(model: BaseModel) -> dict[str, JsonValue]:
    return model.model_dump(mode="json")
