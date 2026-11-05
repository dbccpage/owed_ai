# PR #11 review response

The supplied review inspected `3b23c075fb04d4f07e16a91d008f09f8076945c3`.
The listed defects remained in that head when checked. This correction addresses
the same draft PR without a deployment or a framework change.

| Finding | Correction and evidence |
| --- | --- |
| Primary workflow hidden in sidebar | Main-scene prediction, investigation, verification and terminal recovery controls; the sidebar retains navigation/settings/restart/export/replay. AppTest scopes and the container journey require main controls. |
| Empty or partial full responses accepted | Observed replies must be nonempty and refer to declared rosters. Full replies require exactly one claim per source. Incomplete full replies fail before admission and also fail replay. A complete single-source response supplies partial global knowledge. Complete conflicts still block execution through the conflict check. |
| Desktop connections inaccessible | A visually hidden relationship list remains accessible on desktop and visible on mobile. The SVG description also lists each connection. |
| Replay language overclaims historical verification | Original execution is labeled verified against SQLite; offline replay says recorded results are semantically consistent and explains that the original temporary database is unavailable. |
| Repeated checks lost on export | `migration/3` stores separate informational events with chronology, exact result and unchanged before/after possibility counts. Replay recomputes them. They cannot supply identity links or admission authority. Valid v1/v2 receipts remain supported. |
| Engineering value unclear | A short statement of the outstanding ownership obligation precedes the scene. Final verification summarizes conservation, initial ambiguity, repeated probes, accepted mapping and original row verification. |

## Verification

- Full Python suite: 367 passed; Ruff and strict mypy pass (22 source files).
- New regressions include adapter and replay rejection of empty/partial full replies,
  out-of-roster links, retained complete conflicts, malformed probe metadata,
  legacy-version smuggling and chronology tampering.
- Browser journey at 390 x 844: prediction, repeated total, one identity record,
  automatic full mapping, verification and final reflection all completed with the
  navigation drawer closed. Document width remained 390 pixels.
- Desktop accessibility tree exposes all three source-to-destination connections.
  Browser replay displays the new semantic-consistency wording.
- Existing examples, earlier evidence and Lean sources are preserved byte-for-byte.
- The container acceptance script now follows main-scene controls and checks probe
  export/replay. Hosted CI supplies the actual Linux/Docker and fresh Lean results;
  local Python/browser checks alone do not establish those outcomes.

New review images: [main action on phone](../../evidence/pr11-review-main-mobile.jpg)
and [verified desktop result](../../evidence/pr11-review-verified-desktop.jpg).
The earlier review images remain unchanged.

## Limits and next review

The strict contract rejects malformed observed replies; it does not manufacture a
partial-response status or a successful evidence step for them. The UI explains
that failure and retains the last valid receipt. An unavailable source still has
an explicit unavailable record. A single-source reply can be accepted without
establishing a complete global mapping.

This remains a bounded synthetic one-to-one permutation demonstration. Probe
replay checks consistency of supplied records, not authenticated human actions or
historical database execution. No live model calls, production deployment or
cross-property design rollout were performed for these corrections.

Cold-start comprehension with unfamiliar visitors remains a human acceptance task.
Ask them to explain what the passing checks established, what ownership evidence
was missing, and why execution became justified. Passing automated checks does
not establish that comprehension result.
