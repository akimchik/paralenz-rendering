# /// script
# requires-python = ">=3.10"
# dependencies = [
#     "pandas",
# ]
# ///

import sys
import os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

import glob
import argparse
from datetime import datetime, timezone
import shutil

from scripts.utils import get_meta

def analyze_videos_in_window(media_dir, window_start, window_end):
    videos = []
    for f in glob.glob(os.path.join(media_dir, "*.MP4")):
        if "lowres" in f.lower() or "/._" in f:
            continue
        m = get_meta(f, basename_only=True)
        if m:
            videos.append(m)

    videos.sort(key=lambda x: x['ts'])

    filtered_videos = []
    for v in videos:
        # Check if the video time overlaps with the target window broadly
        if v['ts'] > window_start and v['ts'] < window_end:
            filtered_videos.append(v)

    return filtered_videos

def main(args=None):
    parser = argparse.ArgumentParser(description="Check video metadata within a specific epoch window.")
    parser.add_argument("--media_dir", required=True, help="Directory containing .MP4 videos")
    parser.add_argument("--start", type=float, required=True, help="Start epoch timestamp")
    parser.add_argument("--end", type=float, required=True, help="End epoch timestamp")

    parsed = parser.parse_args(args)

    videos = analyze_videos_in_window(parsed.media_dir, parsed.start, parsed.end)

    print(f"Files in dive window ({parsed.start} to {parsed.end}):")
    if not videos:
        print("No videos found in the specified window.")
        return 1

    for v in videos:
        start_fmt = datetime.fromtimestamp(v['ts'], tz=timezone.utc).strftime('%H:%M:%S')
        end_epoch = v['ts'] + v['dur']
        print(f"{v['path']}: start={v['ts']} ({start_fmt}), dur={v['dur']:.1f}, end={end_epoch:.1f}")
    return 0

if __name__ == '__main__':
    import sys
    sys.exit(main())
