---
name: paralenz-rendering
description: Automates 4K 60fps movie assembly and highlight generation for the Paralenz camera using a headless FFmpeg pipeline. Use this skill when managing the akimchik/paralenz-rendering project to ensure architectural consistency.
---

# Paralenz Rendering Standards (v3.2.1 Modular Architecture)

This skill enforces strict professional mandates for the headless FFmpeg architecture, fully deprecating the legacy DaVinci Resolve integration.

## Core Architecture Mandates

### 0. Agent Execution Protocol (The Ball of Thread)
- **AGENT PROTOCOL:** Before taking any action (creating a branch, writing code, bumping a version), the AI MUST explicitly read this file and related `skill/` documents, map its proposed changes to the rules, and seek approval via an Implementation Plan.
- **Mandatory Testing (TDD) & Coverage:** Code without tests is dead. The project requires a minimum of **80% test coverage**. EVERY new feature, bugfix, or refactoring MUST be accompanied by corresponding unit tests (using `unittest.mock` for system calls).
- **Modular Code Design:** No monolithic `main()` functions. ALL business logic, mathematical calculations, and FFmpeg command generation must be broken out into testable, pure functions (e.g., `calculate_highlight_windows`, `build_overlay_slices`) that take direct arguments (not `argparse.Namespace`) so they can be unit-tested seamlessly.
- **Test Command:** You MUST run the test suite via `uv run --with pandas --with pytest --with pytest-cov pytest -v --cov=scripts --cov-report=term-missing tests/` locally and ensure all tests pass and coverage requirements are met before committing any code.
- **Architecture Modifications Only:** Modifying actual existing codebase files is vastly preferred over writing brand-new one-off scripts. All helper scripts (like offset calculators) must be built as CLI tools with `def main(args=None):` for full testability. Do NOT do snap decisions like custom test scripts, temporary bash hacks, or fast solutions that break project logic or are obvious workarounds.

### 1. Headless Entry Point
- **The Execution (uv):** The canonical execution method is `uv run scripts/build_headless_movie.py`. The `./render` bash wrapper is a convenience entry point that delegates to `uv run` internally. Do NOT instruct users to run raw `python3` or manual `pip install` workflows.
- **Dependencies (Paved Road):** The project relies on PEP 723 inline dependencies handled by `uv`. Do NOT use, create, or instruct users about `pip`, `venv`, `source .venv/bin/activate`, or `requirements.txt`.
- **Environment Variables:** Media paths are securely stored in `.env` (`SEARCH_DIR` and `LOGS_DIR`). Never hardcode these.

### 2. Time-Drift Offset Calculation
- **Camera RTC Synchronization:** Videos and telemetry logs are natively synchronized via the camera's internal Real-Time Clock (RTC). The script MUST default to a zero-offset rather than attempting to auto-calculate drift.
- **Time Zones:** Dive logs (`.CSV`) use UTC. When parsing video metadata with `ffprobe`, always ensure the parsed datetime object is explicitly marked as UTC (`replace(tzinfo=timezone.utc)`).

### 3. Rendering Modes
1. **Full Mode (`-m full`)**: Chronologically joins all high-res MP4s for a given day into a single seamless video with a generated HUD telemetry overlay.
2. **Highlights Mode (`-m highlights`)**: Extracts up to five chapters of action-packed slices from the footage (approx. ~3.9m total) instead of joining them fully.

### 4. Cross-Platform Compatibility
- **Strictly Avoid Fallbacks:** Never hardcode paths like `/opt/homebrew/bin/ffmpeg`. The `or "/opt/homebrew/..."` fallback pattern is explicitly forbidden. Rely strictly on Python's `shutil.which("ffmpeg")` and throw a hard `FileNotFoundError` if missing. This applies to ALL files: scripts, tests, and utilities.

## Related Skills
- **Python Telemetry:** Refer to `skill/python-telemetry.md` for standards on how to parse and smooth the `.CSV` telemetry data using pandas.
