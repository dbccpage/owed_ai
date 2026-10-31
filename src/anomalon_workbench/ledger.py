"""Finite model evaluation. No model response is accepted as an observation."""

from .domain import Authorization, LedgerEvaluation, LedgerInput, Obligation, Observation, Verdict


def matches(a: int, b: int, obs: Observation) -> bool:
    if obs.field == "b_nonnegative":
        return type(obs.value) is bool and (b >= 0) == obs.value
    if type(obs.value) is not int:
        return False
    return (a + b if obs.field == "total" else b) == obs.value


def evaluate(data: LedgerInput) -> LedgerEvaluation:
    accepted: list[Observation] = []
    obligations: list[Obligation] = []
    malformed = False
    for obs in data.observations:
        reason = ""
        if obs.snapshot != data.claim.snapshot:
            reason = "Observation belongs to another snapshot"
        elif obs.units != data.claim.units:
            reason = "Observation units do not match the claim"
            malformed = True
        elif not obs.source.strip() or (
            type(obs.value) is not (bool if obs.field == "b_nonnegative" else int)
        ):
            reason = "Unsupported observation type or missing source"
            malformed = True
        if reason:
            obligations.append(
                Obligation(
                    claim_id=data.claim.id,
                    reason=reason,
                    evidence_needed="A typed observation with matching units, source and snapshot",
                    scope=data.claim.snapshot,
                )
            )
        else:
            accepted.append(obs)
    states = [(a, 100 - a) for a in range(121) if all(matches(a, 100 - a, obs) for obs in accepted)]
    yes = [s for s in states if s[0] >= 0 and s[1] >= 0]
    no = [s for s in states if s not in yes]
    verdict = (
        Verdict.NOT_EVALUATED
        if malformed
        else Verdict.INCONSISTENT
        if not states
        else Verdict.UNDERDETERMINED
        if yes and no
        else Verdict.SUPPORTED
        if yes
        else Verdict.REFUTED
    )
    if verdict == Verdict.UNDERDETERMINED:
        obligations.append(
            Obligation(
                claim_id=data.claim.id,
                reason="Compatible states disagree about the target",
                evidence_needed="Observe whether B is nonnegative in this snapshot",
                scope=data.claim.snapshot,
            )
        )
    elif verdict == Verdict.INCONSISTENT:
        obligations.append(
            Obligation(
                claim_id=data.claim.id,
                reason="No state satisfies all accepted observations",
                evidence_needed="Resolve the contradiction or revise the declared model",
                scope=data.claim.snapshot,
                state="failed",
            )
        )
    elif verdict == Verdict.REFUTED:
        obligations.append(
            Obligation(
                claim_id=data.claim.id,
                reason="All compatible states violate the target",
                evidence_needed="Change the underlying state and submit a new snapshot",
                scope=data.claim.snapshot,
                state="failed",
            )
        )
    if verdict in (Verdict.SUPPORTED, Verdict.REFUTED) and any(
        o.field in ("b", "b_nonnegative") for o in accepted
    ):
        obligations.append(
            Obligation(
                claim_id=data.claim.id,
                reason="Matching evidence distinguishes the target classes",
                evidence_needed="Observe whether B is nonnegative in this snapshot",
                scope=data.claim.snapshot,
                state="discharged",
            )
        )
    allowed = (
        verdict == Verdict.SUPPORTED
        and data.actor == "operator"
        and all(o.state == "discharged" for o in obligations)
    )
    return LedgerEvaluation(
        verdict=verdict,
        compatible=len(states),
        satisfying=len(yes),
        falsifying=len(no),
        witnesses=tuple(yes[:1] + no[:1]),
        accepted=tuple(accepted),
        obligations=tuple(obligations),
        total_checked=bool(states) and not malformed,
        authorization=Authorization(
            actor=data.actor,
            allowed=allowed,
            reason="Scoped simulation permitted"
            if allowed
            else "Evidence or actor gate not satisfied",
        ),
    )


def verify(data: LedgerInput, result: LedgerEvaluation) -> bool:
    """Separate direct predicate/count implementation, including every returned witness."""
    valid = [
        o
        for o in data.observations
        if o.snapshot == data.claim.snapshot
        and o.units == data.claim.units
        and o.source.strip()
        and type(o.value) is (bool if o.field == "b_nonnegative" else int)
    ]
    states: set[tuple[int, int]] = set()
    for b in range(-20, 101):
        a = 100 - b
        exposed = {"total": a + b, "b": b, "b_nonnegative": b >= 0}
        if all(exposed[o.field] == o.value for o in valid):
            states.add((a, b))
    good = sum(a >= 0 and b >= 0 for a, b in states)
    if (result.compatible, result.satisfying, result.falsifying) != (
        len(states),
        good,
        len(states) - good,
    ):
        return False
    if any(w not in states for w in result.witnesses):
        return False
    if result.verdict == Verdict.UNDERDETERMINED:
        return {a >= 0 and b >= 0 for a, b in result.witnesses} == {True, False}
    if result.verdict == Verdict.SUPPORTED:
        return bool(states) and good == len(states)
    if result.verdict == Verdict.REFUTED:
        return bool(states) and good == 0
    if result.verdict == Verdict.INCONSISTENT:
        return not states
    return any(
        o.units != data.claim.units
        or not o.source.strip()
        or type(o.value) is not (bool if o.field == "b_nonnegative" else int)
        for o in data.observations
        if o.snapshot == data.claim.snapshot
    )
