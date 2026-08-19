# Project Backlog & Feature Roadmap

This file tracks planned features and professional improvements for the Headless FFmpeg Automation suite.

## Phase 3: Visual Polishing & Core Upgrades (In Progress)
- [x] **UV Paved Road Execution:** Migrate the entire Python environment management to `uv`. Utilize PEP 723 inline script metadata (`# /// script`) inside `build_headless_movie.py` so users can execute the project directly from GitHub without cloning or manual setup (e.g., `uv run https://raw.githubusercontent.com/...`).
- [x] **Automatic Color Correction:** Implemented a dynamic depth-based `colorbalance` FFmpeg filter that accurately restores absorbed red light proportionately to the CSV depth telemetry, replacing the need for static `.cube` LUTs.
- [ ] **Smooth Transitions:** Automate cross-dissolves (crossfades) between raw 4K clips using the FFmpeg `xfade` filter instead of hard cuts.

## Phase 4: Workflow Improvements
- [ ] **Experimental Color Grading Optimization:** The current `colorbalance` approach (Filter #1) amplifies red noise in dark underwater shadows (turning caves purple). We need to explore luma-masking or non-linear RGB curves (`curves` filter) to optimize the red filter: making corals brighter without ruining shadows.
- [ ] **Water Type Color Profiles:** Enhance the `--water` argument to support `freshwater` (boosts magenta to counteract green algae instead of pure red).
- [ ] **Multi-Day Processing:** Upgrade the `./render` wrapper to accept a range of dates (or automatically process all available media dates) in a single run.
- [ ] **Concurrent Rendering:** Explore using Python's `multiprocessing` to generate highlight slices in parallel before the final FFmpeg concatenation.

---
*Last updated: August 18, 2026*
