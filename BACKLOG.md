# Project Backlog & Feature Roadmap

This file tracks planned features and professional improvements for the Headless FFmpeg Automation suite.

## Phase 3: Visual Polishing & Core Upgrades (In Progress)
- [x] **UV Paved Road Execution:** Migrate the entire Python environment management to `uv`. Utilize PEP 723 inline script metadata (`# /// script`) inside `build_headless_movie.py` so users can execute the project directly from GitHub without cloning or manual setup (e.g., `uv run https://raw.githubusercontent.com/...`).
- [ ] **Automatic Color Correction:** Apply a standard "Underwater Recovery" LUT or `.cube` grade to all MP4s dynamically during the FFmpeg render process (using `lut3d`).
- [ ] **Smooth Transitions:** Automate cross-dissolves (crossfades) between raw 4K clips using the FFmpeg `xfade` filter instead of hard cuts.
- [x] **Check and optimize unit-tests for better project management and test-coverage.** (Closed due to structural refactoring of `main`).

## Phase 3.5: Code Review Remediation (v3.1.5 - v3.1.7)

Full code review revealed 18 issues. Tasks are split across multiple iterations.

### 🎯 Completed in v3.1.5 (Critical Hotfixes)
- [x] **CR-01: Remove hardcoded `/opt/homebrew/bin/` fallbacks**
- [x] **CR-02: Refactor `check-status.py`**
- [x] **CR-03: DRY — Create `scripts/utils.py` for shared code**
- [x] **CR-04: Test `test_headless_engine.py` — remove `/opt/homebrew/` fallback**
- [x] **CR-05: Test `validate_output.py` — remove duplicate `import shutil` and hardcodes**

### 🚧 Planned for v3.1.6 (High Priority & Stability)
- [x] **CR-06: Bug in `render` — add `exit 1`** — Script does not exit after `echo "Usage: ./render -d YYYY-MM-DD"`. Add `exit 1` to prevent running with empty `$DATE`.
- [x] **CR-07: Rewrite `test_srt_generation.py`** — Replace raw source code checks (`assertIn(expected, self.code)`) with real unit tests asserting `format_srt_time()` behavior.
- [x] **CR-08: Fix `test_logic_accuracy.py`** — Replace duplicated local `detect_dives_logic()` (gap=1800) with imported `detect_dives()` (gap=7200) from `scripts/build_headless_movie.py`.
- [x] **CR-09: Update `skill/python-telemetry.md`** — Replace references of outdated `requirements.txt` with PEP 723 + `uv`.
- [x] **CR-10: Align SKILL.md regarding `./render` wrapper** — Remove the word "legacy" and acknowledge `./render` as a valid entry point, or justify its removal.
- [x] **CR-12: Refactor FFmpeg fallback in `build_headless_movie.py`** — Replace brittle `cmd.index(...)` mutation with a standalone `build_ffmpeg_cmd(codec=...)` builder.
- [x] **NEW: Reliable Temp File Cleanup** — Use `atexit` or `try/finally` in `build_headless_movie.py` to ensure `temp_dir` is always removed (even on `No space left on device` or `Ctrl+C`).
- [x] **NEW: Faststart Fix** — Add `-movflags +faststart` flag to the final FFmpeg render to ensure immediate video playback in QuickTime.
- [x] **NEW: Separate Output per Dive** — Instead of concatenating all slices from multiple dives into a single day-long video file, group them and output a distinct MP4 file per dive (e.g., `dive_YYYY-MM-DD_dive1.mp4`).

### 📅 Planned for v3.1.7 (Tech Debt & Polish)
- [x] **CR-11: Clean `EOF` from `.gitignore`** — Remove artifact `EOF` string from `.gitignore` (garbage from `cat << EOF`).
- [x] **CR-13: Add PEP 723 inline metadata** — Add `# /// script` block in `calc_offset.py` and `check_videos.py` to auto-fetch `pandas` via `uv run`.
- [x] **CR-14: Migrate E2E tests to `main(args=...)`** — `test_headless_engine.py` and `validate_output.py` should import `main()` instead of using subprocess for proper coverage tracking.
- [x] **CR-15: Complete CHANGELOG.md v3.1.4** — Add missing items: CLI tools refactor, DoD checklist, CI migration to pytest-cov, SKILL TDD mandates.
- [x] **CR-16: Create `tests/conftest.py`** — Replace `sys.path.insert(...)` boilerplate in every test file with a single `conftest.py` or `pyproject.toml` configuration.
- [x] **CR-17: Hoist inline imports to module level** — In `test_build_headless_movie.py`, move `from scripts.build_headless_movie import concatenate_slices, build_overlay_slices, main` to the top of the file.
- [x] **CR-18: Close UV Paved Road in BACKLOG** — Mark as `[x]` (already implemented in v3.1.1).

## Phase 4: Workflow Improvements (v3.2.0 - v3.3.0)
- [x] **Experimental Color Grading Optimization:** The current `colorbalance` approach (Filter #1) amplifies red noise in dark underwater shadows (turning caves purple). We need to explore luma-masking or non-linear RGB curves (`curves` filter) to optimize the red filter: making corals brighter without ruining shadows.
- [x] **Water Type Color Profiles:** Enhance the `--water` argument to support `freshwater` (boosts magenta to counteract green algae instead of pure red).
- [ ] **Multi-Day Processing:** Upgrade the `./render` wrapper to accept a range of dates (or automatically process all available media dates) in a single run.
- [x] **Concurrent Rendering:** Explore using Python's `multiprocessing` to generate highlight slices in parallel before the final FFmpeg concatenation.

---
*Last updated: September 16, 2026*
