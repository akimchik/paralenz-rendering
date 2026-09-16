# /// script
# requires-python = ">=3.10"
# dependencies = [
#     "pandas",
# ]
# ///

import sys
import os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

import pandas as pd
import subprocess
import json
import glob
import argparse
from datetime import datetime, timezone
import shutil

try:
    from scripts.utils import get_ffmpeg_path, get_meta
except ModuleNotFoundError:
    import urllib.request
    import importlib.util
    branch = os.environ.get("PRLNZ_BRANCH", "main")
    url = f"https://raw.githubusercontent.com/akimchik/paralenz-rendering/{branch}/scripts/utils.py"
    try:
        req = urllib.request.Request(url)
        with urllib.request.urlopen(req) as response:
            code = response.read().decode('utf-8')
        spec = importlib.util.spec_from_loader('scripts.utils', loader=None)
        utils_module = importlib.util.module_from_spec(spec)
        exec(code, utils_module.__dict__)
        get_ffmpeg_path = utils_module.get_ffmpeg_path
        get_meta = utils_module.get_meta
    except Exception as e:
        print(f"Error dynamically loading utils.py from branch '{branch}': {e}")
        sys.exit(1)

def run_cmd(cmd):
    result = subprocess.run(cmd, capture_output=True, text=True)
    if result.returncode != 0:
        print(f"Command Error: {' '.join(cmd)}")
        print(f"Stderr: {result.stderr}")
    return result

def format_srt_time(seconds):
    h = int(seconds // 3600)
    m = int((seconds % 3600) // 60)
    s = int(seconds % 60)
    ms = round((seconds - int(seconds)) * 1000)
    if ms == 1000:
        ms = 0
        s += 1
        if s == 60:
            s = 0
            m += 1
            if m == 60:
                m = 0
                h += 1
    return f"{h:02d}:{m:02d}:{s:02d},{ms:03d}"

def get_color_correction_filter(avg_depth, max_depth=30.0, max_boost=0.4, water_type='saltwater'):
    if water_type == 'none' or avg_depth <= 0:
        return ""
    
    boost = min(avg_depth / max_depth, 1.0) * max_boost
    mid = 0.5 + (boost * 0.75) # Cap the curve bending slightly for natural look
    
    if water_type == 'saltwater':
        return f"curves=r='0/0 0.5/{mid:.3f} 1/1',"
    elif water_type == 'freshwater':
        return f"curves=r='0/0 0.5/{mid:.3f} 1/1':b='0/0 0.5/{mid:.3f} 1/1',"
    return ""

def parse_dive_list(dive_list_str):
    if not dive_list_str:
        return []
    return [int(d.strip()) for d in dive_list_str.split(',')]

def load_and_filter_logs(logs_dir, date):
    log_files = glob.glob(os.path.join(logs_dir, "*.csv"))
    if not log_files:
        return pd.DataFrame()
    df = pd.concat([pd.read_csv(f) for f in log_files])
    df = df[df['ISO8601'].str.startswith(date, na=False)]
    if df.empty:
        return df
    df['Time'] = pd.to_numeric(df['Time'], errors='coerce')
    return df.dropna(subset=['Time']).sort_values(by='Time')

def detect_dives(df, gap):
    if df.empty:
        return []
    df['session'] = (df['Time'].diff() > gap).cumsum()
    return [g for _, g in df.groupby('session') if g['Depth'].max() > 1.0]

def discover_videos(media_dir):
    videos = []
    for f in glob.glob(os.path.join(media_dir, "*.MP4")):
        m = get_meta(f, min_width=3000)
        if m:
            videos.append(m)
    videos.sort(key=lambda x: x['ts'])
    return videos

def calculate_highlight_windows(dive, d_start, d_end, mode):
    windows = []
    if mode == 'highlights':
        entry = dive[dive['Depth'] >= 2.0].head(1)
        if not entry.empty:
            t = entry.iloc[0]['Time']
            windows.append((t - 10, t + 30))
        dive_diff = dive['Depth'].diff()
        if not dive_diff.empty:
            t = dive.iloc[dive_diff.argmax()]['Time']
            windows.append((t - 15, t + 30))
        mid_time = d_start + (d_end - d_start) * 0.45
        mid_row = dive.iloc[(dive['Time'] - mid_time).abs().argsort()[:1]]
        if not mid_row.empty:
            t = mid_row.iloc[0]['Time']
            windows.append((t - 25, t + 25))
        max_t = dive.iloc[dive['Depth'].argmax()]['Time']
        windows.append((max_t - 30, max_t + 30))
        ascent = dive[(dive['Depth'] <= 5.0) & (dive['Time'] > d_start + (d_end - d_start) * 0.75)].head(1)
        if not ascent.empty:
            t = ascent.iloc[0]['Time']
            windows.append((t - 15, t + 25))
        windows.sort(key=lambda x: x[0])
    else:
        windows.append((d_start - 60, d_end + 60))
    return windows

def get_best_hardware_encoder(ffmpeg_bin):
    import subprocess
    try:
        res = subprocess.run([ffmpeg_bin, '-encoders'], capture_output=True, text=True, timeout=2)
        if res.returncode == 0:
            encoders = res.stdout
            for enc in ['h264_videotoolbox', 'h264_nvenc', 'h264_qsv', 'h264_amf', 'h264_vaapi']:
                if enc in encoders:
                    return enc
    except Exception:
        pass
    return 'libx264'

def build_ffmpeg_cmd(ffmpeg_bin, s_start, s_dur, in_path, vf, out_path, hw_encoder='h264_videotoolbox'):
    base_cmd = [ffmpeg_bin, '-y', '-ss', str(s_start), '-t', str(s_dur), '-i', in_path, '-vf', vf]
    if hw_encoder != 'libx264':
        base_cmd.extend(['-c:v', hw_encoder, '-b:v', '80M', '-r', '60'])
    else:
        base_cmd.extend(['-c:v', 'libx264', '-crf', '18', '-preset', 'fast', '-r', '60'])
    base_cmd.extend(['-c:a', 'aac', '-b:a', '320k', out_path])
    return base_cmd

def build_overlay_slices(dives, videos, calc_offset, temp_dir, mode, target_dives, water_type):
    processed_by_dive = {}
    ffmpeg_bin = get_ffmpeg_path()
    hw_encoder = get_best_hardware_encoder(ffmpeg_bin)
    print(f"Using video encoder: {hw_encoder}")

    for d_idx, dive in enumerate(dives):
        current_dive_id = d_idx + 1
        if target_dives and current_dive_id not in target_dives:
            continue

        processed_by_dive[current_dive_id] = []
        d_start, d_end = dive['Time'].min(), dive['Time'].max()
        print(f"Processing Dive #{current_dive_id}: {d_start} to {d_end}")

        windows = calculate_highlight_windows(dive, d_start, d_end, mode)

        for win_idx, (w_start, w_end) in enumerate(windows):
            for v in videos:
                v_start = v['ts'] + calc_offset
                v_end = v_start + v['dur']

                overlap_start = max(w_start, v_start)
                overlap_end = min(w_end, v_end)

                if overlap_start < overlap_end:
                    s_start = overlap_start - v_start
                    s_dur = overlap_end - overlap_start
                    out_s = os.path.join(temp_dir, f"s_{d_idx}_{win_idx}_{os.path.basename(v['path'])}")
                    srt_path = os.path.join(temp_dir, f"sub_{d_idx}_{win_idx}_{os.path.basename(v['path'])}.srt")

                    slice_df = dive[(dive['Time'] >= overlap_start) & (dive['Time'] <= overlap_end)]
                    with open(srt_path, 'w') as f_srt:
                        for idx_s in range(len(slice_df)):
                            row = slice_df.iloc[idx_s]
                            rel_t = row['Time'] - overlap_start
                            rel_t = max(0, rel_t)

                            if idx_s + 1 < len(slice_df):
                                next_rel_t = slice_df.iloc[idx_s+1]['Time'] - overlap_start
                                end_t = min(next_rel_t, s_dur)
                            else:
                                end_t = min(rel_t + 1.0, s_dur)

                            f_srt.write(f"{idx_s+1}\n")
                            f_srt.write(f"{format_srt_time(rel_t)} --> {format_srt_time(end_t)}\n")
                            f_srt.write(f"Depth: {row['Depth']}m | Temp: {row['Temperature']}C\n\n")

                    escaped_srt = __import__('os').path.relpath(srt_path).replace('\\', '/')
                    avg_depth = slice_df['Depth'].mean() if not slice_df.empty else 0.0
                    cc_filter = get_color_correction_filter(avg_depth, water_type=water_type)

                    vf_arg = f"{cc_filter}subtitles=f='{escaped_srt}':force_style='FontSize=5,Alignment=7,BorderStyle=3,Outline=1,Shadow=0,MarginV=15,MarginR=15,FontName=Arial'"

                    cmd = build_ffmpeg_cmd(ffmpeg_bin, s_start, s_dur, v['path'], vf_arg, out_s, hw_encoder=hw_encoder)
                    res = run_cmd(cmd)
                    
                    if res.returncode != 0 and hw_encoder != 'libx264':
                        print(f" -> Hardware encoding ({hw_encoder}) failed, falling back to software for {os.path.basename(v['path'])}")
                        cmd = build_ffmpeg_cmd(ffmpeg_bin, s_start, s_dur, v['path'], vf_arg, out_s, hw_encoder='libx264')
                        res = run_cmd(cmd)

                    if os.path.exists(out_s):
                        processed_by_dive[current_dive_id].append(out_s)
                        print(f" -> Merged: {os.path.basename(v['path'])} | Extracted {s_dur:.1f}s | Output: {os.path.basename(out_s)}")
                    else:
                        print(f" -> Failed to create slice from {os.path.basename(v['path'])}")
                        
        if not processed_by_dive[current_dive_id]:
            del processed_by_dive[current_dive_id]
            
    return processed_by_dive

def concatenate_slices(processed, output, temp_dir):
    if not processed:
        return False

    list_path = os.path.join(temp_dir, "list.txt")
    with open(list_path, 'w') as f:
        for p in processed:
            f.write(f"file '{p}'\n")

    final_cmd = [get_ffmpeg_path(), '-y', '-f', 'concat', '-safe', '0', '-i', list_path, '-c', 'copy', '-movflags', '+faststart', os.path.abspath(output)]
    res = run_cmd(final_cmd)

    return res.returncode == 0 and os.path.exists(output)

def main(args=None):
    parser = argparse.ArgumentParser()
    parser.add_argument("--date", required=True)
    parser.add_argument("--logs_dir", required=True)
    parser.add_argument("--media_dir", required=True)
    parser.add_argument("--output", required=True)
    parser.add_argument("--mode", choices=['highlights', 'full'], default='full')
    parser.add_argument("--offset", type=int, default=None, help="Force manual offset in seconds.")
    parser.add_argument("--dive_list", type=str, default="", help="Comma-separated list of dive IDs.")
    parser.add_argument("--gap", type=int, default=7200, help="Seconds of gap to split session.")
    parser.add_argument("--water", choices=['saltwater', 'none'], default='saltwater', help="Water type.")

    parsed = parser.parse_args(args)

    target_dives = parse_dive_list(parsed.dive_list)

    df = load_and_filter_logs(parsed.logs_dir, parsed.date)
    if df.empty:
        print(f"Error: No valid logs matching date {parsed.date} found.")
        return 1

    dives = detect_dives(df, parsed.gap)
    print(f"Detected Dives: {len(dives)}")
    if not dives:
        print("Error: No valid dives detected in telemetry.")
        return 1

    videos = discover_videos(parsed.media_dir)
    print(f"Indexed High-Res Videos (all): {len(videos)}")

    calc_offset = parsed.offset if parsed.offset is not None else 0
    if parsed.offset is not None:
        print(f"Using manual offset: {calc_offset}s")
    else:
        print("Using default zero-offset (Camera RTC Sync).")

    day_start = dives[0]['Time'].min() - 43200
    day_end = dives[-1]['Time'].max() + 43200
    videos = [v for v in videos if (v['ts'] + calc_offset) >= day_start and (v['ts'] + calc_offset) <= day_end]
    print(f"Filtered to target date: {len(videos)} video(s)")

    if not videos:
        print("Error: No high-res videos found for the target date.")
        return 1

    temp_dir = os.path.abspath(f"temp_slices_{parsed.mode}")
    os.makedirs(temp_dir, exist_ok=True)

    try:
        processed_by_dive = build_overlay_slices(dives, videos, calc_offset, temp_dir, parsed.mode, target_dives, parsed.water)

        if processed_by_dive:
            all_success = True
            for dive_id, processed in processed_by_dive.items():
                base_out, ext = os.path.splitext(parsed.output)
                if f"dive{dive_id}" not in base_out:
                    dive_output = f"{base_out}_dive{dive_id}{ext}"
                else:
                    dive_output = parsed.output
                    
                success = concatenate_slices(processed, dive_output, temp_dir)
                if success:
                    print(f"\nSUCCESS! Rendered Dive #{dive_id}: {os.path.abspath(dive_output)}")
                else:
                    print(f"\nCRITICAL ERROR: Final concatenation failed for Dive #{dive_id}.")
                    all_success = False
            return 0 if all_success else 1
        else:
            print("\nError: No correlated clips found.")
            return 1
    finally:
        try:
            import shutil
            shutil.rmtree(temp_dir)
        except Exception:
            pass

if __name__ == "__main__":
    import sys
    sys.exit(main())
