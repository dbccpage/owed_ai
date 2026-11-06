"""Guided synthetic migration presentation; all verification lives in services."""

import os
import re
from html import escape
from pathlib import Path
from typing import cast

import streamlit as st
from streamlit.delta_generator import DeltaGenerator

from .domain import canonical, digest
from .migration import (
    Account,
    EvidenceAction,
    Plan,
    Scenario,
    compatible,
    evaluate,
    select_action,
    verify_witness,
)
from .migration_demo import (
    Mode,
    Receipt,
    SyntheticAuthority,
    export,
    fixture,
    investigation_timeline,
    record_probe,
    replay,
    run,
)
from .migration_proof import proof_status
from .migration_scene import alternatives_html, scene_html


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


STEPS = (
    "Meet the accounts",
    "Inspect the proposal",
    "Make your prediction",
    "Test the evidence",
    "Resolve the uncertainty",
    "Verify the result",
)
NAMES = ("Priya Shah", "Mateo Rivera", "Ava Chen", "Noah Brooks", "Leila Hassan", "Eli Park")
CHOICES = (
    "Check the total again",
    "Count the accounts again",
    "Request one identity record",
    "Request the full identity mapping",
    "Ask Owed to choose",
)


def clear_evidence_result() -> None:
    for key in (
        "migration_receipt",
        "migration_replay",
        "migration_phase",
        "migration_prediction",
        "migration_feedback",
        "migration_events",
        "migration_eliminated",
        "migration_report",
        "migration_reflection",
        "migration_error",
    ):
        st.session_state.pop(key, None)


def restart_walkthrough(consistent_records: bool = False) -> None:
    """Shared callback for main-scene recovery and navigation restart."""
    clear_evidence_result()
    if consistent_records:
        st.session_state["migration_mode"] = "valid"


def customer_names(scenario: Scenario) -> dict[str, str]:
    return dict(zip(sorted(a.id for a in scenario.accounts), NAMES))


def current_scenario() -> tuple[Scenario, Plan, Plan]:
    seed = int(st.session_state.get("migration_seed", 0))
    scenario, candidate, authority = fixture(seed)
    epoch = int(st.session_state.get("migration_epoch", 0))
    if epoch:
        scenario = Scenario(
            seed=seed,
            scope=scenario.scope.model_copy(
                update={
                    "snapshot": f"{scenario.scope.snapshot}-changed-{epoch}",
                    "crosswalk": f"{scenario.scope.crosswalk}-changed-{epoch}",
                }
            ),
            accounts=(
                Account(id=scenario.accounts[0].id, cents=scenario.accounts[0].cents + epoch),
                *scenario.accounts[1:],
            ),
            destinations=scenario.destinations,
        )
    return scenario, candidate, authority


def stored_receipt() -> Receipt | None:
    stored = st.session_state.get("migration_receipt")
    return Receipt.model_validate_json(canonical(stored)) if stored is not None else None


def investigation(choice: str, source: str = "", *, refresh: bool = False) -> None:
    """Choose only public requests; hidden correspondence stays in the authority adapter."""
    receipt = stored_receipt()
    if receipt is None:
        return
    scenario, candidate, authority = current_scenario()
    before = receipt.final.compatible_count
    mode = cast(Mode, st.session_state.get("migration_mode", "valid"))
    if choice in CHOICES[:2]:
        if len(receipt.investigations) >= 32:
            st.session_state["migration_error"] = (
                "32 informational probes reached. Export this investigation and restart."
            )
            return
        receipt = record_probe(receipt, "repeat_total" if choice == CHOICES[0] else "repeat_count")
        st.session_state["migration_receipt"] = receipt
        st.session_state.pop("migration_replay", None)
        value = (
            dollars(sum(c for _, c in receipt.preview.rows))
            if choice == CHOICES[0]
            else str(len(receipt.preview.rows))
        )
        report = f"{choice}: {value}. {before} possibilities remain; none eliminated. This repeats a conservation check and supplies no ownership information."
    else:
        selected = select_action(scenario, receipt.observations)
        requested = (
            EvidenceAction(kind="source", source=source, cost=2)
            if choice == CHOICES[2]
            else EvidenceAction(kind="full_crosswalk", cost=max(1, len(scenario.accounts) - 1))
            if choice == CHOICES[3] or refresh
            else None
        )
        action = requested or selected
        if action is None:
            return
        try:
            updated = run(
                scenario,
                candidate,
                SyntheticAuthority(scenario, authority, "valid" if refresh else mode),
                prior=receipt,
                one_action=True,
                requested_action=requested,
            )
        except ValueError as exc:
            if str(exc) != "evidence_response_contract":
                raise
            st.session_state["migration_error"] = (
                "Invalid identity response: it was empty, incomplete for the request, or contained "
                "unrequested records. No new identity evidence was accepted. The previous receipt "
                "is retained; retry with a source that satisfies the request."
            )
            st.session_state["migration_phase"] = 4
            return
        st.session_state.pop("migration_error", None)
        st.session_state["migration_receipt"] = updated
        st.session_state.pop("migration_replay", None)
        after = updated.final.compatible_count
        request = "one identity record" if action.kind == "source" else "the full identity mapping"
        who = "You requested" if requested else "Owed selected"
        report = f"{who} {request}. {before} → {after} possibilities; {before - after} eliminated."
        if updated.final.evidence_status[-1] != "accepted":
            report += " The returned records were not accepted for this snapshot."
        if not requested:
            report += f" Declared request cost: {action.cost}. Repeating totals is uninformative; Owed selects an informative request using the menu's costs."
    current_receipt = stored_receipt()
    st.session_state["migration_eliminated"] = (
        before - current_receipt.final.compatible_count if current_receipt else 0
    )
    st.session_state["migration_report"] = report
    events = list(st.session_state.get("migration_events", []))
    st.session_state["migration_events"] = [*events, report][-30:]
    st.session_state["migration_phase"] = 4


def primary_controls(panel: DeltaGenerator, receipt: Receipt | None, phase: int) -> None:
    """All primary transitions live here, independently of sidebar visibility."""
    with panel:
        if phase == 0:
            if st.button("Inspect the proposal", type="primary", width="stretch"):
                scenario, candidate, authority = current_scenario()
                mode = cast(Mode, st.session_state.get("migration_mode", "valid"))
                st.session_state["migration_receipt"] = run(
                    scenario,
                    candidate,
                    SyntheticAuthority(scenario, authority, mode),
                    acquire=False,
                )
                st.session_state["migration_phase"] = 1
                st.session_state.pop("migration_replay", None)
                st.rerun()
        elif phase == 1:
            if st.button("Make your prediction", type="primary", width="stretch"):
                st.session_state["migration_phase"] = 2
                st.rerun()
        elif phase == 2:
            prediction = st.radio(
                "Are these checks enough to approve the migration?",
                ["Yes", "No", "Not enough information"],
                index=None,
                key="migration_prediction",
            )
            if st.button(
                "Test my prediction", type="primary", disabled=prediction is None, width="stretch"
            ):
                st.session_state["migration_feedback"] = (
                    "You identified the missing justification. The total and account count establish conservation, but ownership is still unresolved."
                    if prediction != "Yes"
                    else "These checks establish conservation. They do not connect each balance to its owner, so approval is not justified yet."
                )
                st.session_state["migration_phase"] = 3
                st.rerun()
        elif receipt and receipt.execution:
            if phase < 5 and st.button("Verify the result", type="primary", width="stretch"):
                st.session_state["migration_phase"] = 5
                st.rerun()
            if phase == 5:
                answer = st.radio(
                    "What made proceeding justified?",
                    ["The matching total", "Evidence connecting balances to owners"],
                    index=None,
                    key="migration_reflection",
                )
                if answer:
                    st.caption(
                        "Exactly: identity evidence justified the repair; database checks verified its execution."
                        if answer != "The matching total"
                        else "The total was already right. Identity evidence resolved ownership, then the database checks verified the repair."
                    )
        elif receipt and receipt.final.conflicts:
            st.caption(
                "Conflicting identity records prevent a justified repair. Start a new run with consistent records."
            )
            st.button(
                "Restart with consistent records",
                type="primary",
                width="stretch",
                key="main_restart_consistent",
                on_click=restart_walkthrough,
                args=(True,),
            )
        elif receipt and len(receipt.steps) >= 8:
            st.caption("Eight evidence requests reached. Export this result, then restart.")
            st.button(
                "Restart the walkthrough",
                type="primary",
                width="stretch",
                key="main_restart_limit",
                on_click=restart_walkthrough,
            )
        elif receipt:
            choice = st.selectbox(
                "Choose what to investigate", CHOICES, index=4, key="migration_investigation"
            )
            names = customer_names(receipt.scenario)
            source = ""
            if choice == CHOICES[2]:
                source = st.selectbox(
                    "Whose identity record?",
                    sorted(names),
                    format_func=lambda s: names[s],
                    key="migration_source",
                )
            if st.button("Run this investigation", type="primary", width="stretch"):
                investigation(choice, source)
                st.rerun()
            if "stale" in receipt.final.evidence_status:
                if st.button("Refresh identity records", width="stretch"):
                    investigation(CHOICES[3], refresh=True)
                    st.rerun()


def controls(panel: DeltaGenerator, receipt: Receipt | None, phase: int) -> None:
    with panel:
        st.markdown(
            f'<div class="an-side-step"><div class="an-side-step__label">Journey · {phase + 1} / 6</div><div class="an-side-step__title">{STEPS[phase]}</div></div>',
            unsafe_allow_html=True,
        )
        st.progress((phase + 1) / 6)
        with st.expander("Scenario settings"):
            labels = {
                "valid": "Valid identity records",
                "missing": "Missing identity records",
                "stale": "Outdated identity records",
                "contradictory": "Conflicting identity records",
            }
            st.selectbox(
                "Choose an evidence scenario",
                list(labels),
                format_func=lambda v: labels[v],
                key="migration_mode",
                on_change=clear_evidence_result,
            )
            st.caption(
                "Fictional customers, synthetic records, temporary databases. No real accounts or model calls."
            )
            if st.button("Generate another reproducible case"):
                st.session_state["migration_seed"] = (
                    int(st.session_state.get("migration_seed", 0)) + 1
                ) % (2**32)
                st.session_state["migration_epoch"] = 0
                clear_evidence_result()
                st.rerun()
        st.button(
            "Restart the walkthrough",
            width="stretch",
            key="navigation_restart",
            on_click=restart_walkthrough,
        )
        if receipt:
            st.download_button(
                "Export replayable receipt",
                export(receipt),
                "owed-migration.json",
                "application/json",
                width="stretch",
            )
            if st.button("Replay this receipt offline", width="stretch"):
                st.session_state["migration_replay"] = {
                    "receipt_digest": digest(receipt),
                    "matched": replay(export(receipt)),
                }
            result = st.session_state.get("migration_replay")
            if isinstance(result, dict) and result.get("receipt_digest") == digest(receipt):
                st.caption(replay_message(result["matched"]))
                st.caption(
                    "Checks the recorded values and decisions; the original temporary database is no longer available."
                )


def replay_message(matched: bool) -> str:
    return (
        "Offline replay: recorded results are semantically consistent."
        if matched
        else "Offline replay: recorded results are not semantically consistent."
    )


def consequence_panel(receipt: Receipt, phase: int, names: dict[str, str]) -> str:
    """Keep the current ambiguity or correction beside the same account scene."""
    content = ""
    if receipt.final.witness:
        witness = receipt.final.witness
        if not verify_witness(receipt.scenario, receipt.observations, witness):
            raise ValueError("invalid_display_witness")
        amounts = {a.id: dollars(a.cents) for a in receipt.scenario.accounts}

        def assignment(plan: Plan) -> list[dict[str, str]]:
            return [
                {
                    "source": p.source,
                    "name": names[p.source],
                    "balance": amounts[p.source],
                    "destination": p.destination,
                }
                for p in plan.links
            ]

        content = (
            f"<h2>{receipt.final.compatible_count} assignments fit · two shown</h2>"
            '<p class="an-note">These observations fit both assignments. Owed cannot yet justify choosing one. Highlighted rows disagree.</p>'
            + alternatives_html(assignment(witness.first), assignment(witness.second))
            + '<p class="an-note">Both preserve the same total and account count.</p>'
        )
    elif receipt.execution:
        labels = {
            "committed": "Transaction committed",
            "total_preserved": "Total preserved",
            "row_count_preserved": "Account count preserved",
            "identity_coverage": "All identities covered",
            "execution_conforms": "Database matches the plan",
            "ownership_preserved": "Balances kept with owners",
        }
        if phase == 5:
            content = "<h2>The actual execution checks</h2>" + "".join(
                '<div class="an-check-row"><span>'
                + labels[k]
                + "</span><strong>"
                + ("Passed" if v else "Failed")
                + "</strong></div>"
                for k, v in receipt.execution.model_dump().items()
                if k != "rows"
            )
        elif receipt.repaired:
            original = {p.source: p.destination for p in receipt.original.links}
            content = '<h2>Evidence justified this correction</h2><p class="an-note">The same total, with ownership now established. Each reassignment follows accepted identity records and the one-to-one rule.</p>'
            content += "".join(
                '<div class="an-check-row"><strong>'
                + escape(names[p.source])
                + "</strong><span>"
                + escape(original[p.source])
                + " → "
                + escape(p.destination)
                + "</span></div>"
                for p in receipt.repaired.links
                if original[p.source] != p.destination
            )
            content += '<p class="an-note">Use Verify the result to inspect the actual database checks.</p>'
    elif receipt.final.conflicts:
        content = "<h2>Conflicting identity records</h2><p>Two accepted claims disagree. No assignment satisfies them both. Execution stays blocked; restart with a consistent source.</p>"
    if st.session_state.get("migration_report"):
        content += (
            '<p class="an-callout">' + escape(str(st.session_state["migration_report"])) + "</p>"
        )
    return (
        '<aside class="an-consequences" aria-label="Current evidence and consequences">'
        + content
        + "</aside>"
    )


def page(panel: DeltaGenerator | None = None) -> None:
    scenario, _, _ = current_scenario()
    receipt = stored_receipt()
    phase = int(st.session_state.get("migration_phase", 0))
    if receipt and receipt.scenario != scenario:
        st.warning(
            "Snapshot or crosswalk version changed. The receipt remains history for its original scope; restart to use the new snapshot."
        )
        receipt, phase = None, 0
    controls(panel if panel is not None else st.sidebar, receipt, phase)
    names = customer_names(scenario)
    st.markdown(
        '<div class="an-eyebrow">Anomalon / Owed · Interactive evidence lab</div>',
        unsafe_allow_html=True,
    )
    st.title("Move three customers’ balances into a new banking system.")
    st.write(
        "Can you keep everyone’s money with the right person? The new system uses different account IDs."
    )
    st.caption(
        "Interactive demo—no account required. Follow the next action below; settings and replay are in navigation."
    )
    journey = "".join(
        f'<li class="{"an-current" if i == phase else "an-done" if i < phase else ""}"'
        + (' aria-current="step"' if i == phase else "")
        + f">{label}</li>"
        for i, label in enumerate(STEPS)
    )
    st.markdown(
        '<ol class="an-journey" aria-label="Walkthrough progress">' + journey + "</ol>",
        unsafe_allow_html=True,
    )
    if receipt:
        st.write(
            "A proposed migration passed its financial checks. Owed must establish which customer owns each destination account before executing the repair."
        )
    primary_controls(st.container(border=True), receipt, phase)
    if st.session_state.get("migration_error"):
        st.error(str(st.session_state["migration_error"]))
    current = evaluate(scenario, receipt.original, receipt.observations) if receipt else None
    if receipt:
        established = f"Total {dollars(sum(c for _, c in receipt.preview.rows))} and {len(receipt.preview.rows)} accounts match"
        owed = (
            "No ownership obligation remains under the accepted evidence"
            if receipt.execution
            else "Resolve conflicting identity records"
            if receipt.final.conflicts
            else f"Identity evidence · {receipt.final.compatible_count} assignments remain"
        )
        if not receipt.execution and not receipt.final.conflicts:
            if receipt.final.evidence_status:
                latest = receipt.final.evidence_status[-1]
                if latest in ("unavailable", "stale", "invalid"):
                    owed = {
                        "unavailable": "Missing records",
                        "stale": "Outdated records excluded",
                        "invalid": "Invalid records excluded",
                    }[latest] + f" · {receipt.final.compatible_count} assignments remain"
            if "migration_eliminated" in st.session_state:
                owed += f" · {st.session_state['migration_eliminated']} eliminated by last check"
        execution = "Verified against SQLite (original run)" if receipt.execution else "Blocked"
    else:
        established, owed, execution = (
            "Source accounts supplied",
            "Inspect the proposed migration",
            "Not started",
        )
    st.markdown(
        '<div class="an-status'
        + (" an-status--ok" if receipt and receipt.execution else "")
        + '" role="status">'
        + "".join(
            "<div><strong>" + escape(k) + "</strong>" + escape(v) + "</div>"
            for k, v in (
                ("Established", established),
                ("Still owed", owed),
                ("Execution", execution),
            )
        )
        + "</div>",
        unsafe_allow_html=True,
    )
    states = compatible(scenario, receipt.observations) if receipt else ()
    owners = {}
    if receipt and states:
        for destination in scenario.destinations:
            possibilities = {
                p.source for state in states for p in state.links if p.destination == destination
            }
            if len(possibilities) == 1:
                owners[destination] = names[next(iter(possibilities))]
    sources = [
        {"id": a.id, "name": names[a.id], "balance": dollars(a.cents)}
        for a in sorted(scenario.accounts, key=lambda a: a.id)
    ]
    rows = dict(
        receipt.execution.rows
        if receipt and receipt.execution
        else receipt.preview.rows
        if receipt
        else ()
    )
    previous = dict(receipt.preview.rows) if receipt and receipt.execution else {}
    destinations = [
        {
            "id": d,
            "owner": owners.get(d, "Owner not established"),
            "balance": dollars(rows[d]) if d in rows else "Awaiting proposal",
            "balance_label": "Verified"
            if receipt and receipt.execution
            else "Proposed"
            if receipt
            else "",
            "previous": dollars(previous[d]) if d in previous and previous[d] != rows[d] else "",
        }
        for d in sorted(scenario.destinations)
    ]
    plan = (receipt.repaired or receipt.original) if receipt else None
    links = (
        [
            {
                "source": p.source,
                "destination": p.destination,
                "kind": "verified" if receipt and receipt.execution else "proposed",
            }
            for p in plan.links
        ]
        if plan
        else []
    )
    account_scene = scene_html(
        sources,
        destinations,
        links,
        title="Verified migration"
        if receipt and receipt.execution
        else "Proposed migration"
        if receipt
        else "Meet the accounts",
        caption="Solid connections and corrected balances follow accepted identity evidence and actual database checks."
        if receipt and receipt.execution
        else "Dashed connections show the proposal, not established ownership."
        if receipt
        else "These are fictional customers. New account ownership is concealed until evidence establishes it.",
    )
    if phase >= 3 and receipt:
        st.markdown(
            '<div class="an-workspace">'
            + account_scene
            + consequence_panel(receipt, phase, names)
            + "</div>",
            unsafe_allow_html=True,
        )
    else:
        st.markdown(account_scene, unsafe_allow_html=True)
    if len({a.cents for a in scenario.accounts}) < len(scenario.accounts):
        st.info(
            "Some balances are equal. An identity correction can leave the displayed amounts unchanged."
        )
    if phase == 1:
        st.info(
            "The total and account count match. Inspect the proposal, then make your prediction with the action above."
        )
    if phase == 2:
        st.subheader("Are these checks enough to approve the migration?")
        st.write("Choose an answer above before testing the evidence.")
    if phase >= 3 and current:
        feedback = st.session_state.get("migration_feedback")
        if feedback:
            st.info(str(feedback))
        if receipt and receipt.steps:
            latest = receipt.final.evidence_status[-1]
            if latest == "unavailable":
                st.warning(
                    "The source did not supply identity records. Ownership remains unresolved; execution is blocked. Retry the request or choose a different scenario."
                )
            elif latest == "stale":
                st.warning(
                    "These identity records belong to an older snapshot and were excluded. Refresh identity records to continue."
                )
            if receipt.final.conflicts:
                st.error(
                    "Resolve the conflicting identity records before proceeding. No repair is admitted; restart with a consistent source."
                )
            elif receipt.final.mismatch and not receipt.execution:
                st.warning(
                    "The accepted record contradicts part of the proposal. More records are needed to establish the complete repair."
                )
        if receipt and receipt.execution:
            st.success(
                "Identity evidence resolved the mapping. The corrected connections and balances above are verified against the resulting SQLite database."
            )
            if phase == 5:
                st.write(
                    "What made proceeding justified—the matching total, or the evidence connecting each balance to its owner?"
                )
                st.subheader("What Owed established in this run")
                st.table(
                    [
                        {
                            "Owed established": "Conservation",
                            "Evidence": "SQLite total and account-count checks",
                        },
                        {
                            "Owed established": "Initial ownership uncertainty",
                            "Evidence": f"{receipt.initial.compatible_count} compatible assignments; two checked alternatives"
                            if receipt.initial.witness
                            else receipt.initial.ownership.value,
                        },
                        {
                            "Owed established": "Effect of repeated checks",
                            "Evidence": f"{len(receipt.investigations)} recorded probes; none added identity evidence"
                            if receipt.investigations
                            else "No repeat probes requested in this run",
                        },
                        {
                            "Owed established": "Ownership mapping",
                            "Evidence": "Current accepted identity records and the declared one-to-one rule",
                        },
                        {
                            "Owed established": "Correct original execution",
                            "Evidence": "Committed transaction and row verification against SQLite",
                        },
                    ]
                )


def explanation_page() -> None:
    st.title("Why a correct total leaves something owed")
    st.write(
        "A total of $1,000 can be distributed among three new accounts in six different ways. Counting the accounts and repeating the total cannot tell us which destination belongs to each customer."
    )
    st.subheader("What Owed actually does")
    st.write(
        "Within a declared 2–6 account model, Owed enumerates one-to-one assignments consistent with the accepted identity records. If multiple assignments remain, two differing assignments witness the unresolved ownership question."
    )
    st.write(
        "You can request one record or the complete mapping. Owed can also choose from its finite menu: it excludes uninformative repeats and picks an informative request with the lowest declared cost, breaking ties deterministically. It does not optimize every possible sequence of future requests."
    )
    st.subheader("Why the stop matters")
    st.write(
        "Missing records add no ownership information. Outdated records are excluded. Conflicting records leave no consistent assignment. None authorizes a repair. Current consistent evidence must fix the mapping before a synthetic operator admission permits a new temporary SQLite execution."
    )
    st.caption(
        "The authority is supplied by the synthetic scenario. This demonstration does not discover real customer identities or establish general autonomous intelligence."
    )


def technical_page() -> None:
    st.title("Technical evidence and replay")
    receipt = stored_receipt()
    if receipt:
        st.write(
            "The current receipt records observations, who selected each request, the ambiguity witnesses, the admitted plan, and actual database checks."
        )
        st.download_button(
            "Export replayable receipt", export(receipt), "owed-migration.json", "application/json"
        )
        if st.button("Replay this receipt offline"):
            st.session_state["migration_replay"] = {
                "receipt_digest": digest(receipt),
                "matched": replay(export(receipt)),
            }
        result = st.session_state.get("migration_replay")
        if isinstance(result, dict) and result.get("receipt_digest") == digest(receipt):
            st.write(replay_message(result["matched"]))
            st.caption(
                "This checks the recorded results, not the occurrence of the original database event."
            )
        with st.expander("Plans, observations, obligations, admission and receipt"):
            st.json(receipt.model_dump(mode="json"))
        with st.expander("Investigation history"):
            st.table(investigation_timeline(receipt))
            st.caption(
                "Informational total/count probes are recorded separately and supply no identity evidence. Total probe values are integer USD cents."
            )
        if st.button("Change snapshot and crosswalk version"):
            st.session_state["migration_epoch"] = (
                int(st.session_state.get("migration_epoch", 0)) + 1
            )
            st.session_state.pop("migration_replay", None)
            st.warning(
                "Snapshot changed. The receipt remains history for its original scope; its admission is inapplicable to the new snapshot."
            )
    else:
        st.info("Start the guided migration to create a receipt.")
    with st.expander("Replay an exported receipt"):
        raw = st.text_area("Receipt JSON (100 KB maximum)", max_chars=100000)
        if st.button("Check imported receipt"):
            try:
                st.write(replay_message(replay(raw)))
            except (ValueError, TypeError, KeyError, RecursionError):
                st.error("Invalid, oversized or unsupported receipt. Nothing was executed.")
    engineering()


def engineering() -> None:
    with st.expander("Engineering behind the demo"):
        _render_engineering_contents()


def _render_engineering_contents() -> None:
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


_ONE_SCREEN_CSS = """
<style>
[data-testid="stMainBlockContainer"] {
  padding-top: 0.75rem !important;
  padding-bottom: 0.75rem !important;
  max-width: 1240px !important;
}
[data-testid="stMain"] h1 {
  font-size: 1.25rem !important;
  margin-bottom: 0.15rem !important;
  padding-top: 0 !important;
  padding-bottom: 0.15rem !important;
}
[data-testid="stMain"] h2, [data-testid="stMain"] h3 {
  font-size: 0.92rem !important;
  margin-top: 0.25rem !important;
  margin-bottom: 0.15rem !important;
  padding-top: 0 !important;
}
[data-testid="stMain"] p {
  font-size: 0.82rem !important;
  line-height: 1.35 !important;
  margin-bottom: 0.2rem !important;
}
</style>
"""


def _one_screen_page() -> None:
    st.markdown(_ONE_SCREEN_CSS, unsafe_allow_html=True)
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
    scenario, candidate, authority = current_scenario()
    epoch = int(st.session_state.get("migration_epoch", 0))

    if len({a.cents for a in scenario.accounts}) < len(scenario.accounts):
        st.info(
            "Some balances are equal. An incorrect identity mapping can leave numeric rows unchanged; this alone does not demonstrate monetary harm."
        )

    if start_requested:
        st.session_state.pop("migration_replay", None)
        st.session_state["migration_receipt"] = run(
            scenario, candidate, SyntheticAuthority(scenario, authority, mode), acquire=False
        )

    receipt = stored_receipt()
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
            _render_engineering_contents()
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
                for link in sorted(candidate.links, key=lambda item: item.destination)
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
            src_by_id = {a.id: a.cents for a in scenario.accounts}
            cand_by_dest = {link.destination: src_by_id[link.source] for link in candidate.links}
            auth_by_dest = {link.destination: src_by_id[link.source] for link in authority.links}
            auth_owner = {link.destination: link.source for link in authority.links}
            preview_diffs = ", ".join(
                f"{d}: {dollars(cand_by_dest[d])} -> {dollars(auth_by_dest[d])} (owner {auth_owner[d]}, {'changed' if cand_by_dest[d] != auth_by_dest[d] else 'unchanged'})"
                for d in sorted(scenario.destinations)
            )
            st.write(
                f"**Pending evidence acquisition (`{mode}`):** `{preview_diffs}` · **Source:** crosswalk `{scenario.scope.crosswalk}` vs candidate plan · **Rule:** `admit` & `execute` (`ownership_preserved`)."
            )
            st.caption(
                "Click 'Run the migration challenge' above to evaluate the candidate plan and inspect or repair the account rows."
            )

    with st.expander("More"):
        _render_more_controls(seed, epoch, scenario, receipt)
        _render_engineering_contents()


def _render_more_controls(
    seed: int, epoch: int, scenario: Scenario, receipt: Receipt | None
) -> None:
    import streamlit.components.v1 as components

    onepane = (Path(__file__).parent / "assets" / "onepane.html").read_text(encoding="utf-8")
    components.html(onepane, height=680, scrolling=True)
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
