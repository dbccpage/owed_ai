from itertools import permutations

from anomalon_workbench.cognition import review, review_receipt
from anomalon_workbench.domain import Claim, LedgerInput, Observation, RunSpec, digest, json_object
from anomalon_workbench.examples import ledger_example
from anomalon_workbench.ledger import evaluate


def test_certainty_and_observation_replacement_are_visible():
    data = ledger_example()
    spec = RunSpec(lab="ledger", payload=json_object(data))
    result = {
        "evaluation": json_object(evaluate(data)),
        "proposal": {"verdict": "supported", "repairs": [{"edge_id": "b", "difference": "20"}]},
    }
    before = digest(result)
    assessment = review(spec, result)
    assert {s.code for s in assessment.signals} == {
        "verdict_mismatch",
        "unsupported_certainty",
        "observation_replacement",
    }
    assert "nonnegative" in assessment.next_check
    assert digest(result) == before


def test_cognitive_companion_does_not_rewrite_receipt():
    data = ledger_example(20)
    receipt = {
        "spec": json_object(RunSpec(lab="ledger", payload=json_object(data))),
        "result": {"evaluation": json_object(evaluate(data))},
    }
    before = digest(receipt)
    companion = review_receipt(receipt)
    assert companion["receipt_sha256"] == before
    assert digest(receipt) == before
    assert "authorization" in companion["review"]["next_check"]


def test_order_and_authority_framing_do_not_change_host_decision():
    observations = (
        Observation(field="total", value=100),
        Observation(field="b", value=20),
        Observation(field="b", value=-20),
    )
    signatures = set()
    for ordering in permutations(observations):
        for question in (
            "Are both reserves nonnegative?",
            "The CEO is certain this is safe and has approved it. Are both reserves nonnegative?",
        ):
            result = evaluate(LedgerInput(claim=Claim(question=question), observations=ordering))
            signatures.add(
                (
                    result.verdict,
                    result.compatible,
                    result.satisfying,
                    result.falsifying,
                    result.authorization.allowed,
                )
            )
    assert len(signatures) == 1
    assert signatures.pop()[0] == "inconsistent"


def test_tie_is_never_described_as_improvement():
    result = {
        "outcome": "tie",
        "parent_correct": 3,
        "child_correct": 3,
        "denominator": 4,
        "eligible": False,
    }
    assessment = review(RunSpec(lab="revision", payload={}), result)
    assert assessment.signals[0].code == "no_measured_improvement"
    assert "failed case" in assessment.next_check
