"""Finite demo for the tuner loop: pin the right keys in a tiny cache.

Task. Twelve keys are read with a skewed (Zipf) frequency; the cache can pin
four. A run is a fresh 600-read segment of a recorded trace. Before each run
the loop proposes pin/swap changes, the evaluator replays the *previous* run's
segment to test each one, the policy authorizer approves changes that save at
least 1% of reads, and at most one approved change is applied per run (a
declared policy rule; the rest are deferred with their verdicts on record). Two error rates are
measured per run:

- task error: miss rate of the configuration in force during the run;
- proposal error: fraction of evaluated proposals the replay refuted.

Run the demo twice, with and without mistake memory, to show what memory buys:
the task error falls in both; the proposal error only stays down with memory,
because refuted swaps are otherwise re-proposed and re-refuted every run.

Outputs (``python -m anomalon_workbench.tuner_demo --out docs/engine``):
``demo_chart.svg``, ``demo_receipts.json`` (the full hash chain of the run
with memory) and ``demo_summary.json``. Standard library only.
"""

from __future__ import annotations

import argparse
import json
import random
from collections.abc import Mapping, Sequence
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from .tuner import (
    Candidate,
    Loop,
    Mistake,
    MistakeMemory,
    Policy,
    PolicyAuthorizer,
    ReceiptLog,
    Verdict,
    replay,
)

KEYS = 12
CAPACITY = 4
READS_PER_RUN = 600
RUNS = 8
MIN_IMPROVEMENT = 0.01


def zipf_trace(
    seed: int,
    runs: int = RUNS,
    reads: int = READS_PER_RUN,
    keys: int = KEYS,
    s: float = 1.1,
) -> list[list[int]]:
    rng = random.Random(seed)
    weights = [1.0 / ((k + 1) ** s) for k in range(keys)]
    order = list(range(keys))
    rng.shuffle(order)  # the hot keys are not simply 0..3
    return [
        [order[rng.choices(range(keys), weights=weights)[0]] for _ in range(reads)]
        for _ in range(runs)
    ]


def misses(pinned: frozenset[int], segment: Sequence[int]) -> int:
    return sum(1 for k in segment if k not in pinned)


@dataclass
class CacheState:
    pinned: frozenset[int] = frozenset()
    pinned_at_run_start: frozenset[int] = frozenset()
    last_segment: list[int] = field(default_factory=list)

    def context(self) -> dict[str, Any]:
        counts: dict[str, int] = {}
        for key in self.last_segment:
            counts[str(key)] = counts.get(str(key), 0) + 1
        return {"pinned": sorted(self.pinned), "last_counts": counts}

    def to_json(self) -> dict[str, Any]:
        return {"pinned": sorted(self.pinned)}


class ToggleProposer:
    """Propose pinning each unpinned key, swapping it in when the cache is full.

    Candidates are ordered by how often the key was read in the last segment, so
    when two approved changes conflict the more valuable one is applied first.
    The proposer only guesses; the evaluator and the policy decide.
    """

    name = "toggle-proposer"

    def propose(self, context: Mapping[str, Any]) -> Sequence[Candidate]:
        pinned: frozenset[int] = frozenset(context["pinned"])
        counts: Mapping[str, int] = context.get("last_counts", {})
        keys = sorted(
            (k for k in range(KEYS) if k not in pinned),
            key=lambda k: -counts.get(str(k), 0),
        )
        out: list[Candidate] = []
        for key in keys:
            if len(pinned) < CAPACITY:
                out.append(Candidate("pin", {"key": key}, self.name, f"pin {key}"))
            else:
                for victim in sorted(pinned, key=lambda k: counts.get(str(k), 0)):
                    out.append(
                        Candidate(
                            "swap",
                            {"key_in": key, "key_out": victim},
                            self.name,
                            f"swap {victim} out for {key}",
                        )
                    )
        return out


def apply_candidate(pinned: frozenset[int], candidate: Candidate) -> frozenset[int]:
    """Return the configuration after ``candidate``; raise when it no longer applies."""
    if candidate.kind == "pin":
        key = int(candidate.payload["key"])
        if key in pinned or len(pinned) >= CAPACITY:
            raise RuntimeError(f"pin {key} no longer applies to {sorted(pinned)}")
        return pinned | {key}
    if candidate.kind == "swap":
        key_in, key_out = int(candidate.payload["key_in"]), int(
            candidate.payload["key_out"]
        )
        if key_in in pinned or key_out not in pinned:
            raise RuntimeError(
                f"swap {key_out}->{key_in} no longer applies to {sorted(pinned)}"
            )
        return (pinned - {key_out}) | {key_in}
    raise ValueError(f"unknown candidate kind {candidate.kind!r}")


class ReplayEvaluator:
    """Replay the last recorded segment under the current and the candidate configuration."""

    name = "replay-evaluator"

    def evaluate(self, candidate: Candidate, history: Any) -> Verdict:
        state: CacheState = history
        segment = state.last_segment
        if len(segment) < 50:
            return Verdict(
                "underdetermined",
                self.name,
                f"only {len(segment)} recorded reads",
                {"reads": len(segment)},
            )
        before = misses(state.pinned_at_run_start, segment)
        after = misses(apply_candidate(state.pinned_at_run_start, candidate), segment)
        improvement = (before - after) / len(segment)
        evidence = {
            "reads": len(segment),
            "pinned_before": sorted(state.pinned_at_run_start),
            "misses_before": before,
            "misses_after": after,
            "improvement": improvement,
        }
        if improvement >= MIN_IMPROVEMENT:
            return Verdict(
                "supported",
                self.name,
                f"saves {before - after} of {len(segment)} reads",
                evidence,
            )
        return Verdict(
            "refuted",
            self.name,
            f"saves {before - after} reads, below {MIN_IMPROVEMENT:.0%}",
            evidence,
        )


def verify_receipts(
    log: ReceiptLog, trace: Sequence[Sequence[int]]
) -> list[dict[str, Any]]:
    """Independently recompute every ``evaluated`` receipt's evidence from the recorded trace.

    Returns one entry per receipt whose claimed verdict or numbers disagree with a
    direct recount. This is the check that catches an evaluator that lies, and it
    uses only receipts plus the recorded history, never the evaluator itself.
    """
    log.require_intact()
    mismatches: list[dict[str, Any]] = []
    for receipt in log:
        if receipt.step != "evaluated":
            continue
        label = str(receipt.body.get("run", ""))
        run_index = (
            int(label.split("-")[-1])
            if label.startswith("run-") and label[4:].isdigit()
            else -1
        )
        segment = trace[run_index - 1] if 0 < run_index <= len(trace) else []
        verdict = receipt.body["verdict"]
        evidence = verdict.get("evidence", {})
        candidate = Candidate(
            receipt.body["candidate"]["kind"],
            receipt.body["candidate"]["payload"],
            "replayed",
        )
        problem = ""
        if run_index < 0:
            problem = "receipt has no run label, so its history segment cannot be found"
        elif not isinstance(evidence.get("pinned_before"), list):
            problem = "evidence lacks the configuration it was evaluated against"
        else:
            pinned = frozenset(int(k) for k in evidence["pinned_before"])
            try:
                after = misses(apply_candidate(pinned, candidate), segment)
            except RuntimeError as exc:
                problem = f"candidate did not apply: {exc}"
            else:
                before = misses(pinned, segment)
                improvement = (before - after) / len(segment) if segment else 0.0
                expected = "supported" if improvement >= MIN_IMPROVEMENT else "refuted"
                if len(segment) < 50:
                    expected = "underdetermined"
                if (before, after) != (
                    evidence.get("misses_before"),
                    evidence.get("misses_after"),
                ) or expected != verdict["status"]:
                    problem = f"recount gives {expected} ({before}->{after}); receipt says {verdict['status']}"
        if problem:
            mismatches.append(
                {
                    "seq": receipt.seq,
                    "candidate_id": receipt.candidate_id,
                    "problem": problem,
                }
            )
    return mismatches


class NullMemory(MistakeMemory):
    """A memory that forgets everything: the ablation for the demo."""

    def remember(self, mistake: Mistake) -> None:
        return None


@dataclass
class DemoResult:
    label: str
    task_error: list[float]
    proposal_error: list[float]
    proposals: list[int]
    skipped: list[int]
    applied: list[int]
    apply_failed: list[int]
    final_pinned: list[int]
    log: ReceiptLog

    def to_json(self) -> dict[str, Any]:
        return {
            "label": self.label,
            "task_error": self.task_error,
            "proposal_error": self.proposal_error,
            "proposals": self.proposals,
            "skipped_known_mistakes": self.skipped,
            "applied": self.applied,
            "apply_failed": self.apply_failed,
            "final_pinned": self.final_pinned,
            "receipts": len(self.log),
            "receipt_head": self.log.head,
            "chain_intact": self.log.verify() == -1,
        }


def run_demo(seed: int = 7, with_memory: bool = True, runs: int = RUNS) -> DemoResult:
    trace = zipf_trace(seed, runs=runs)
    state = CacheState()
    policy = Policy(
        "demo/auto-approve-pins",
        auto_approve_kinds=frozenset({"pin", "swap"}),
        min_improvement=MIN_IMPROVEMENT,
        max_applied_per_run=1,
    )
    loop = Loop(
        ToggleProposer(),
        ReplayEvaluator(),
        PolicyAuthorizer(),
        policy,
        memory=None if with_memory else NullMemory(),
    )
    result = DemoResult(
        "with memory" if with_memory else "no memory",
        [],
        [],
        [],
        [],
        [],
        [],
        [],
        loop.log,
    )

    for run_index, segment in enumerate(trace):
        if run_index > 0:
            state.pinned_at_run_start = state.pinned

            def apply(candidate: Candidate) -> Mapping[str, Any]:
                state.pinned = apply_candidate(
                    state.pinned, candidate
                )  # refuses conflicting changes
                return state.to_json()

            summary = loop.run_once(
                state.context(), state, apply=apply, run_label=f"run-{run_index}"
            )
            result.proposals.append(summary.proposed)
            result.skipped.append(summary.skipped_known_mistakes)
            result.applied.append(summary.applied)
            result.apply_failed.append(summary.apply_failed)
            result.proposal_error.append(summary.proposal_error_rate)
        else:
            result.proposals.append(0)
            result.skipped.append(0)
            result.applied.append(0)
            result.apply_failed.append(0)
            result.proposal_error.append(0.0)
        result.task_error.append(misses(state.pinned, segment) / len(segment))
        state.last_segment = list(segment)
    result.final_pinned = sorted(state.pinned)
    return result


def _polyline(
    values: Sequence[float], x0: float, y0: float, w: float, h: float, ymax: float
) -> str:
    n = max(len(values) - 1, 1)
    pts = [
        f"{x0 + i * w / n:.1f},{y0 + h - (v / ymax) * h:.1f}"
        for i, v in enumerate(values)
    ]
    return " ".join(pts)


def render_chart(results: Sequence[DemoResult]) -> str:
    """Two line panels (task error, proposal error) per run, one line per result."""
    width, panel_w, panel_h, left, top, gap = 760, 300, 200, 60, 40, 80
    colours = ["#1f77b4", "#d62728", "#2ca02c"]
    panels = [
        ("Task error (miss rate)", "task_error"),
        ("Proposal error (refuted / evaluated)", "proposal_error"),
    ]
    parts = [
        f'<svg xmlns="http://www.w3.org/2000/svg" width="{width}" height="{panel_h + top + 90}" font-family="sans-serif" font-size="12">',
        f'<rect width="{width}" height="{panel_h + top + 90}" fill="white"/>',
    ]
    for p, (title, attr) in enumerate(panels):
        x0 = left + p * (panel_w + gap)
        y0 = top
        parts.append(
            f'<text x="{x0}" y="{y0 - 14}" font-size="14" font-weight="bold">{title}</text>'
        )
        parts.append(
            f'<rect x="{x0}" y="{y0}" width="{panel_w}" height="{panel_h}" fill="none" stroke="#888"/>'
        )
        for frac in (0.0, 0.5, 1.0):
            y = y0 + panel_h - frac * panel_h
            parts.append(
                f'<line x1="{x0}" y1="{y:.1f}" x2="{x0 + panel_w}" y2="{y:.1f}" stroke="#ddd"/>'
            )
            parts.append(
                f'<text x="{x0 - 8}" y="{y + 4:.1f}" text-anchor="end">{frac:.1f}</text>'
            )
        runs = len(results[0].task_error) if results else 0
        for i in range(runs):
            x = x0 + i * panel_w / max(runs - 1, 1)
            parts.append(
                f'<text x="{x:.1f}" y="{y0 + panel_h + 16}" text-anchor="middle">{i}</text>'
            )
        parts.append(
            f'<text x="{x0 + panel_w / 2:.1f}" y="{y0 + panel_h + 34}" text-anchor="middle">run</text>'
        )
        for c, res in enumerate(results):
            values: list[float] = getattr(res, attr)
            parts.append(
                f'<polyline points="{_polyline(values, x0, y0, panel_w, panel_h, 1.0)}" fill="none" '
                f'stroke="{colours[c % len(colours)]}" stroke-width="2"/>'
            )
            for i, v in enumerate(values):
                x = x0 + i * panel_w / max(len(values) - 1, 1)
                y = y0 + panel_h - v * panel_h
                parts.append(
                    f'<circle cx="{x:.1f}" cy="{y:.1f}" r="3" fill="{colours[c % len(colours)]}"/>'
                )
    for c, res in enumerate(results):
        y = top + panel_h + 58 + c * 16
        parts.append(
            f'<line x1="{left}" y1="{y}" x2="{left + 24}" y2="{y}" stroke="{colours[c % len(colours)]}" stroke-width="2"/>'
        )
        parts.append(
            f'<text x="{left + 30}" y="{y + 4}">{res.label}: final miss rate {res.task_error[-1]:.3f}, final pins {res.final_pinned}</text>'
        )
    parts.append("</svg>")
    return "\n".join(parts)


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--out", type=Path, default=Path("docs/engine"))
    parser.add_argument("--seed", type=int, default=7)
    args = parser.parse_args(argv)
    with_memory = run_demo(args.seed, with_memory=True)
    no_memory = run_demo(args.seed, with_memory=False)
    args.out.mkdir(parents=True, exist_ok=True)
    (args.out / "demo_chart.svg").write_text(
        render_chart([with_memory, no_memory]), encoding="utf-8"
    )
    (args.out / "demo_receipts.json").write_text(
        with_memory.log.dumps(), encoding="utf-8"
    )
    summary = {
        "seed": args.seed,
        "keys": KEYS,
        "capacity": CAPACITY,
        "reads_per_run": READS_PER_RUN,
        "results": [with_memory.to_json(), no_memory.to_json()],
        "replay_of_memory_run": replay(with_memory.log),
    }
    (args.out / "demo_summary.json").write_text(
        json.dumps(summary, indent=1, sort_keys=True), encoding="utf-8"
    )
    for res in (with_memory, no_memory):
        print(f"{res.label:12s} task error {[round(v, 3) for v in res.task_error]}")
        print(f"{'':12s} proposal error {[round(v, 3) for v in res.proposal_error]}")
        print(
            f"{'':12s} proposed {res.proposals} skipped {res.skipped} applied {res.applied} refused {res.apply_failed}"
        )
    print(
        f"receipts: {len(with_memory.log)} (chain intact: {with_memory.log.verify() == -1})"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
