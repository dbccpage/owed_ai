"""Guided synthetic migration presentation; all verification lives in services."""

from typing import cast

import streamlit as st

from .domain import canonical, digest
from .migration import Account, Scenario, evaluate, select_action, verify_witness
from .migration_demo import Mode, Receipt, SyntheticAuthority, export, fixture, replay, run
from .migration_proof import proof_status


def page() -> None:
    st.title("The total was right. The balances went to the wrong accounts.")
    st.write(
        "Migrate customer balances without changing their owners. Watch Owed find the missing evidence, repair the mapping, and check the actual database rows."
    )
    st.caption(
        "Synthetic customer accounts · computed locally now · no login or model API required"
    )
    start_requested = st.button("Run the migration challenge", type="primary")
    seed = int(st.session_state.get("migration_seed", 0))
    scenario, candidate, authority = fixture(seed)
    epoch = int(st.session_state.get("migration_epoch", 0))
    if epoch:
        scope = scenario.scope.model_copy(
            update={
                "snapshot": f"{scenario.scope.snapshot}-changed-{epoch}",
                "crosswalk": f"{scenario.scope.crosswalk}-changed-{epoch}",
            }
        )
        accounts = (
            Account(id=scenario.accounts[0].id, cents=scenario.accounts[0].cents + epoch),
            *scenario.accounts[1:],
        )
        scenario = Scenario(
            seed=seed, scope=scope, accounts=accounts, destinations=scenario.destinations
        )
    st.subheader("Task: keep each balance with its owner")
    left, right = st.columns(2)
    with left:
        st.write("**Source snapshot** · " + scenario.scope.snapshot)
        st.table(
            [{"Source account": a.id, "Balance (USD cents)": a.cents} for a in scenario.accounts]
        )
    with right:
        st.write("**Destination roster** · " + scenario.scope.roster)
        st.table([{"Destination account": d} for d in scenario.destinations])
    st.write(
        "The source and destination use different identifiers. The authoritative identity crosswalk has not been observed yet."
    )
    st.caption(
        f"Reproducible seed: {seed}. Negative balances are allowed; one currency, complete snapshots, bijections, 2–6 accounts only."
    )
    if len({a.cents for a in scenario.accounts}) < len(scenario.accounts):
        st.info(
            "Some balances are equal. An incorrect identity mapping can leave numeric rows unchanged; this alone does not demonstrate monetary harm."
        )
    with st.expander("Try another case or withhold evidence"):
        mode = cast(
            Mode,
            st.selectbox("Evidence availability", ["valid", "missing", "stale", "contradictory"]),
        )
        if st.button("Generate another reproducible case"):
            st.session_state["migration_seed"] = (seed + 1) % (2**32)
            st.session_state.pop("migration_receipt", None)
            st.session_state["migration_epoch"] = 0
            st.rerun()
        if st.button("Reset this session"):
            for key in list(st.session_state):
                if isinstance(key, str) and key.startswith("migration_"):
                    del st.session_state[key]
            st.rerun()
    if start_requested:
        st.session_state.pop("migration_replay", None)
        # Only preview and missing-distinction evaluation happen at this stage.
        st.session_state["migration_receipt"] = run(
            scenario, candidate, SyntheticAuthority(scenario, authority, mode), acquire=False
        )
    stored = st.session_state.get("migration_receipt")
    receipt = Receipt.model_validate_json(canonical(stored)) if stored is not None else None
    replay_result = st.session_state.get("migration_replay")
    if (
        receipt is None or not isinstance(replay_result, dict)
        or replay_result.get("receipt_digest") != digest(receipt)
        or type(replay_result.get("matched")) is not bool
    ):
        st.session_state.pop("migration_replay", None)
    if receipt is None:
        engineering()
        return
    if receipt.scenario != scenario:
        st.session_state.pop("migration_replay", None)
        st.warning(
            "Snapshot or crosswalk version changed. The receipt below remains history for its original scope; its admission is inapplicable here."
        )
        stale = evaluate(scenario, candidate, receipt.observations)
        st.write("Current ownership:", stale.ownership.value)
        st.write("Evidence dependency status:", list(stale.evidence_status))
        st.download_button(
            "Export historical receipt", export(receipt), "owed-history.json", "application/json"
        )
        return
    st.subheader("1. The supplied checks pass in a real SQLite preview")
    a, b = st.columns(2)
    a.metric("Total preserved", str(receipt.preview.total_preserved))
    b.metric("Row count preserved", str(receipt.preview.row_count_preserved))
    st.table([{"Destination": d, "Preview balance (cents)": c} for d, c in receipt.preview.rows])
    st.caption(
        "Deterministic fixture candidate, intentionally insufficient. This is not a retained LLM mistake or an industry benchmark."
    )
    st.subheader("2. Ownership is initially underdetermined")
    witness = receipt.initial.witness
    if witness:
        amount = next(a.cents for a in scenario.accounts if a.id == witness.source)
        first = next(p.destination for p in witness.first.links if p.source == witness.source)
        second = next(p.destination for p in witness.second.links if p.source == witness.source)
        st.write(
            f"Both mappings preserve every row and the same total. They send source {witness.source}'s {amount} cents to different accounts: {first} or {second}."
        )
        st.write(
            "Independent witness check:",
            verify_witness(scenario, receipt.initial_observations, witness),
        )
        st.table(
            [
                {
                    "Source": p.source,
                    "Mapping A": p.destination,
                    "Mapping B": next(
                        q.destination for q in witness.second.links if q.source == p.source
                    ),
                    "Affected": p.destination
                    != next(q.destination for q in witness.second.links if q.source == p.source),
                }
                for p in witness.first.links
            ]
        )
    st.subheader("3. Obtain evidence that can resolve the distinction")
    st.write(
        "Repeating the total query cannot distinguish these mappings. The next action is chosen from a finite menu using declared costs and deterministic tie-breaking."
    )
    action = select_action(scenario, receipt.observations)
    if action and len(receipt.steps) < 8:
        st.write(
            "Selected action:",
            action.kind,
            "· cost",
            action.cost,
            "· source",
            action.source or "all",
        )
        st.caption(
            "Lowest-cost informative action in the evaluated menu; not a globally optimal adaptive strategy."
        )
        if st.button("Obtain selected evidence and apply justified repair"):
            st.session_state["migration_receipt"] = run(
                scenario,
                candidate,
                SyntheticAuthority(scenario, authority, mode),
                prior=receipt,
                one_action=True,
            )
            st.rerun()
        if any(status == "stale" for status in receipt.final.evidence_status):
            if st.button("Refresh stale crosswalk from current authority"):
                st.session_state["migration_receipt"] = run(
                    scenario,
                    candidate,
                    SyntheticAuthority(scenario, authority),
                    prior=receipt,
                    one_action=True,
                )
                st.rerun()
    elif action:
        st.warning(
            "Eight evidence actions reached. Export this unresolved receipt and reset to try a new run."
        )
    if receipt.steps:
        status = receipt.final.evidence_status[-1]
        observation = receipt.steps[-1].observation
        st.write("Evidence response:", status, "· source:", observation.authority)
        if status == "unavailable":
            st.warning(
                "The source did not supply a correspondence. Ownership remains unresolved; no repair can be admitted."
            )
        elif status == "stale":
            st.warning(
                "The crosswalk belongs to another scope and was excluded. Refresh it for this snapshot."
            )
        elif status == "accepted":
            st.caption(
                "Accepted in this synthetic scenario: "
                + observation.scope.snapshot
                + " / "
                + observation.scope.crosswalk
            )
            st.table(
                [
                    {"Source account": p.source, "Authoritative destination": p.destination}
                    for p in observation.links
                ]
            )
    st.write("Original candidate ownership:", receipt.final.ownership.value)
    st.write("Remaining obligation:", receipt.final.obligation.explanation)
    if receipt.final.mismatch:
        st.warning(
            f"Candidate refuted: source {receipt.final.mismatch.source} belongs at {receipt.final.mismatch.destination} according to current accepted evidence."
        )
    if receipt.final.conflicts:
        st.error("Accepted correspondence records conflict. No repair is admitted.")
        st.write("Conflicting observation digests:", list(receipt.final.conflicts))
    if receipt.execution:
        st.subheader("4. Repaired, committed, and independently checked")
        if receipt.repaired:
            st.write(
                "Repaired plan ownership:",
                evaluate(scenario, receipt.repaired, receipt.observations).ownership.value,
            )
        st.table(
            [{"Destination": d, "Repaired balance (cents)": c} for d, c in receipt.execution.rows]
        )
        st.table(
            [
                {
                    "Property": {
                        "committed": "Transaction committed",
                        "total_preserved": "Total preserved",
                        "row_count_preserved": "Row count preserved",
                        "identity_coverage": "All destination identities covered",
                        "execution_conforms": "Database matches the admitted plan",
                        "ownership_preserved": "Per-account balances preserved",
                    }.get(key, key),
                    "Result": str(value),
                }
                for key, value in receipt.execution.model_dump().items()
                if key != "rows"
            ]
        )
        st.success(
            "Complete sandbox migration. Current evidence justifies the repaired correspondence and the committed rows match it."
        )
        st.caption(
            "Simulated operator admission binds the exact candidate, scenario, policy and evidence. This public action affects only a fresh temporary synthetic database."
        )
    st.subheader("5. Inspect or challenge the evidence")
    if st.button("Change snapshot and crosswalk version"):
        st.session_state.pop("migration_replay", None)
        st.session_state["migration_epoch"] = epoch + 1
        st.rerun()
    st.download_button(
        "Export replayable receipt", export(receipt), "owed-migration.json", "application/json"
    )
    if st.button("Replay this receipt offline"):
        st.session_state["migration_replay"] = {
            "receipt_digest": digest(receipt), "matched": replay(export(receipt))
        }
    if "migration_replay" in st.session_state:
        st.write("Offline semantic replay matched:", st.session_state["migration_replay"]["matched"])
    with st.expander("Plans, observations, obligations, admission and receipt"):
        st.caption(
            "Hashes detect content changes relative to the supplied digest. They do not authenticate a self-consistently rewritten bundle. Replay is never execution authority."
        )
        st.json(receipt.model_dump(mode="json"))
        st.code(digest(receipt))
    with st.expander("Replay an exported receipt without executing a migration"):
        raw = st.text_area("Receipt JSON (100 KB maximum)", max_chars=100000)
        if st.button("Check imported receipt"):
            try:
                st.write("Imported replay matched:", replay(raw))
            except (ValueError, TypeError, KeyError, RecursionError):
                st.error("Invalid, oversized or unsupported receipt. Nothing was executed.")
    engineering()


def engineering() -> None:
    with st.expander("Engineering behind the demo"):
        st.write(
            "Jeremy H. Carroll · Anomalon. Exact finite evidence checks, independent certificates, atomic SQLite execution and reproducible offline receipts."
        )
        st.link_button("Source and reproducible commands", "https://github.com/dbccpage/owed_ai")
        st.code(
            "uv run python scripts/migration_validation.py\nuv run pytest tests/test_migration.py -q\nuv run python scripts/check_migration_lean.py"
        )
        formal = proof_status()
        st.write(
            "Formal supplement:",
            "Verified during build"
            if formal["status"] == "verified_during_build"
            else "Not verified for this build",
        )
        st.json(formal)
        st.write(
            "Conservation is proved for finite reindexing; the counterexample separates ownership from totals; ownership follows conditionally from a bijective crosswalk and the inverse-lookup model. Runtime checks compare actual SQLite rows. This is not an end-to-end formal verification of Python or SQL."
        )
        st.link_button(
            "Theorem source",
            "https://github.com/dbccpage/owed_ai/blob/feat/migration-challenge/lean/Migration.lean",
        )
        st.caption(
            "Runs are session-local and temporary. Export receipts before leaving; the free deployment does not provide durable migration runs."
        )
