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
    st.caption(
        "Interactive demo—no account required. Migrate customer balances without changing their owners: check the claim, see which check fails, price the missing crosswalk, ask the authority, and verify the repaired rows."
    )
    labels = {
        "valid": "Valid identity records · justify a repair",
        "missing": "Missing identity records · stop without enough evidence",
        "stale": "Outdated identity records · require a refresh",
        "contradictory": "Conflicting identity records · stop on a contradiction",
    }
    top_left, top_right = st.columns([3, 1])
    with top_left:
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
    with top_right:
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

    if len({a.cents for a in scenario.accounts}) < len(scenario.accounts):
        st.info(
            "Some balances are equal. An incorrect identity mapping can leave numeric rows unchanged; this alone does not demonstrate monetary harm."
        )

    if start_requested:
        st.session_state.pop("migration_replay", None)
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

    if receipt is not None and receipt.scenario != scenario:
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
        with st.expander("More"):
            _render_more_controls(seed, epoch, scenario, receipt)
            engineering()
        return

    source_summary = ", ".join(
        f"{a.id}={dollars(a.cents)}" for a in sorted(scenario.accounts, key=lambda x: x.id)
    )
    total_cents = sum(a.cents for a in scenario.accounts)
    action = select_action(scenario, receipt.observations if receipt else ())
    action_cost = action.cost if action else max(1, len(scenario.accounts) - 1)
    action_kind = action.kind if action else "full_crosswalk"

    col_left, col_right = st.columns([5, 7])

    with col_left:
        st.subheader("1. The claim: the total is right")
        st.write(
            f"**Total preserved:** `{dollars(total_cents)}` across `{len(scenario.accounts)}` accounts. "
            f"**Source:** ledger rows `{source_summary}` · **Rule:** `total_preserved` & `row_count_preserved`."
        )

        st.subheader("2. The check that fails: which balances, which accounts")
        st.info("A correct total does not establish correct ownership.")
        if receipt is not None:
            proposed_summary = ", ".join(
                f"{dest}={dollars(c)}" for dest, c in sorted(receipt.preview.rows)
            )
            compat_count = receipt.initial.compatible_count
        else:
            src_by_id = {a.id: a.cents for a in scenario.accounts}
            proposed_summary = ", ".join(
                f"{link.destination}={dollars(src_by_id[link.source])} (from {link.source})"
                for link in sorted(candidate.links, key=lambda l: l.destination)
            )
            compat_count = evaluate(scenario, candidate, ()).compatible_count
        st.write(
            f"**Check failed:** `ownership_preserved` is `underdetermined` ({compat_count} permutations share total `{dollars(total_cents)}`). "
            f"**Source:** candidate rows `{proposed_summary}` · **Rule:** `evaluate` (`ownership_preserved`)."
        )

        st.subheader("3. What the machine does not know and what it would cost to find out")
        st.write(
            f"**Unknown:** authoritative account-identity crosswalk for scope `{scenario.scope.snapshot}` / `{scenario.scope.roster}` / `{scenario.scope.crosswalk}`. "
            f"**Cost:** `{action_kind}` costs `{action_cost}` (`repeat_total` costs `0` but cannot distinguish mappings; single-account lookup costs `2`) · **Source:** action menu over `{compat_count}` compatible states · **Rule:** `select_action`."
        )

        st.subheader("4. The question it asks")
        st.write(
            f"**Question to authority (`synthetic-source/v1`):** supply `{action_kind}` correspondence linking `{', '.join(sorted(a.id for a in scenario.accounts))}` to `{', '.join(sorted(scenario.destinations))}` for snapshot `{scenario.scope.snapshot}` and crosswalk `{scenario.scope.crosswalk}` · **Source:** scope `{scenario.scope.snapshot}/{scenario.scope.crosswalk}` · **Rule:** `response_matches_action` & `evidence_status`."
        )
        if receipt is not None:
            if action and len(receipt.steps) < 8:
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

    with col_right:
        st.subheader("5. The corrected result with the rows that changed")
        if receipt is not None:
            st.table(comparison(receipt))
            if receipt.execution:
                corrected = dict(receipt.execution.rows)
                changed = sum(c != corrected[d] for d, c in receipt.preview.rows)
                total = dollars(sum(c for _, c in receipt.preview.rows))
                if changed == len(receipt.preview.rows):
                    st.write(
                        f"**Every balance was assigned incorrectly. Both versions total {total}.**"
                    )
                elif changed:
                    st.write(
                        f"**{changed} of {len(receipt.preview.rows)} balances changed. Both versions total {total}.**"
                    )
                else:
                    st.write(
                        f"**The identity mapping changed, but the displayed balances did not. Both versions total {total}.**"
                    )
                repaired_links = (
                    {link.destination: link.source for link in receipt.repaired.links}
                    if receipt.repaired
                    else {}
                )
                row_diffs = ", ".join(
                    f"{d}: {dollars(c)} -> {dollars(corrected[d])} (owner {repaired_links.get(d, '?')}, {'changed' if c != corrected[d] else 'unchanged'})"
                    for d, c in sorted(receipt.preview.rows)
                )
                st.write(
                    f"**Rows changed:** `{row_diffs}` · **Source:** accepted crosswalk `{scenario.scope.crosswalk}` · **Rule:** `admit` & `execute` (`ownership_preserved = True`)."
                )
            else:
                st.write(
                    "Corrected balances are not established yet. Owed needs identity records linking the old accounts to the new ones."
                )

            if receipt.steps:
                status = receipt.final.evidence_status[-1]
                if status == "unavailable":
                    st.warning(
                        "The source did not supply a correspondence. Ownership remains unresolved; no repair can be admitted."
                    )
                elif status == "stale":
                    st.warning(
                        "The identity records belong to an older version and were excluded. Refresh them for this snapshot before proceeding."
                    )

            if receipt.execution:
                st.write(
                    "**Original proposal: rejected.** **Repaired proposal: verified against current evidence.**"
                )
                st.success(
                    "Ownership is supported by the accepted identity records and checked against the resulting database."
                )
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
            if "migration_replay" in st.session_state:
                st.write(
                    "Offline semantic replay matched:",
                    st.session_state["migration_replay"]["matched"],
                )
        else:
            st.caption(
                "Click 'Run the migration challenge' above to evaluate the candidate plan and inspect or repair the account rows."
            )

    with st.expander("More"):
        _render_more_controls(seed, epoch, scenario, receipt)
        engineering()


def _render_more_controls(
    seed: int, epoch: int, scenario: Scenario, receipt: Receipt | None
) -> None:
    st.markdown("**Source accounts and session controls**")
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

    if receipt is None:
        return

    witness = receipt.initial.witness
    if witness:
        st.markdown("**Why the original checks cannot establish ownership**")
        st.caption(
            "Deterministic fixture candidate, intentionally insufficient. This is not a retained model mistake or an industry benchmark."
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

    if receipt.steps and receipt.final.evidence_status[-1] == "accepted":
        observation = receipt.steps[-1].observation
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
        st.markdown("**All six execution checks and the admission boundary**")
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

    st.markdown("**Inspect or replay this result**")
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
        st.rerun()
    st.caption(
        "Hashes detect content changes relative to the supplied digest. They do not authenticate a self-consistently rewritten bundle. Replay is never execution authority."
    )
    st.json(receipt.model_dump(mode="json"))
    st.code(digest(receipt))
    raw = st.text_area("Receipt JSON (100 KB maximum)", max_chars=100000)
    if st.button("Check imported receipt"):
        try:
            st.write("Imported replay matched:", replay(raw))
        except (ValueError, TypeError, KeyError, RecursionError):
            st.error("Invalid, oversized or unsupported receipt. Nothing was executed.")


def engineering() -> None:
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
        "Conservation is checked in Lean for finite reindexing; the counterexample separates ownership from totals; ownership follows conditionally from a bijective crosswalk and the inverse-lookup model. Runtime checks compare actual SQLite rows. This is not an end-to-end formal verification of Python or SQL."
    )
    st.link_button(
        "Theorem source",
        f"https://github.com/dbccpage/owed_ai/blob/{commit or 'main'}/lean/Migration.lean",
    )
    st.caption(
        "Runs are session-local and temporary. Export receipts before leaving; the free deployment does not provide durable migration runs."
    )
