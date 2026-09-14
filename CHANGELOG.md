# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [v3.1.6] - 2026-09-14

### Fixed
- **FFmpeg Fallback**: Replaced fragile array index mutation (`cmd.index(...)`) with a robust standalone command builder (`build_ffmpeg_cmd`) for switching between hardware (`h264_videotoolbox`) and software (`libx264`) encoding.
- **Reliable Cleanup**: Encapsulated the main FFmpeg overlay execution inside a `try/finally` block to guarantee `temp_dir` cleanup, even if interrupted by `Ctrl+C` or "No space left on device" errors.
- **Immediate Playback**: Added the `-movflags +faststart` flag to the final FFmpeg concatenation command. This shifts the `moov` atom to the front of the `.mp4` file, allowing instant playback in QuickTime without waiting for the entire file to buffer.
- **Multi-Dive Output**: Fixed an issue where slices from multiple separate dives within the same day were concatenated into a single massive video. The script now iterates over each dive individually and outputs distinct files (e.g., `dive_2026-08-10_dive1.mp4`).

## [v3.1.5] - 2026-08-25

### Fixed
- **Code Review Remediation (Critical)**: Refactored redundant `get_meta()`, `get_ffmpeg_path()`, and `get_ffprobe_path()` functions into a shared `scripts/utils.py` module to adhere to DRY principles.
- **Cross-Platform Hygiene**: Purged all hardcoded `/opt/homebrew/bin/` fallback paths from scripts and tests, replacing them with strict `shutil.which` checks that gracefully raise `FileNotFoundError` or `unittest.skipIf`.
- **Wrapper Bug**: Fixed a silent failure in the `./render` wrapper by adding an explicit `exit 1` when the date argument is missing.
- **Script Modernization**: Rewrote `check-status.py` to strip out polyglot bash/python hacks and fully conform to the standard PEP 723 Python architecture.
- **Test Integrity**: Introduced `tests/conftest.py` to fix absolute path resolution in tests, enabling the E2E `test_headless_engine.py` suite to run correctly. Tests now dynamically skip when local FFmpeg execution is broken, guaranteeing a clean CI/CD run.

## [v3.1.4] - 2026-08-25

### Changed
- **Test Optimization & Refactoring**: Disassembled the monolithic `main()` function in `build_headless_movie.py` into distinct pure functions (`parse_dive_list`, `load_and_filter_logs`, `detect_dives`, `calculate_highlight_windows`, `discover_videos`).
- Added robust unit tests (`tests/test_build_headless_movie.py`) using mocks to accurately measure logical coverage with `pytest-cov`, making the project test-friendly and resilient for future enhancements.
- Fixed a milliseconds precision bug in `format_srt_time`.

## [v3.1.3] - 2026-08-19

### Changed
- **Cross-Platform Instructions**: Formatted Windows package managers into a list, added a 5th Generic Linux approach for static binaries, and provided explicit PowerShell syntax for `uv run` line-continuations.

## [v3.1.2] - 2026-08-19

### Changed
- **Linux & Windows Compatibility Instructions**: Replaced single Debian `apt-get` documentation with specific package manager commands for top Linux distributions (Debian/Ubuntu, RHEL/CentOS, Gentoo, Slackware) and added a Generic Linux fallback for static binaries. Formatted Windows package managers (`winget`, `choco`, `scoop`) and added explicit PowerShell syntax examples for `uv run` to fix line-continuation bugs.

## [v3.1.1] - 2026-08-19

### Added
- **Dynamic Color Correction (Experimental)**: Added an automatic FFmpeg `colorbalance` filter that dynamically restores absorbed red light proportionally to the current dive depth (up to 40% at 30 meters). Note: Can amplify noise in deep shadows. Added `--water` argument (`saltwater`, `none`) to toggle the feature.
- **Paved Road Architecture**: Fully migrated project execution to `uv` and PEP 723 inline script metadata, dropping legacy virtual environments and wrapper requirements.

### Changed
- **Unified Documentation**: Merged `USAGE.md` into `README.md` for a single source of truth.
- **OS Independence**: Added explicit installation instructions for Windows (`winget`, `choco`, PowerShell) and macOS/Linux.
- **CLI Docs Consistency**: Corrected `--gap` and `--offset` help text in the code to strictly match actual default behavior.

## [v3.0.0] - 2026-08-18

### Added
- **Dynamic Telemetry Engine**: Replaced static overlay text with a dynamic SubRip (`.srt`) subtitle generator. Overlays now update second-by-second, syncing precise unrounded depth, temperature, and exact `ISO8601` timestamps directly from the CSV logs.
- **Telemetry Polish**: Date and Time are stripped from the subtitle for a cleaner look. Font size has been adjusted.

### Fixed
- **Time Synchronization Bug**: Removed automatic offset logic. The script now relies on native camera hardware RTC synchronization (zero-offset) by default, fixing the 3-minute drift between video and telemetry data.

## [v2.1.0] - 2026-08-12

### Added
- **Dynamic Color Correction (Experimental)**: Added an automatic FFmpeg `colorbalance` filter that dynamically restores absorbed red light proportionally to the current dive depth (up to 40% at 30 meters). Note: Can amplify noise in deep shadows. Added `--water` argument (`saltwater`, `none`) to toggle the feature.
- **Auto-Bootstrap**: Added logic to `./render` to automatically build the Python virtual environment and install dependencies if they are missing.
- **Portable Status Script**: Replaced hardcoded status checks with a universal `check-status.py` script that uses a portable shebang (`#!/usr/bin/env python3`).
- **Autonomous Architecture Rules**: Enforced strict rules inside `skill/github-release-management.md` for branching algorithms and release management.

### Fixed
- **Highlights Output Bug**: Ensured that the `-m highlights` command appends a `_highlights` suffix to the output filename to prevent overwriting the full movie render.
- **Temporary Files**: Added a safe, automated cleanup step using `shutil.rmtree` to remove `temp_slices_*` directories upon successful rendering.

## [v2.0.0] - 2026-06-27

### Added
- **Headless Migration**: Completely transitioned the project from the legacy DaVinci Resolve UI workflow to a fully headless FFmpeg-based pipeline.
- **Smart Highlights**: Upgraded the highlight extraction engine to support a 5-chapter chronological extraction for punchier reels.

### Changed
- **Entry Point**: Standardized all execution through the `./render` bash wrapper.

### Removed
- **DaVinci Resolve Dependencies**: Purged all legacy Lua API documentation and scripts associated with the UI-based pipeline.
