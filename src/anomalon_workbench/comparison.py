"""Independent, engineer-authored interval checklist; no call to the finite evaluator."""

from .domain import LedgerInput, Verdict


def checklist(data: LedgerInput) -> Verdict:
    lower, upper = -20, 100
    contradiction = False
    for obs in data.observations:
        if obs.snapshot != data.claim.snapshot:
            continue
        if (
            obs.units != data.claim.units
            or not obs.source.strip()
            or type(obs.value) is not (bool if obs.field == "b_nonnegative" else int)
        ):
            return Verdict.NOT_EVALUATED
        if obs.field == "total":
            contradiction |= obs.value != 100
        elif obs.field == "b":
            lower, upper = max(lower, int(obs.value)), min(upper, int(obs.value))
        elif obs.value:
            lower = max(lower, 0)
        else:
            upper = min(upper, -1)
    if contradiction or lower > upper:
        return Verdict.INCONSISTENT
    if lower >= 0:
        return Verdict.SUPPORTED
    if upper < 0:
        return Verdict.REFUTED
    return Verdict.UNDERDETERMINED
