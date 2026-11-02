"""Guided synthetic migration presentation; all verification lives in services."""

import os
import re
from typing import cast

import streamlit as st

from .domain import canonical, digest
from .migration import Account, Scenario, evaluate, select_action, verify_witness
from .migration_demo import Mode, Receipt, SyntheticAuthority, export, fixture, replay, run
from .migration_proof import proof_status


def dollars(cents: int) -> str:
    """Format integer cents without rounding or floating-point conversion."""
    whole, part = divmod(abs(cents), 100)
    return f"{'-' if cents < 0 else ''}${whole:,}" + (f".{part:02d}" if part else "")


def comparison(receipt: Receipt) -> list[dict[str, str]]:
    corrected = dict(receipt.execution.rows) if receipt.execution else {}
    return [
        {
            "Account": destination,
            "Proposed balance": dollars(cents),
            "Corrected balance": dollars(corrected[destination])
            if corrected
            else "Not established",
        }
        for destination, cents in sorted(receipt.preview.rows)
    ]


def source_commit() -> str | None:
    """Render's runtime metadata, never a guess from a receipt fingerprint."""
    value = os.getenv("RENDER_GIT_COMMIT", "")
    return value if re.fullmatch(r"[0-9a-f]{40}", value) else None


def clear_evidence_result() -> None:
    st.session_state.pop("migration_receipt", None)
    st.session_state.pop("migration_replay", None)


def page() -> None:
    st.title("The total was right. The balances went to the wrong accounts.")
    st.write(
        "Migrate customer balances without changing their owners. Watch Owed find the missing evidence, repair the mapping, and check the actual database rows."
    )
    st.caption("Interactive demo—no account required.")
    labels = {
        "valid": "Valid identity records · justify a repair",
        "missing": "Missing identity records · stop without enough evidence",
        "stale": "Outdated identity records · require a refresh",
        "contradictory": "Conflicting identity records · stop on a contradiction",
    }
    mode = cast(
        Mode,
        st.selectbox(
            "Choose an evidence scenario",
            list(labels),
            format_func=lambda value: labels[value],
            key="migration_mode",
            on_change=clear_evidence_result,
        ),
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
    st.write(
        "The migration must keep each balance with its owner. The old and new systems use "
        "different account IDs. A matching total cannot tell us which new account belongs to whom."
    )
    if len({a.cents for a in scenario.accounts}) < len(scenario.accounts):
        st.info(
            "Some balances are equal. An incorrect identity mapping can leave numeric rows unchanged; this alone does not demonstrate monetary harm."
        )
    with st.expander("Source accounts and additional cases"):
        st.table([{"Source account": a.id, "Balance": dollars(a.cents)} for a in scenario.accounts])
        st.caption(
            f"Seed {seed} · snapshot {scenario.scope.snapshot} · roster {scenario.scope.roster}. "
            "Synthetic USD accounts; negative balances allowed, complete snapshots, "
            "one-to-one mappings, 2–6 accounts."
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
        receipt is None
        or not isinstance(replay_result, dict)
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
    st.subheader("1. The total passes. Ownership needs evidence.")
    a, b = st.columns(2)
    a.metric("Total preserved", dollars(sum(c for _, c in receipt.preview.rows)))
    b.metric("Accounts preserved", str(len(receipt.preview.rows)))
    st.info("A correct total does not establish correct ownership.")
    st.table(comparison(receipt))
    if receipt.execution:
        corrected = dict(receipt.execution.rows)
        changed = sum(c != corrected[d] for d, c in receipt.preview.rows)
        total = dollars(sum(c for _, c in receipt.preview.rows))
        if changed == len(receipt.preview.rows):
            st.write(f"**Every balance was assigned incorrectly. Both versions total {total}.**")
        elif changed:
            st.write(
                f"**{changed} of {len(receipt.preview.rows)} balances changed. Both versions total {total}.**"
            )
        else:
            st.write(
                f"**The identity mapping changed, but the displayed balances did not. Both versions total {total}.**"
            )
    else:
        st.write(
            "Corrected balances are not established yet. Owed needs identity records linking the old accounts to the new ones."
        )
    witness = receipt.initial.witness
    if witness:
        with st.expander("Why the original checks cannot establish ownership"):
            st.caption(
                "Deterministic fixture candidate, intentionally insufficient. This is not a retained LLM mistake or an industry benchmark."
            )
            amount = next(a.cents for a in scenario.accounts if a.id == witness.source)
            first = next(p.destination for p in witness.first.links if p.source == witness.source)
            second = next(p.destination for p in witness.second.links if p.source == witness.source)
            st.write(
                f"Both mappings preserve every row and the same total. They send source {witness.source}'s {dollars(amount)} to different accounts: {first} or {second}."
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
                        != next(
                            q.destination for q in witness.second.links if q.source == p.source
                        ),
                    }
                    for p in witness.first.links
                ]
            )
    st.subheader("2. Check identity records before proceeding")
    st.write(
        "Identity records can establish who owns each new account. Missing, outdated or conflicting records cannot justify a repair."
    )
    action = select_action(scenario, receipt.observations)
    if action and len(receipt.steps) < 8:
        st.write(
            "Next: request identity records from the synthetic authority and check whether they justify a repair."
        )
        with st.expander("How the evidence request was selected"):
            st.write(
                "Selected action:",
                action.kind,
                "· cost",
                action.cost,
                "· source",
                action.source or "all",
            )
            st.caption(
                "Lowest-cost informative action in a finite menu with deterministic tie-breaking; not a globally optimal adaptive strategy. Repeating the total query cannot distinguish the mappings."
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
        if status == "unavailable":
            st.warning(
                "The source did not supply a correspondence. Ownership remains unresolved; no repair can be admitted."
            )
        elif status == "stale":
            st.warning(
                "The identity records belong to an older version and were excluded. Refresh them for this snapshot before proceeding."
            )
        elif status == "accepted":
            with st.expander("Accepted identity records"):
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
    if receipt.execution:
        st.write("**Original proposal: rejected.**")
        st.write("**Repaired proposal: verified against current evidence.**")
    elif receipt.final.conflicts:
        st.write("**Original proposal: blocked. No repair admitted.**")
    elif receipt.final.mismatch:
        st.write(
            "**Original proposal: rejected. More identity records are needed to justify a repair.**"
        )
    else:
        st.write("**Original proposal: not authorized. Ownership remains unresolved.**")
    if receipt.final.conflicts:
        st.error("Resolve the conflicting identity records before proceeding.")
    if receipt.execution:
        st.subheader("3. The repair is justified and the database matches")
        st.success(
            "Ownership is supported by the accepted identity records and checked against the resulting database."
        )
        with st.expander("All six execution checks and the admission boundary"):
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
            st.caption(
                "Simulated operator admission binds the exact candidate, scenario, policy and evidence. This public action affects only a fresh temporary synthetic database."
            )
    st.subheader("Inspect or replay this result")
    if st.button("Change snapshot and crosswalk version"):
        st.session_state.pop("migration_replay", None)
        st.session_state["migration_epoch"] = epoch + 1
        st.rerun()
    st.download_button(
        "Export replayable receipt", export(receipt), "owed-migration.json", "application/json"
    )
    if st.button("Replay this receipt offline"):
        st.session_state["migration_replay"] = {
            "receipt_digest": digest(receipt),
            "matched": replay(export(receipt)),
        }
    if "migration_replay" in st.session_state:
        st.write(
            "Offline semantic replay matched:", st.session_state["migration_replay"]["matched"]
        )
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
        commit = source_commit()
        if commit:
            st.markdown(
                f"Deployed Git commit: [{commit}](https://github.com/dbccpage/owed_ai/commit/{commit})"
            )
            st.caption(
                "Reported by Render runtime metadata; separate from the receipt's build fingerprint."
            )
        else:
            st.caption("Deployed Git commit: unavailable in this environment.")
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
            f"https://github.com/dbccpage/owed_ai/blob/{commit or 'main'}/lean/Migration.lean",
        )
        st.caption(
            "Runs are session-local and temporary. Export receipts before leaving; the free deployment does not provide durable migration runs."
        )
