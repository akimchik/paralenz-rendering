# Project Backlog & Feature Roadmap

This file tracks planned features and professional improvements for the Headless FFmpeg Automation suite.

## Phase 3: Visual Polishing & Core Upgrades ✅ (Closed)
- [x] **UV Paved Road Execution:** Migrate the entire Python environment management to `uv`. Utilize PEP 723 inline script metadata (`# /// script`) inside `build_headless_movie.py` so users can execute the project directly from GitHub without cloning or manual setup (e.g., `uv run https://raw.githubusercontent.com/...`).
- [x] **Automatic Color Correction:** Dynamic depth-based `curves` filter applied per-slice using real telemetry data. Replaces the static `.cube` LUT approach.
- [x] **Check and optimize unit-tests for better project management and test-coverage.** (Closed due to structural refactoring of `main`).
- [ ] **Smooth Transitions:** Automate cross-dissolves (crossfades) between raw 4K clips using the FFmpeg `xfade` filter instead of hard cuts. *(Carried to Phase 6)*

## Phase 3.5: Code Review Remediation ✅ (Closed — v3.1.5 to v3.1.7)

Full code review revealed 18 issues. All resolved across v3.1.5, v3.1.6, and v3.1.7.

<details>
<summary>Click to expand completed items</summary>

### Completed in v3.1.5 (Critical Hotfixes)
- [x] **CR-01: Remove hardcoded `/opt/homebrew/bin/` fallbacks**
- [x] **CR-02: Refactor `check-status.py`**
- [x] **CR-03: DRY — Create `scripts/utils.py` for shared code**
- [x] **CR-04: Test `test_headless_engine.py` — remove `/opt/homebrew/` fallback**
- [x] **CR-05: Test `validate_output.py` — remove duplicate `import shutil` and hardcodes**

### Completed in v3.1.6 (High Priority & Stability)
- [x] **CR-06: Bug in `render` — add `exit 1`**
- [x] **CR-07: Rewrite `test_srt_generation.py`**
- [x] **CR-08: Fix `test_logic_accuracy.py`**
- [x] **CR-09: Update `skill/python-telemetry.md`**
- [x] **CR-10: Align SKILL.md regarding `./render` wrapper**
- [x] **CR-12: Refactor FFmpeg fallback in `build_headless_movie.py`**
- [x] **NEW: Reliable Temp File Cleanup**
- [x] **NEW: Faststart Fix**
- [x] **NEW: Separate Output per Dive**

### Completed in v3.1.7 (Tech Debt & Polish)
- [x] **CR-11: Clean `EOF` from `.gitignore`**
- [x] **CR-13: Add PEP 723 inline metadata**
- [x] **CR-14: Migrate E2E tests to `main(args=...)`**
- [x] **CR-15: Complete CHANGELOG.md v3.1.4**
- [x] **CR-16: Create `tests/conftest.py`**
- [x] **CR-17: Hoist inline imports to module level**
- [x] **CR-18: Close UV Paved Road in BACKLOG**

</details>

## Phase 4: Workflow Improvements ✅ (Closed — v3.2.0 to v3.2.1)
- [x] **Experimental Color Grading Optimization:** Migrated from `colorbalance`/`colorchannelmixer` to non-linear `curves` filter. Mid-tones are boosted proportionally to depth while blacks stay black (no purple caves).
- [x] **Water Type Color Profiles:** `--water` argument supports `saltwater`, `freshwater`, and `none`.
- [x] **Concurrent Rendering:** `ThreadPoolExecutor` parallelizes slice extraction. PID-based temp directories prevent race conditions.
- [x] **Script Cleanup:** Removed obsolete `check-status.py`, `calc_offset.py`, and `check_videos.py` — all functionality absorbed into `build_headless_movie.py`.
- [ ] **Multi-Day Processing:** Upgrade the entrypoint to accept a range of dates (or automatically process all available media dates) in a single run. *(Carried to Phase 6)*

## Phase 5: v3.2.1 Code Review Remediation ✅ (Closed — v3.2.2)

Post-release audit of v3.2.1 revealed 14 issues. All were resolved during the v3.2.2 Single-Pass Architecture transition.

### 🔴 Critical (Must fix before any new features)
- [x] **CR-01: Delete `tests/validate_output.py`** — 286 lines of dead code. Not collected by pytest (no `TestCase` class, no `test_` functions). Calls `sys.exit()` which would kill pytest if ever imported.
- [x] **CR-02: Replace `__import__('os')` anti-pattern** — `_process_slice()` uses `__import__('os').path.basename()` three times instead of the already-imported `os` module. *(Resolved natively: `_process_slice` was deleted in Single-Pass rewrite).*
- [x] **CR-03: Remove duplicate inline imports** — `subprocess` re-imported inside `get_best_hardware_encoder()` (already at module level L19). `shutil` re-imported inside `finally` block (already at module level L25).
- [x] **CR-05: Remove `check-status.py` reference from README** — "Monitoring Progress" section documents a deleted script.
- [x] **CR-06: Remove `evermeet.cx` recommendation from README** — This source ships x86_64-only binaries without `libass`. Broke our CI today. Replace with Homebrew tap instructions only.

### 🟡 Medium (Should fix in same iteration)
- [x] **CR-07: Fix `temp_dir_display` banner** — Banner at L299 prints `temp_slices_{mode}` but actual dir created at L346 is `temp_slices_{mode}_{date}_{pid}`. User sees a non-existent path.
- [x] **CR-08: Delete duplicated assertion blocks in tests** — `test_build_overlay_slices` and `test_build_overlay_slices_fallback` each have the same 12-line assertion block copy-pasted twice. *(Resolved natively: deleted obsolete tests).*
- [x] **CR-09: Remove `print\(` from `.coveragerc` exclusions** — This silently excludes every `print()` statement from coverage analysis, including actual error handling paths. Coverage numbers are inflated. **Solution:** Extract cosmetic output (banners, progress) into a `_info(msg)` helper marked with `# pragma: no cover`. Keep raw `print()` only for error paths — these must be covered by tests.
- [ ] **CR-10: Fix freshwater blue channel coefficient** — Red and blue curves use the same `mid` value. Freshwater should use a lower blue boost (e.g., `boost * 0.5`) to avoid unnatural pink tones.
- [ ] **CR-11: Add `--water` flag coverage in E2E tests** — No E2E test for `freshwater` or `none`. Add at minimum a `--water none` E2E test.

### 🟢 Low / Cosmetic
- [x] **CR-12: Clean BACKLOG.md references to deleted scripts** — *(This commit)*
- [x] **CR-14: Remove unused `import json` from `test_headless_engine.py`** *(Resolved natively: `json` is now used by `inspect_video`).*

## Phase 6: Future Features (Backlog)
- [ ] **Multi-Day Processing:** Accept a date range (`--date-from`, `--date-to`) or auto-discover all available dates from the logs directory. *(Carried from Phase 4)*
- [ ] **Smooth Transitions:** Cross-dissolves between clips via FFmpeg `xfade` filter. *(Carried from Phase 3)*

---
*Last updated: September 16, 2026*
