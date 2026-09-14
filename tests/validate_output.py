#!/usr/bin/env python3
"""
Validate that the headless engine produces a playable, correct video.
Runs the engine on mock data, then inspects the output with ffprobe.
"""
import os
import sys
import json
import shutil
import tempfile
import subprocess

import pandas as pd

from scripts.utils import get_ffmpeg_path, get_ffprobe_path
FFMPEG = get_ffmpeg_path()
FFPROBE = get_ffprobe_path()

EXPECTED = {
    "width": 3840,
    "height": 2160,
    "fps_min": 59.0,
    "codec": "h264",
    "min_duration_s": 0.5,
    "has_audio": True,
}


def create_mock_environment():
    """Create temp dirs with a 4K 60fps mock video and matching telemetry CSV."""
    test_dir = tempfile.mkdtemp(prefix="validate_")
    logs_dir = os.path.join(test_dir, "LOGS")
    media_dir = os.path.join(test_dir, "DCIM")
    os.makedirs(logs_dir)
    os.makedirs(media_dir)

    date = "2026-06-06"
    epoch = 1780740000  # 2026-06-06 ~10:00 UTC
    start_utc = "2026-06-06T10:00:00Z"

    # 1. Create a 4K 60fps mock video with audio (3 seconds)
    vid_path = os.path.join(media_dir, "PARA0001.MP4")
    cmd = [
        FFMPEG, "-y",
        "-f", "lavfi", "-i", "color=c=blue:s=3840x2160:r=60:d=3",
        "-f", "lavfi", "-i", "sine=frequency=440:duration=3",
        "-metadata", f"creation_time={start_utc}",
        "-c:v", "libx264", "-pix_fmt", "yuv420p",
        "-c:a", "aac", "-b:a", "128k",
        "-shortest", vid_path
    ]
    res = subprocess.run(cmd, capture_output=True, text=True)
    if res.returncode != 0:
        print(f"FAIL: Could not create mock video\n{res.stderr}")
        return None
    print(f"  Created mock video: {vid_path}")

    # 2. Create matching telemetry CSV (3 seconds of data)
    csv_path = os.path.join(logs_dir, "LOG01.csv")
    data = {
        "Time": [epoch + i for i in range(4)],
        "Temperature": [20.3, 20.1, 19.8, 19.5],
        "Depth": [2.0, 15.5, 30.2, 25.0],
        "ISO8601": [f"{date}T10:00:0{i}Z" for i in range(4)],
    }
    pd.DataFrame(data).to_csv(csv_path, index=False)
    print(f"  Created telemetry CSV: {csv_path}")

    return {
        "test_dir": test_dir,
        "logs_dir": logs_dir,
        "media_dir": media_dir,
        "date": date,
    }


import io
from contextlib import redirect_stdout, redirect_stderr
from scripts.build_headless_movie import main as build_main

def run_engine(env, mode, use_auto_offset=False):
    """Run the headless engine and return the output path + subprocess result."""
    suffix = "auto" if use_auto_offset else "manual"
    base_output = os.path.join(env["test_dir"], f"output_{mode}_{suffix}.mp4")
    expected_output = os.path.join(env["test_dir"], f"output_{mode}_{suffix}_dive1.mp4")
    args = ["--date", env["date"], "--logs_dir", env["logs_dir"], "--media_dir", env["media_dir"], "--output", base_output, "--mode", mode]
    if not use_auto_offset: args += ["--offset", "0"]

    print(f"
  Running main() with mode {mode}...")
    f_out = io.StringIO()
    f_err = io.StringIO()
    class MockResult:
        def __init__(self, stdout, stderr, returncode):
            self.stdout, self.stderr, self.returncode = stdout, stderr, returncode
            
    with redirect_stdout(f_out), redirect_stderr(f_err):
        ret = build_main(args)
        
    res = MockResult(f_out.getvalue(), f_err.getvalue(), ret)
    return expected_output, res


def inspect_video(path):
    """Use ffprobe to extract video metadata and return a structured report."""
    if not os.path.exists(path):
        return None

    cmd = [
        FFPROBE, "-v", "quiet",
        "-print_format", "json",
        "-show_format", "-show_streams",
        path
    ]
    res = subprocess.run(cmd, capture_output=True, text=True)
    if res.returncode != 0:
        return None

    data = json.loads(res.stdout)
    streams = data.get("streams", [])
    fmt = data.get("format", {})

    video = next((s for s in streams if s["codec_type"] == "video"), None)
    audio = next((s for s in streams if s["codec_type"] == "audio"), None)

    if not video:
        return None

    # Parse frame rate (e.g. "60/1" or "60000/1001")
    r_num, r_den = video.get("r_frame_rate", "0/1").split("/")
    fps = float(r_num) / float(r_den) if float(r_den) != 0 else 0

    return {
        "file_size_bytes": int(fmt.get("size", 0)),
        "duration_s": float(fmt.get("duration", 0)),
        "width": int(video.get("width", 0)),
        "height": int(video.get("height", 0)),
        "codec": video.get("codec_name", "unknown"),
        "fps": fps,
        "nb_frames": int(video.get("nb_frames", 0)),
        "has_audio": audio is not None,
        "audio_codec": audio.get("codec_name", "none") if audio else "none",
    }


def validate(info, label):
    """Compare video info against expected values. Return (pass_count, fail_count, messages)."""
    checks = []
    passed = 0
    failed = 0

    def check(name, condition, detail=""):
        nonlocal passed, failed
        if condition:
            checks.append(f"    ✅ {name}")
            passed += 1
        else:
            checks.append(f"    ❌ {name} — {detail}")
            failed += 1

    check("Resolution",
          info["width"] >= EXPECTED["width"] and info["height"] >= EXPECTED["height"],
          f"got {info['width']}x{info['height']}, expected {EXPECTED['width']}x{EXPECTED['height']}")

    check("Frame Rate",
          info["fps"] >= EXPECTED["fps_min"],
          f"got {info['fps']:.2f} fps, expected >= {EXPECTED['fps_min']}")

    check("Video Codec",
          info["codec"] == EXPECTED["codec"],
          f"got '{info['codec']}', expected '{EXPECTED['codec']}'")

    check("Duration",
          info["duration_s"] >= EXPECTED["min_duration_s"],
          f"got {info['duration_s']:.2f}s, expected >= {EXPECTED['min_duration_s']}s")

    check("Has Audio",
          info["has_audio"] == EXPECTED["has_audio"],
          f"audio stream {'found' if info['has_audio'] else 'missing'}")

    check("File Not Empty",
          info["file_size_bytes"] > 1000,
          f"file is only {info['file_size_bytes']} bytes")

    check("Has Frames",
          info["nb_frames"] > 0,
          f"got {info['nb_frames']} frames")

    print(f"\n  [{label}] — {passed} passed, {failed} failed:")
    for c in checks:
        print(c)

    return passed, failed


def main():
    print("=" * 60)
    print("  HEADLESS ENGINE OUTPUT VALIDATION")
    print("=" * 60)

    # Setup
    print("\n📦 Creating mock environment...")
    env = create_mock_environment()
    if not env:
        print("ABORT: Could not create mock environment.")
        sys.exit(1)

    total_passed = 0
    total_failed = 0

    # Test 1: Highlights with manual offset
    output, res = run_engine(env, "highlights", use_auto_offset=False)
    if os.path.exists(output):
        info = inspect_video(output)
        if info:
            p, f = validate(info, "Highlights (--offset 0)")
            total_passed += p
            total_failed += f
            print(f"    📐 {info['width']}x{info['height']} | {info['fps']:.0f}fps | "
                  f"{info['codec']} | {info['duration_s']:.2f}s | "
                  f"{info['nb_frames']} frames | {info['file_size_bytes']/1024:.0f} KB")
        else:
            print("    ❌ ffprobe could not read the output file")
            total_failed += 1
    else:
        print(f"    ❌ Output file not created")
        print(f"    stdout: {res.stdout[-500:]}")
        print(f"    stderr: {res.stderr[-500:]}")
        total_failed += 1

    # Test 2: Highlights with auto-offset
    output, res = run_engine(env, "highlights", use_auto_offset=True)
    if os.path.exists(output):
        info = inspect_video(output)
        if info:
            p, f = validate(info, "Highlights (auto-offset)")
            total_passed += p
            total_failed += f
            print(f"    📐 {info['width']}x{info['height']} | {info['fps']:.0f}fps | "
                  f"{info['codec']} | {info['duration_s']:.2f}s | "
                  f"{info['nb_frames']} frames | {info['file_size_bytes']/1024:.0f} KB")
        else:
            print("    ❌ ffprobe could not read the output file")
            total_failed += 1
    else:
        print(f"    ❌ Output file not created")
        print(f"    stdout: {res.stdout[-500:]}")
        print(f"    stderr: {res.stderr[-500:]}")
        total_failed += 1

    # Test 3: Full mode with auto-offset
    output, res = run_engine(env, "full", use_auto_offset=True)
    if os.path.exists(output):
        info = inspect_video(output)
        if info:
            p, f = validate(info, "Full Movie (auto-offset)")
            total_passed += p
            total_failed += f
            print(f"    📐 {info['width']}x{info['height']} | {info['fps']:.0f}fps | "
                  f"{info['codec']} | {info['duration_s']:.2f}s | "
                  f"{info['nb_frames']} frames | {info['file_size_bytes']/1024:.0f} KB")
        else:
            print("    ❌ ffprobe could not read the output file")
            total_failed += 1
    else:
        print(f"    ❌ Output file not created")
        print(f"    stdout: {res.stdout[-500:]}")
        print(f"    stderr: {res.stderr[-500:]}")
        total_failed += 1

    # Cleanup
    shutil.rmtree(env["test_dir"])

    # Final Report
    print("\n" + "=" * 60)
    if total_failed == 0:
        print(f"  🎉 ALL CHECKS PASSED ({total_passed}/{total_passed})")
    else:
        print(f"  ⚠️  {total_failed} CHECK(S) FAILED ({total_passed} passed, {total_failed} failed)")
    print("=" * 60)
    sys.exit(1 if total_failed > 0 else 0)


if __name__ == "__main__":
    main()
