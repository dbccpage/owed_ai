# Overnight Improvement Log — Owed (`2026-11-05`)

## What this app does

1. Owed is a Python and Streamlit application (`app.py` calling `anomalon_workbench.ui:main`) that defaults to the guided `"Migration challenge"` page (`src/anomalon_workbench/migration_ui.py`).
2. The default migration challenge simulates migrating customer account balances (integer cents across 2 to 6 source accounts `S-*` to destination accounts `N-*`) under a candidate mapping that preserves total dollars and row count while permuting account ownership.
3. The deterministic checker (`src/anomalon_workbench/migration.py:evaluate`) checks whether total cents, row count, and per-account ownership are preserved, and constructs a counterexample witness of two mappings that share the same total while assigning a source account's balance to different destinations.
4. When ownership is `underdetermined`, the action selector (`migration.py:select_action`) prices candidate evidence queries (`repeat_total` at cost 0, single-account lookup at cost 2, `full_crosswalk` at cost `max(1, n - 1)`) and selects the lowest-cost query that resolves the ambiguity.
5. Clicking `"Run the migration challenge"` evaluates the candidate plan against the chosen synthetic authority mode (`valid`, `missing`, `stale`, or `contradictory` in `src/anomalon_workbench/migration_demo.py`).
6. Clicking `"Obtain selected evidence and apply justified repair"` queries `SyntheticAuthority` (`synthetic-source/v1`), validates scope and consistency of the returned links, and either blocks admission or derives a repaired bijection.
7. When evidence is accepted and conflict-free, `migration.py:execute` runs the repaired migration inside an in-memory SQLite transaction and checks six post-conditions (`committed`, `total_preserved`, `row_count_preserved`, `identity_coverage`, `execution_conforms`, `ownership_preserved`).
8. Every run produces a canonical JSON `Receipt` (`migration_demo.py:export`) with SHA-256 digests that can be re-evaluated offline via `migration_demo.py:replay`.
9. Behind the sidebar navigation, `src/anomalon_workbench/ui.py` also hosts five additional workbench views (`Overview`, `Evidence` for 2-reserve integer ledger checks, `Composition` for rational difference-constraint graphs, `Revision` for parent/child prompt evaluation, and `Run inspector` for SQLite-stored runs and recorded bundles).
10. Code-versus-README note: `README.md` describes both the guided migration challenge and the three workbench labs, whereas the baseline Streamlit server had no `.streamlit/config.toml` and defaulted to dark mode (`rgb(14, 17, 23)`) in headless Chromium/Edge.

## Baseline

- **Desktop front page (`1280 × 800`)**: `overnight/baseline/front_1280x800.png` (rendered in Streamlit dark theme `rgb(14, 17, 23)` with open sidebar and multi-screen vertical scroll `scrollHeight = 2079 px`).
- **Phone front page (`390 × 844`)**: `overnight/baseline/front_390x844.png` (rendered in Streamlit dark theme `rgb(14, 17, 23)` with vertical scroll `scrollHeight = 2368 px`).
- **Browser console output**: `overnight/baseline/browser_console.txt` (`0` console errors).
- **First result timing**: `overnight/baseline/first_result_timing.txt` (`/_stcore/health` HTTP 200 in `12.7 ms`, initial HTML in `18.4 ms`, headless Edge DOM and screenshot ready in `4120.5 ms`).
- **Baseline test suite output**: `overnight/baseline/test_suite_output.txt` (`331 passed in 32.01s`).

### Complete inventory of pages, sidebar entries, widgets, expanders, and tabs in `ui.py` and `migration_ui.py`

| Location (baseline -> updated lines) | Element / Widget | Kind | Used by the one-screen migration flow? | Disposition |
|---|---|---|---|---|
| `ui.py:447-511` (`baseline 391-455`) | `st.sidebar` with `st.title("Owed")`, `st.radio("Workbench", ["Migration challenge", "Overview", "Evidence", "Composition", "Revision", "Run inspector"])`, `st.divider()`, hosted `st.expander("Operator access and live experiments")` (`st.button("Log out")`, `st.expander("Account identifier for access requests")`, `st.button("Log in with Google")`), or local `st.selectbox("Provider")`, `st.text_input("Explicit model ID")`, `st.selectbox("Output mode")` | Sidebar navigation & provider controls | Only default selection `"Migration challenge"` is used; other radio options and provider controls are for secondary labs | Kept in Streamlit widget tree for `AppTest` compatibility; hidden visually on screen via CSS (`[data-testid="stSidebar"] { display: none !important; }`) and `initial_sidebar_state="collapsed"` |
| `ui.py:268-326` (`baseline 259-325`) | `overview()` page (`st.title("Owed")`, 3 bordered containers, `st.link_button("Explore Owed on GitHub")`, `st.expander("Formal supplement and research lineage")`) | Secondary page (`Overview`) | Not used in migration flow | Preserved in `ui.py` behind `"Overview"` radio state; removed internal terms (`Omega Engine`, `Pre-Genesis`, `Genesis`, `LGGR`, `PFP`, `EIS`, `PCIV`) and `◈` symbol |
| `ui.py:75-123` (`baseline 74-122`) | `ledger_page()` (`st.selectbox("Observation")`, `st.radio("Simulated actor")`, `st.expander("Edit evidence and scope")`, `st.text_area`, 3 `st.metric`, `st.table`, `st.expander("Accepted evidence, assumptions and full host evaluation")`, `start_button("ledger", ...)`) | Secondary page (`Evidence`) | Not used in migration flow | Preserved in `ui.py` behind `"Evidence"` radio state |
| `ui.py:125-155` (`baseline 125-154`) | `graph_page()` (`st.expander("Edit the synthetic constraints")`, `st.text_area`, `st.json`, `start_button("graph", ...)`) | Secondary page (`Composition`) | Not used in migration flow | Preserved in `ui.py` behind `"Composition"` radio state |
| `ui.py:157-186` (`baseline 157-185`) | `revision_page()` (`st.expander("Protected core")`, `st.text_area("Editable parent instructions")`, `start_button("revision", ...)`) | Secondary page (`Revision`) | Not used in migration flow | Preserved in `ui.py` behind `"Revision"` radio state |
| `ui.py:203-266, 525-558` (`baseline 199-256, 469-502`) | `inspector()` fragment & `"Run inspector"` branch (`st.selectbox("Run")`, `st.button("Cancel run")`, `show_review()` with `st.expander("Review scope and source binding")`, `st.expander("Proposal, checked evidence and complete result")`, `st.download_button("Export replay bundle")`, `st.button("Verify offline replay")`, `st.checkbox`, `st.button("Admit candidate for subsequent runs")`, `st.expander("Progress events")`, `st.expander("Recorded live demonstrations · no API key needed")` with `st.selectbox("Recorded lab")` & `st.button("Verify recorded demonstration")`, `st.file_uploader`, `st.button("Replay uploaded bundle")`) | Secondary page (`Run inspector`) | Not used in migration flow | Preserved in `ui.py` behind `"Run inspector"` radio state |
| `migration_ui.py:47-70` (`baseline 47-59`) | Page header (`st.title`), intro caption (`st.caption`), `st.selectbox("Choose an evidence scenario")`, `st.button("Run the migration challenge", type="primary")` | Top-level migration controls | **Yes** — selects scenario and runs the migration challenge | Displayed in a compact 2-column top bar above the 5 numbered sections |
| `migration_ui.py:139-143` | Section `1. The claim: the total is right` (`st.subheader`, `st.write` with total, account count, `Source:` ledger rows, and `Rule:`) | Core migration step 1 | **Yes** | Displayed in left column of the one-screen layout |
| `migration_ui.py:145-162` | Section `2. The check that fails: which balances, which accounts` (`st.subheader`, `st.info("A correct total does not establish correct ownership.")`, `st.write` with `underdetermined` status, permutation count, `Source:` candidate rows, and `Rule:`) | Core migration step 2 | **Yes** | Displayed in left column of the one-screen layout |
| `migration_ui.py:164-168` | Section `3. What the machine does not know and what it would cost to find out` (`st.subheader`, `st.write` with missing crosswalk scope, action costs, `Source:` action menu, and `Rule:`) | Core migration step 3 | **Yes** | Displayed in left column of the one-screen layout |
| `migration_ui.py:170-198` | Section `4. The question it asks` (`st.subheader`, `st.write` with authority query, `Source:`, `Rule:`, and action buttons `st.button("Obtain selected evidence and apply justified repair")` / `st.button("Refresh stale crosswalk from current authority")`) | Core migration step 4 | **Yes** | Displayed in left column of the one-screen layout |
| `migration_ui.py:201-274` | Section `5. The corrected result with the rows that changed` (`st.subheader`, `st.table(comparison(receipt))` with `Account`, `Proposed balance`, `Corrected balance`, summary of changed rows, explicit `Rows changed:` diff with `Source:` and `Rule:`, and admission status banner) | Core migration step 5 | **Yes** | Displayed in right column of the one-screen layout |
| `migration_ui.py:276-398` (`baseline 82-104, 152-298`) | `st.expander("More")` containing `_render_more_controls()` (source accounts `st.table`, `st.button("Generate another reproducible case")`, `st.button("Reset this session")`, witness counterexample `st.table`, accepted correspondence `st.table`, six execution checks `st.table`, `st.button("Change snapshot and crosswalk version")`, `st.download_button("Export replayable receipt")`, `st.button("Replay this receipt offline")`, `st.json`, `st.code(digest(receipt))`, `st.text_area("Receipt JSON (100 KB maximum)")`, `st.button("Check imported receipt")`) and `engineering()` (`st.link_button`, `st.code`, `proof_status()` JSON, theorem `st.link_button`) | Secondary details and diagnostic controls (previously 3 separate expanders + top-level source table and reset buttons) | Not needed on first screen; available on demand | Consolidated inside a single `st.expander("More")` at the bottom of the screen |

## Changed

1. **Enforced light-only Anomalon paper theme (`b775b91` -> working tree)**:
   - Added `.streamlit/config.toml` and CLI flags in `src/anomalon_workbench/serve.py` (`--theme.base=light`, `--theme.backgroundColor=#fbfbf9`, `--theme.secondaryBackgroundColor=#ffffff`, `--theme.textColor=#15202c`, `--theme.primaryColor=#12706c`, `--server.headless=true`).
   - Added `_ANOMALON_CSS` in `src/anomalon_workbench/ui.py` applying IBM Plex Sans and IBM Plex Mono typography, `#fbfbf9` paper background, `#ffffff` card surfaces, `#15202c` ink, `#12706c` teal primary buttons, `6px` border radius, zero shadows, and zero `prefers-color-scheme` dark rules.
2. **Removed internal jargon and decorative symbols from `ui.py`**:
   - Removed internal labels (`Omega Engine`, `Pre-Genesis`, `Genesis`, `LGGR`, `PFP`, `EIS`, `PCIV`) and the `◈` symbol from `src/anomalon_workbench/ui.py`.
3. **Reshaped the migration page into one screen with five ordered elements and one `"More"` expander (`src/anomalon_workbench/migration_ui.py`)**:
   - Placed the five required elements on one screen at `1280 × 800` (`mainRectH = 679 px <= 800 px`, `scrollHeight = 800 px`, `scrollWidth = 1280 px`):
     1. `1. The claim: the total is right` (with `Source:` ledger rows and `Rule:`)
     2. `2. The check that fails: which balances, which accounts` (with `Source:` candidate rows and `Rule:`)
     3. `3. What the machine does not know and what it would cost to find out` (with `Source:` action menu over compatible states and `Rule:`)
     4. `4. The question it asks` (with `Source:` snapshot/crosswalk scope, `Rule:`, and evidence acquisition button)
     5. `5. The corrected result with the rows that changed` (with the `Account` / `Proposed balance` / `Corrected balance` table, per-row diff, `Source:` accepted crosswalk, and `Rule:`)
   - Consolidated the source-account table, seed/reset controls, counterexample witness table, 6-property execution table, receipt JSON/export/import replay controls, and Lean build metadata into a single `st.expander("More")` at the bottom of the page.
4. **Added regression test and verified all 332 tests + container `AppTest` checks**:
   - Added `test_one_screen_five_elements_and_more_control` in `tests/test_migration_story.py`.
   - Verified `pytest -q` (`332 passed in 25.49s`) and the `AppTest` suite from `scripts/check_container.py`.
   - Captured post-change screenshots `overnight/after_front_1280x800.png` and `overnight/after_front_390x844.png`.

## Not done

- Executing `scripts/check_container.py` against a live Docker daemon: Docker is not installed on this Windows host, so the outer `docker run` wrapper could not be invoked. The inner `AppTest`, `proof_status()`, and offline `replay(export(receipt))` checks from `scripts/check_container.py` were executed directly against the local `.venv` in `WORKBENCH_MODE=hosted` and passed.

## Decisions for the owner

- **Whether to remove or expose the five secondary workbench views (`Overview`, `Evidence`, `Composition`, `Revision`, `Run inspector`) via a separate URL route**: Currently they remain intact in `src/anomalon_workbench/ui.py` (so all existing unit and `AppTest` suites pass) while the sidebar chrome is hidden on the front page so `/` is a clean single-pane migration story. Deciding whether to retire those secondary labs or expose them at a dedicated path is a product-scope decision for the owner.

## Found but out of scope

- Local untracked `data/runs/` state from earlier manual runs can reference missing artifact hashes if `data/artifacts/` was partially cleaned; hosted mode uses isolated temporary/volume directories (`WORKBENCH_DATA_DIR`).
