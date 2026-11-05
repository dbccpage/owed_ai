# `anomalon_workbench.migration`

Source: `src/anomalon_workbench/migration.py`

Bounded migration contracts, evidence evaluation and independent certificates.

The evaluator has no authority access. Every compatible mapping is enumerated
only within the declared 2–6 account model (at most 720 permutations).

## class `Account` (Record)

_No docstring yet._

Fields:

- `id: str`
- `cents: int`

## class `Scope` (Record)

_No docstring yet._

Fields:

- `snapshot: str`
- `roster: str`
- `crosswalk: str`
- `unit: Literal['USD-cent']`

## class `Scenario` (Record)

_No docstring yet._

Fields:

- `seed: int`
- `scope: Scope`
- `accounts: tuple[Account, ...]`
- `destinations: tuple[str, ...]`

### `unique`

```python
def unique(self) -> Scenario
```

_No docstring yet._

## class `Link` (Record)

_No docstring yet._

Fields:

- `source: str`
- `destination: str`

## class `Plan` (Record)

_No docstring yet._

Fields:

- `version: int`
- `origin: Literal['fixture', 'evidence_repair', 'model_proposal']`
- `links: tuple[Link, ...]`

## class `Observation` (Record)

_No docstring yet._

Fields:

- `scope: Scope`
- `authority: Literal['synthetic-source/v1']`
- `links: tuple[Link, ...]`
- `status: Literal['observed', 'unavailable']`
- `issue: str`

## class `Witness` (Record)

_No docstring yet._

Fields:

- `first: Plan`
- `second: Plan`
- `source: str`

## class `Obligation` (Record)

_No docstring yet._

Fields:

- `claim: Literal['ownership']`
- `dependencies: tuple[str, ...]`
- `state: Literal['open', 'discharged', 'failed']`
- `resolution: str`
- `explanation: str`

## class `Evaluation` (Record)

_No docstring yet._

Fields:

- `ownership: Verdict`
- `evidence_status: tuple[Literal['accepted', 'stale', 'unavailable', 'invalid'], ...]`
- `compatible_count: int`
- `witness: Witness | None`
- `mismatch: Link | None`
- `conflicts: tuple[str, ...]`
- `obligation: Obligation`

## class `EvidenceAction` (Record)

_No docstring yet._

Fields:

- `kind: Literal['repeat_total', 'source', 'full_crosswalk']`
- `source: str`
- `cost: int`

## class `EvidencePort` (Protocol)

_No docstring yet._

### `obtain`

```python
def obtain(self, scope: Scope, action: EvidenceAction) -> Observation
```

_No docstring yet._

## Functions

### `valid_plan`

```python
def valid_plan(scenario: Scenario, plan: Plan) -> bool
```

_No docstring yet._

### `compatible`

```python
def compatible(scenario: Scenario, observations: tuple[Observation, ...]) -> tuple[Plan, ...]
```

_No docstring yet._

### `evidence_status`

```python
def evidence_status(scenario: Scenario, observation: Observation) -> Literal['accepted', 'stale', 'unavailable', 'invalid']
```

_No docstring yet._

### `evaluate`

```python
def evaluate(scenario: Scenario, plan: Plan, observations: tuple[Observation, ...]) -> Evaluation
```

_No docstring yet._

### `verify_witness`

```python
def verify_witness(scenario: Scenario, observations: tuple[Observation, ...], witness: Witness) -> bool
```

Direct certificate check: no call to compatible(), evaluate() or constructor.

### `response_matches_action`

```python
def response_matches_action(scenario: Scenario, action: EvidenceAction, observation: Observation) -> bool
```

Observed responses must cover their request; unavailable carries no claims.

Full requests require one claim per source. Global consistency is evaluated
separately, so complete but conflicting claims remain detectable as conflicts.
A source request may return conflicting claims about that requested source.

### `evidence_actions`

```python
def evidence_actions(scenario: Scenario) -> list[EvidenceAction]
```

The declared finite menu; no authority or hidden mapping is consulted.

### `select_action`

```python
def select_action(scenario: Scenario, observations: tuple[Observation, ...]) -> EvidenceAction | None
```

Lowest cost informative action in this finite menu, deterministic ties.

This does not claim minimum total cost of a complete adaptive strategy.
