# Owed guided migration scene

Review slice from `d59b189072b3c852e5fee820d6ac94264ba1cd57`, implementing the user-supplied account-migration redesign. The working scene is the reference to approve before applying the visual system to other Anomalon properties. Production deployment and cross-site rollout follow that review.

## The experience

1. **Meet the accounts.** Three fictional named customers show $700, $200, and $100. New account IDs are visible; ownership stays unknown. An explicit next action appears in the main scene, including when the navigation drawer is closed.
2. **Inspect the proposal.** Dashed connections and balances are labeled proposed. The total and count match; ownership is unresolved. The proposal is not called wrong on those checks alone.
3. **Make your prediction.** Yes, No, and Not enough information are available before alternatives are shown. Both answers withholding approval are acknowledged; the flow does not force an incorrect answer.
4. **Test the evidence.** The engine computes six compatible assignments in the default case and shows two disagreeing ones beside the same account scene. The view says these are two examples, not the entire possibility set.
5. **Resolve the uncertainty.** Repeating totals or counts leaves six assignments and adds no identity observation. A visitor-selected identity record leaves two, reveals only the established owner, and records the request provenance. The existing selector can then request the full mapping, leaving one. Missing or stale records are excluded; conflicting records block execution. Outdated records have a refresh action. Conflicts require a restart with a consistent source; the UI does not silently erase accepted evidence.
6. **Verify the result.** Accepted current evidence and the one-to-one model justify the repair. Solid connections, named destination owners, corrected amounts and previous amounts appear in place. The actual six SQLite execution checks appear beside them. A final question asks what justified proceeding.

Established / Still owed / Execution remains visible. The main scene holds prediction, investigation, verification and terminal recovery actions. Scenario settings, navigation restart, export and digest-bound replay stay in the sidebar. Explanation and Technical evidence are secondary pages; original research labs remain available. Raw JSON is confined to technical inspection.

## Engine and receipt contracts

`migration.py` remains the owner of compatibility, evaluation, witness verification and evidence selection. The renderer has no authority adapter or hidden mapping. Destination owners are derived only from compatible assignments under accepted observations; an inferred remaining owner uses the declared one-to-one mapping requirement. Only the synthetic authority adapter sees the fixture's hidden correspondence.

`evidence_actions` exposes the existing finite menu. Automatic selection still excludes uninformative totals and chooses the lowest declared-cost informative request, with deterministic ties. This is not a search over all complete adaptive strategies. Costs are synthetic request costs, not model API charges.

Manual identity requests require a small receipt extension. New `migration/3` receipts retain the `migration/2` distinction recording `selected_by` as engine or visitor. Replay checks automatic choices against the selector and visitor choices against the declared menu, including source and cost. Both paths enforce response scope, roster membership, nonempty observed replies and request coverage before compatibility evaluation and admission. A full-mapping response must contain exactly one claim per source; incomplete observed full replies are rejected. A response to a single-source request may leave global knowledge partial. Complete conflicting replies still reach the conflict check. A declaration of who selected a request is provenance, not authenticated authorship or additional execution authority.

Valid legacy `migration/1` and `migration/2` receipts remain supported: missing `selected_by` means engine, and a migration/1 receipt claiming a visitor-selected action is rejected. Schema/checker mismatches and unsupported requests are rejected. Repeating total/count checks only reads preview results; it does not fabricate an identity record. Informational probes now live in the receipt's separate `investigations` list, with step boundary, result, before/after compatible counts and `information_gained: none`. Replay checks chronological placement and recomputes each result/count. Probes never enter accepted identity evidence; old schema versions cannot carry this new metadata.

Exported hashes bind supplied content. They do not authenticate a self-consistently rewritten bundle. Original execution is verified against SQLite. Offline replay checks semantic consistency of recorded results and decisions; it cannot reopen the original temporary database or establish that the historical transaction occurred. Replay never grants execution authority. All migrations affect fresh temporary synthetic SQLite databases; original examples and proof evidence remain unchanged.

## Claude's design contribution

Claude Code supplied a design-only response to the brief: warm paper canvas, navy navigation, teal action/knowledge accents, amber uncertainty, green verification, system fonts, responsive cards and connection diagrams, and reduced-motion support. Repository source and file tools were excluded from that call. Codex integrated and tested the response in the existing Streamlit stack.

The shared visual vocabulary lives in `src/anomalon_workbench/assets/anomalon.css`, using `--an-*` tokens and `an-*` component classes. `migration_scene.py` renders escaped account cards, connections and alternative assignments; it makes no engine decisions. Streamlit-specific adapters use stable test IDs rather than generated classes. There are no external fonts, image dependencies, or browser scripts.

Desktop places alternatives/corrections beside the account scene. On small screens the accounts remain paired in two columns, SVG connections become explicit text, and the consequence panels stack. Primary actions remain in the main scene. The full successful journey was completed at 390×844 without opening the drawer and without horizontal overflow. All individual connections remain available in the desktop accessibility tree through a visually hidden list and the SVG description; the list is visible on mobile. Animation respects `prefers-reduced-motion`.

These tokens are prepared for reuse across Anomalon properties. They have not yet been applied to the other subdomains or `anomalon.com`; the user's specification first requires approval of this working scene.

## Validation and review

- All 367 Python tests passed, including the complete existing core suite and new walkthrough/provenance cases. Ruff and strict mypy passed.
- New checks cover all prediction choices; withheld destination identities; repeated uninformative checks; partial knowledge (6 → 2); full resolution; manual versus automatic selection; unsupported requests; old receipt replay; digest-bound replay invalidation; missing, stale and conflicting records; escaped HTML; and separate technical pages.
- The container acceptance script follows the new prediction-first controls and retains unprivileged execution, cleanup, persistence and semantic replay checks. Hosted CI supplies the actual container and fresh Lean validation outcome.
- Browser review exercised the desktop journey, repeated total, partial identity request, automatic selection, in-place correction and actual execution checks. The phone journey completed at 390×844 with no horizontal overflow and the drawer closed throughout; desktop connection text and the precise offline replay message were checked in the browser.
- The Lean source and earlier proof reports/receipts were preserved. This change does not extend the formal theorem statements.

A passing interaction test is not a measured comprehension study. The final acceptance question remains for the user and a new visitor: can they explain what was missing, how ambiguity was demonstrated, why repeated totals were insufficient, and what evidence justified proceeding?

Review images: [ambiguity on desktop](../evidence/guided-migration-ambiguity.jpg),
[verified result](../evidence/guided-migration-verified.jpg), and
[phone layout](../evidence/guided-migration-mobile.jpg).

The [review-response record](pr11-review-response.md) covers the corrections and new screenshots.

## Next review

Approve or revise this working scene and its transitions. Then apply the approved tokens and components across the other MVPs, adapting them to their existing stacks. Keep later Composition/Revision redesigns as separate reviewable slices.
