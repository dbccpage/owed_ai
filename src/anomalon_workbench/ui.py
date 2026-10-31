"""Python-authored UI: narrative first, raw evidence one click away."""

from __future__ import annotations

import hashlib
import json
import os
import uuid
from dataclasses import replace
from pathlib import Path
from typing import Literal, cast

import streamlit as st
from pydantic import JsonValue, ValidationError

from . import graphs, ledger
from .cognition import review_receipt
from .domain import GraphInput, LedgerInput, RunSpec, canonical, digest, json_object
from .examples import graph_example, initial_prompt, ledger_example
from .providers import ProviderConfig, load_environment
from .service import parse_record, replay
from .storage import Store
from .worker import launch


def start_button(
    lab: Literal["ledger", "graph", "revision"],
    payload: dict[str, JsonValue],
    store: Store,
    provider: str,
    model: str,
) -> None:
    st.caption("Live generation · up to 12 requests · 5 minutes · 2,048 output tokens/request")
    if st.button("Run with live model", type="primary", key="run-" + lab):
        try:
            config = replace(
                ProviderConfig.from_env(provider, model),
                output_mode=cast(
                    Literal["json_prompt", "json_schema"],
                    st.session_state.get("output_mode", "json_prompt"),
                ),
            )
            spec = RunSpec(lab=lab, payload=payload)
            run_id = store.enqueue(uuid.uuid4().hex, json_object(spec), config.public())
            launch(store, run_id)
            st.session_state["selected_run"] = run_id
            st.success("Run started. Open Run inspector to follow progress and inspect the result.")
        except (ValueError, ValidationError, OSError):
            st.error(
                "Cannot start: check provider/model/key settings, input, and whether a run is already active."
            )


def ledger_page(store: Store, provider: str, model: str) -> None:
    st.title("01 / What does the evidence establish?")
    st.write(
        "A total of 100 can conceal a deficit. A checked total does not settle every question about its parts."
    )
    preset = st.selectbox("Observation", ["Total only", "B = 20", "B = −20"])
    actor = st.radio("Simulated actor", ["viewer", "operator"], horizontal=True)
    data = ledger_example({"Total only": None, "B = 20": 20, "B = −20": -20}[preset], actor)
    with st.expander("Edit evidence and scope"):
        raw = st.text_area(
            "Editable input · matching units and snapshots matter",
            json.dumps(json_object(data), indent=2),
            height=240,
            key="ledger-" + preset + actor,
        )
    try:
        edited = parse_record(raw, LedgerInput)
        result = ledger.evaluate(edited)
        st.subheader(result.verdict.value.replace("_", " ").title())
        a, b, c = st.columns(3)
        a.metric("Compatible states", result.compatible)
        b.metric("Support the claim", result.satisfying)
        c.metric("Refute the claim", result.falsifying)
        st.write("**Independently checked witnesses**")
        st.table(
            [
                {"Reserve A": a, "Reserve B": b, "Both nonnegative": a >= 0 and b >= 0}
                for a, b in result.witnesses
            ]
        )
        for obligation in result.obligations:
            st.info(
                f"{obligation.state.upper()}: {obligation.reason}. {obligation.evidence_needed}."
            )
        st.write(
            "**Simulated release:**", "Permitted" if result.authorization.allowed else "Denied"
        )
        st.caption(
            "Python finite checking only here. The independent Lean supplement is shown on Overview."
        )
        with st.expander("Accepted evidence, assumptions and full host evaluation"):
            st.json(json_object(result))
        start_button("ledger", json_object(edited), store, provider, model)
    except (ValueError, ValidationError):
        st.error(
            "Input is outside the supported ledger schema. No evaluation or release is accepted."
        )


def graph_page(store: Store, provider: str, model: str) -> None:
    st.title("02 / Can locally valid pieces fit together?")
    st.write(
        "A→B says +1. B→C says +1. A→C says +3. Each pair works; together they cannot describe one set of values."
    )
    with st.expander("Edit the synthetic constraints"):
        raw = st.text_area(
            "Exact difference constraints · only marked edges may be repaired",
            json.dumps(json_object(graph_example()), indent=2),
            height=300,
        )
    try:
        data = parse_record(raw, GraphInput)
        result = graphs.evaluate(data)
        st.subheader("Global consistency: " + result.verdict.value.replace("_", " "))
        st.write(result.reason)
        if result.certificate:
            st.json(json_object(result.certificate))
            st.caption(
                "Certificate independently checked: " + str(graphs.verify(data, result.certificate))
            )
        st.info(
            "A repair is a new synthetic constraint version. Original observations are never silently overwritten."
        )
        start_button("graph", json_object(data), store, provider, model)
    except (ValueError, ValidationError):
        st.error(
            "Malformed graph. Use at most eight named vertices and sixteen exact rational edges."
        )


def revision_page(store: Store, provider: str, model: str) -> None:
    st.title("03 / Can an agent improve without approving itself?")
    st.write(
        "Observe → revise → compare → review. Nine requests test a single child against its parent; ties and failures remain visible."
    )
    active = store.active_prompt()
    parent = active or json_object(initial_prompt())
    st.caption("Parent: " + digest(parent))
    with st.expander("Protected core", expanded=False):
        st.write(parent["core"])
    instructions = st.text_area(
        "Editable parent instructions", str(parent["instructions"]), height=140
    )
    if instructions != parent["instructions"]:
        parent = {
            **parent,
            "instructions": instructions,
            "parent_hash": digest(parent),
            "mutation": "operator instruction edit",
        }
    st.write(
        "Two development cases feed the revision. Two separate cases are withheld until the child is frozen."
    )
    st.info(
        "Passing makes a candidate eligible for review. Activation requires a separate operator decision in Run inspector."
    )
    start_button("revision", {"parent": parent}, store, provider, model)


def show_review(receipt: dict[str, JsonValue]) -> None:
    if "spec" not in receipt:
        return
    companion = review_receipt(receipt)
    audit = cast(dict[str, JsonValue], companion["review"])
    st.subheader("What deserves your attention?")
    st.write("**Question:**", audit["question"])
    st.write("**Checked result:**", audit["checked_result"])
    for signal in cast(list[dict[str, JsonValue]], audit["signals"]):
        st.warning(str(signal["detail"]))
    st.info("Next check: " + str(audit["next_check"]))
    with st.expander("Review scope and source binding"):
        st.json(companion)


@st.fragment(run_every="2s")
def inspector(store: Store) -> None:
    rows = store.list_runs()
    if not rows:
        st.info("No runs yet. Start a live lab or inspect an included replay bundle below.")
        return
    ids = [str(r["id"]) for r in rows]
    selected = str(st.session_state.get("selected_run", ids[0]))
    run_id = st.selectbox("Run", ids, index=ids.index(selected) if selected in ids else 0)
    row = store.get(run_id)
    st.write("**Execution:**", row["status"])
    events = store.events(run_id)
    st.caption(f"{len(events)} recorded progress events")
    if row["status"] in ("queued", "running"):
        if st.button("Cancel run"):
            store.cancel(run_id)
        st.caption(
            "Cancellation prevents new requests. An in-flight request may take up to 60 seconds to return."
        )
    if row["receipt_hash"]:
        receipt = store.read(str(row["receipt_hash"]))
        result = cast(dict[str, JsonValue], receipt["result"])
        show_review(receipt)
        with st.expander("Proposal, checked evidence and complete result"):
            st.json(result)
        calls = cast(list[dict[str, JsonValue]], receipt.get("calls", []))
        replies = [cast(dict[str, JsonValue], c["reply"]) for c in calls if "reply" in c]
        tokens = sum(
            int(cast(int, r.get("input_tokens") or 0)) + int(cast(int, r.get("output_tokens") or 0))
            for r in replies
        )
        costs = [r.get("cost") for r in replies]
        cost_label = "cost unknown or incomplete"
        if len(replies) == len(calls) and costs and all(c is not None for c in costs):
            cost_label = f"reported cost: ${sum(float(cast(float, c)) for c in costs):.6f} USD"
        st.caption(f"Requests: {len(calls)} · reported tokens: {tokens} · {cost_label}")
        bundle = {"sha256": digest(receipt), "receipt": receipt}
        st.download_button(
            "Export replay bundle",
            canonical(bundle),
            file_name=f"{run_id}.json",
            mime="application/json",
        )
        replay_key = "replay_checked:" + str(row["receipt_hash"])
        if row["status"] == "completed" and st.button("Verify offline replay"):
            st.session_state[replay_key] = replay(receipt)
        if replay_key in st.session_state:
            st.write("Semantic replay matched:", st.session_state[replay_key])
        if result.get("eligible") is True:
            operator = st.checkbox(
                "I am acting as the local operator and have reviewed this candidate"
            )
            if st.button("Admit candidate for subsequent runs", disabled=not operator):
                st.success("Admitted: " + store.admit(run_id, "operator"))
    with st.expander("Progress events"):
        st.json(events)


def overview() -> None:
    st.title("Owed")
    st.caption("The Accountable Agent Workbench · v0.0.1.0 · from Anomalon / Omega Engine")
    st.header("What did the agent establish—and what does it still owe?")
    st.write(
        "Three small experiments turn a research programme into observable behavior. Models propose; exact checkers inspect evidence; operators retain admission authority."
    )
    for title, body in [
        (
            "01 · Evidence",
            "The same total can hide different states. Find the observation that resolves the claim.",
        ),
        (
            "02 · Composition",
            "Locally satisfiable constraints can conflict globally. Inspect a concrete obstruction.",
        ),
        (
            "03 · Revision",
            "An agent can revise a prompt without becoming its own judge. Compare outcomes and ancestry.",
        ),
    ]:
        with st.container(border=True):
            st.subheader(title)
            st.write(body)
    st.write(
        "**Five-minute tour:** evidence → obstruction → revision → receipt. Start with the checked examples, then run your chosen live model."
    )
    st.caption(
        "Local single-user research software. Permission controls are simulated roles, not production authentication."
    )
    proof = Path("evidence/lean-verification.json")
    with st.expander("Formal supplement and research lineage"):
        st.write(
            "Genesis: preserved distinctions and explicit assumptions. LGGR: local/global consistency. PFP: proposals checked by the host. EIS: failure screening. PCIV: immutable ancestry. Governance: separate admission."
        )
        if proof.exists():
            report = json.loads(proof.read_text(encoding="utf-8"))
            current = all(
                (Path("lean") / name).exists()
                and hashlib.sha256((Path("lean") / name).read_bytes()).hexdigest() == expected
                for name, expected in report["source_sha256"].items()
            )
            st.write("Recorded proof sources match this checkout:", current)
            if not current:
                st.warning(
                    "The recorded proof check is stale for this checkout. Recheck before relying on it."
                )
            st.json(report)
            st.caption(
                "Recorded supplement check; independent of this run. Recheck with scripts/check_lean.py."
            )
        else:
            st.write("Lean supplement: not checked in this installation.")


def main() -> None:
    load_environment()
    st.set_page_config(
        page_title="Owed · Accountable Agent Workbench", page_icon="◈", layout="wide"
    )
    store = Store(Path(os.getenv("WORKBENCH_DATA_DIR", "data")))
    store.recover()
    with st.sidebar:
        st.title("◈ Owed")
        page = st.radio(
            "Workbench", ["Overview", "Evidence", "Composition", "Revision", "Run inspector"]
        )
        st.divider()
        names = ["openrouter", "anthropic", "compatible", "local"]
        configured = os.getenv("WORKBENCH_PROVIDER", "openrouter")
        provider = st.selectbox(
            "Provider", names, index=names.index(configured) if configured in names else 0
        )
        model = st.text_input("Explicit model ID", value=os.getenv("WORKBENCH_MODEL", ""))
        st.selectbox(
            "Output mode",
            ["json_schema", "json_prompt"],
            key="output_mode",
            help="Native JSON schema requires model support. JSON prompt mode also uses strict local validation.",
        )
        st.caption(
            "Credentials stay in your environment or ignored .env. No request is made until you start a run."
        )
    if page == "Overview":
        overview()
    elif page == "Evidence":
        ledger_page(store, provider, model)
    elif page == "Composition":
        graph_page(store, provider, model)
    elif page == "Revision":
        revision_page(store, provider, model)
    else:
        st.title("Run inspector")
        inspector(store)
        samples = sorted(Path("examples/live").glob("*/*.json"))
        if samples:
            with st.expander("Recorded live demonstrations · no API key needed"):
                sample = st.selectbox(
                    "Recorded lab", samples, format_func=lambda p: f"{p.parent.name} / {p.stem}"
                )
                bundle = json.loads(sample.read_text(encoding="utf-8"))
                st.caption(
                    f"Recorded {sample.parent.name} response; this is not a fresh live request."
                )
                show_review(bundle["receipt"])
                st.json(bundle["receipt"]["result"])
                if st.button("Verify recorded demonstration"):
                    st.write(
                        "Integrity and semantic replay matched:",
                        digest(bundle["receipt"]) == bundle["sha256"] and replay(bundle["receipt"]),
                    )
        uploaded = st.file_uploader("Verify an exported bundle without a model", type="json")
        if uploaded and st.button("Replay uploaded bundle"):
            try:
                bundle = json.loads(uploaded.getvalue())
                st.write(
                    "Integrity and replay matched:",
                    digest(bundle["receipt"]) == bundle["sha256"] and replay(bundle["receipt"]),
                )
            except (ValueError, KeyError, TypeError):
                st.error("Invalid or unsupported bundle.")
