# `anomalon_workbench.tuner_demo`

Source: `src/anomalon_workbench/tuner_demo.py`

Finite demo for the tuner loop: pin the right keys in a tiny cache.

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

## class `CacheState`

_No docstring yet._

Fields:

- `pinned: frozenset[int]`
- `pinned_at_run_start: frozenset[int]`
- `last_segment: list[int]`

### `context`

```python
def context(self) -> dict[str, Any]
```

_No docstring yet._

### `to_json`

```python
def to_json(self) -> dict[str, Any]
```

_No docstring yet._

## class `ToggleProposer`

Propose pinning each unpinned key, swapping it in when the cache is full.

Candidates are ordered by how often the key was read in the last segment, so
when two approved changes conflict the more valuable one is applied first.
The proposer only guesses; the evaluator and the policy decide.

### `propose`

```python
def propose(self, context: Mapping[str, Any]) -> Sequence[Candidate]
```

_No docstring yet._

## class `ReplayEvaluator`

Replay the last recorded segment under the current and the candidate configuration.

### `evaluate`

```python
def evaluate(self, candidate: Candidate, history: Any) -> Verdict
```

_No docstring yet._

## class `NullMemory` (MistakeMemory)

A memory that forgets everything: the ablation for the demo.

### `remember`

```python
def remember(self, mistake: Mistake) -> None
```

_No docstring yet._

## class `DemoResult`

_No docstring yet._

Fields:

- `label: str`
- `task_error: list[float]`
- `proposal_error: list[float]`
- `proposals: list[int]`
- `skipped: list[int]`
- `applied: list[int]`
- `apply_failed: list[int]`
- `final_pinned: list[int]`
- `log: ReceiptLog`

### `to_json`

```python
def to_json(self) -> dict[str, Any]
```

_No docstring yet._

## Functions

### `zipf_trace`

```python
def zipf_trace(seed: int, runs: int=RUNS, reads: int=READS_PER_RUN, keys: int=KEYS, s: float=1.1) -> list[list[int]]
```

_No docstring yet._

### `misses`

```python
def misses(pinned: frozenset[int], segment: Sequence[int]) -> int
```

_No docstring yet._

### `apply_candidate`

```python
def apply_candidate(pinned: frozenset[int], candidate: Candidate) -> frozenset[int]
```

Return the configuration after ``candidate``; raise when it no longer applies.

### `verify_receipts`

```python
def verify_receipts(log: ReceiptLog, trace: Sequence[Sequence[int]]) -> list[dict[str, Any]]
```

Independently recompute every ``evaluated`` receipt's evidence from the recorded trace.

Returns one entry per receipt whose claimed verdict or numbers disagree with a
direct recount. This is the check that catches an evaluator that lies, and it
uses only receipts plus the recorded history, never the evaluator itself.

### `run_demo`

```python
def run_demo(seed: int=7, with_memory: bool=True, runs: int=RUNS) -> DemoResult
```

_No docstring yet._

### `render_chart`

```python
def render_chart(results: Sequence[DemoResult]) -> str
```

Two line panels (task error, proposal error) per run, one line per result.

### `main`

```python
def main(argv: Sequence[str] | None=None) -> int
```

_No docstring yet._
