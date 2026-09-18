# Headless Dive Automation (v3.2.1)

Automate the creation of 4K 60fps diving movies and highlight reels directly from your camera's DCIM folder, integrated with real-time telemetry data.

*As of v2.0.0, this project has fully migrated to a headless FFmpeg-based architecture for maximum stability and speed, deprecating the legacy DaVinci Resolve integration.*

## Table of Contents
1. [Features](#features)
2. [Prerequisites](#prerequisites)
3. [Quick Start (Paved Road)](#quick-start-paved-road)
4. [Local Configuration](#local-configuration)
5. [CLI Arguments Reference](#cli-arguments-reference)
6. [Core Advanced Features](#core-advanced-features)
7. [Professional Standards](#professional-standards)

## Features

- **Universal Multi-Dive Support:** Automatically detects multiple dive sessions per day and correlates video clips using recording timestamps.
- **Headless Pipeline:** Renders directly from the terminal without needing any heavy UI software.
- **Movie Assembly:** Chronologically joins high-res MP4s and builds a seamless video.
- **AI-Free Highlights:** Creates a punchy highlight reel by taking three 3-second "action slices" (Start, Mid, End) from every clip.
- **Dynamic HUD:** Overlays real-time depth and temperature telemetry via dynamic SubRip (`.srt`) subtitle generation, seamlessly synchronized using camera RTC.
- **Strict Filtering:** Implements precise single-day filtering to ensure only the target date's media is processed.
- **60fps Stability:** Generates standard 60fps files without dropped frames.
- **Autonomous Verification:** Includes a testing framework for CI/CD integration.

## Prerequisites

### 1. Python Environment (`uv`)
This project requires [uv](https://github.com/astral-sh/uv), a lightning-fast Python package manager. The environment and dependencies are automatically managed via PEP 723 inline script metadata.

**macOS / Generic Linux:**
```bash
curl -LsSf https://astral.sh/uv/install.sh | sh
```

**Windows (PowerShell):**
```powershell
powershell -ExecutionPolicy ByPass -c "irm https://astral.sh/uv/install.ps1 | iex"
```

### 2. FFmpeg
Ensure `ffmpeg` and `ffprobe` are installed on your system.

**macOS:**
> [!WARNING]
> The default `brew install ffmpeg` is currently compiled **without** the subtitles filter (`libass`), which will cause the render to fail when building the telemetry HUD. 

To fix this, you must either download a full static build or compile it with `libass` support:
1. **Download Static Build (Recommended):** Download FFmpeg and FFprobe from [evermeet.cx](https://evermeet.cx/ffmpeg/), unzip them, and place them in `/usr/local/bin` or your `$PATH`.
2. **Compile via Homebrew:** 
   ```bash
   brew tap homebrew-ffmpeg/ffmpeg
   brew install homebrew-ffmpeg/ffmpeg/ffmpeg --with-libass
   ```

**Linux:**
- *Debian/Ubuntu:* `sudo apt-get update && sudo apt-get install -y ffmpeg`
- *RHEL/CentOS:* `sudo dnf install ffmpeg`
- *Gentoo:* `sudo emerge --ask media-video/ffmpeg`
- *Slackware:* `sudo sbopkg -i ffmpeg`
- *Generic Linux (Static Binary):* Download a pre-compiled static build (e.g., from [johnvansickle.com/ffmpeg](https://johnvansickle.com/ffmpeg/)) and extract it to your `$PATH`.

**Windows:**
- *Winget (Default):* `winget install ffmpeg`
- *Chocolatey:* `choco install ffmpeg`
- *Scoop:* `scoop install ffmpeg`

## Quick Start (Paved Road)

Thanks to `uv` and PEP 723, you can execute the core engine directly from GitHub without cloning the repository or setting up `.env` files. `uv` will dynamically download the script, create an ephemeral environment, and install `pandas` in milliseconds.

**macOS / Linux (Bash/Zsh):**
```bash
uv run https://raw.githubusercontent.com/akimchik/paralenz-rendering/main/scripts/build_headless_movie.py \
  --date 2026-06-27 \
  --logs_dir /path/to/logs \
  --media_dir /path/to/media \
  --output my_dive.mp4
```

**Windows (PowerShell):**
```powershell
uv run https://raw.githubusercontent.com/akimchik/paralenz-rendering/main/scripts/build_headless_movie.py `
  --date 2026-06-27 `
  --logs_dir C:\data\logs `
  --media_dir C:\data\media `
  --output C:\data\media\my_dive.mp4
```

## Local Configuration (Using `.env`)

The python engine can automatically read your `.env` file, allowing you to omit long paths from your commands.

1. **Copy the template:**
   ```bash
   cp .env.example .env
   ```
2. **Edit `.env`:**
   - `SEARCH_DIR`: Path to your camera's DCIM folder (where `.MP4` files live).
   - `LOGS_DIR`: Path to your dive logs folder (where `.CSV` files live).

### Basic Usage (With `.env` configured)
Once `.env` is configured, you only need to provide the date! The script will automatically generate the output filename.
```bash
uv run scripts/build_headless_movie.py --date 2026-06-27
```

### Manual Usage (Without `.env`)
If you prefer not to use `.env`, you must provide all paths explicitly:
```bash
uv run scripts/build_headless_movie.py \
  --date 2026-06-27 \
  --logs_dir ./data/logs \
  --media_dir ./data/media \
  --output my_dive.mp4
```


### Advanced Execution Examples

**1. Generate 5-Chapter Smart Highlights for Dive 1:**
```bash
uv run scripts/build_headless_movie.py \
  --date 2026-06-27 --logs_dir ./data/logs --media_dir ./data/media --output highlights.mp4 \
  --mode highlights --dive_list 1
```

**2. Add a custom 2-hour offset if the camera RTC drifted:**
```bash
uv run scripts/build_headless_movie.py \
  --date 2026-06-27 --logs_dir ./data/logs --media_dir ./data/media --output offset_dive.mp4 \
  --offset 7200
```

**3. Disable dynamic color correction (if using physical red filters):**
```bash
uv run scripts/build_headless_movie.py \
  --date 2026-06-27 --logs_dir ./data/logs --media_dir ./data/media --output raw_color.mp4 \
  --water none
```

## CLI Arguments Reference

| Argument | Required | Default | Description |
| :--- | :---: | :---: | :--- |
| `--date` | **Yes** | - | Target ISO8601 date (e.g. `2026-06-27`). |
| `--logs_dir` | **Yes** | - | Path to directory containing `.CSV` logs. |
| `--media_dir` | **Yes** | - | Path to directory containing `.MP4` files. |
| `--output` | **Yes** | - | Output path for the rendered MP4 file. |
| `--mode` | No | `full` | `full` (renders entire sessions) or `highlights` (5-chapter smart slices). |
| `--offset` | No | `0` | Force manual time sync offset in seconds between telemetry and video. |
| `--dive_list` | No | `""` | Comma-separated list of Dive IDs to render (e.g. `1,3,4`). Processes all if empty. |
| `--gap` | No | `1800` | Gap threshold in seconds to detect new dives. Default is 30 mins (1800s). |
| `--water` | No | `saltwater` | `saltwater` (boosts red), `freshwater` (boosts magenta), or `none` (disables correction). |

> [!WARNING]
> The dynamic color correction (`--water {saltwater,freshwater,none}`) is an advanced `curves` filter that restores absorbed colors proportionally to the current dive depth. It targets mid-tones to naturally recover colors without amplifying noise in deep shadows.

## Core Advanced Features

### Global Multi-Dive Support
The system automatically detects multiple dives in your logs using a configurable gap (default: 30 mins). It correlates each video clip to the correct dive using its recording timestamp.
- **Auto-Sync:** If you have 3 dives in one day, the script will generate 3 separate HUD profiles and sync the correct data to the correct footage automatically.
- **Session Detection:** It identifies gaps in activity to separate "Dives" from "Surface intervals."

> [!TIP]
> The default gap is `1800` seconds (30 mins) to accommodate very long surface intervals. If you need tighter split thresholds, pass a lower value using `--gap`.

### Dynamic HUD
A real-time depth and temperature HUD is injected into the video using dynamic SubRip (`.srt`) subtitle generation.

> [!NOTE]
> The script relies on native camera hardware RTC synchronization (zero-offset) by default, ensuring perfect alignment between the `.MP4` files and `.CSV` telemetry logs. A manual offset can be supplied via `--offset` only if drift occurs.

## Professional Standards

- **Testing:** Code without tests is dead code. Testing is mandatory for all new features. Comprehensive unit and integration tests are located in `tests/`. Agents are strictly required to verify their changes locally before committing (`uv run --with pandas --with pytest pytest -v tests/`).
- **Privacy:** Local paths and binary assets are strictly excluded via `.gitignore`.
