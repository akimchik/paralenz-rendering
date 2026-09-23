# /// script
# requires-python = ">=3.10"
# dependencies = [
#     "pandas",
#     "python-dotenv",
# ]
# ///

import sys
import os
import shutil
import concurrent.futures
import argparse
import glob
import datetime
import re
import subprocess

try:
    from dotenv import load_dotenv, find_dotenv
    load_dotenv(find_dotenv(usecwd=True))
except ImportError:  # pragma: no cover
    pass
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

import pandas as pd
from datetime import timezone

try:
    from scripts.utils import get_ffmpeg_path, get_meta
except ModuleNotFoundError:  # pragma: no cover
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
    except Exception as e:  # pragma: no cover
        print(f"Error dynamically loading utils.py from branch '{branch}': {e}")
        sys.exit(1)

def run_cmd(cmd, total_duration=None):
    process = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True, bufsize=1)
    time_regex = re.compile(r"time=(\d{2}):(\d{2}):(\d{2})\.(\d{2})")
    
    last_lines = []
    
    for line in process.stdout:
        last_lines.append(line)
        if len(last_lines) > 20:
            last_lines.pop(0)
            
        match = time_regex.search(line)
        if match:
            h, m, s, ms = match.groups()
            curr_sec = float(h)*3600 + float(m)*60 + float(s) + float(ms)/100.0
            
            if total_duration and total_duration > 0:
                pct = (curr_sec / total_duration) * 100
                print(f"\r⏳ Render Progress: {h}:{m}:{s} / {format_srt_time(total_duration).replace(',', '.')} ({pct:.1f}%)", end="", flush=True)
            else:
                print(f"\r⏳ Render Progress: {h}:{m}:{s}", end="", flush=True)
            
    process.wait()
    print() # clear the progress line
    
    if process.returncode != 0:
        print(f"Command Error: {' '.join(cmd)}")
        print("Last output:")
        print("".join(last_lines))
        
    class DummyResult:
        def __init__(self, returncode, stderr):
            self.returncode = returncode
            self.stderr = stderr
            
    return DummyResult(process.returncode, "".join(last_lines))

def _info(msg): # pragma: no cover
    print(msg)

def format_srt_time(seconds):
    h = int(seconds // 3600)
    m = int((seconds % 3600) // 60)
    s = int(seconds % 60)
    ms = round((seconds - int(seconds)) * 1000)
    if ms >= 1000:
        ms -= 1000
        s += 1
        if s == 60:
            s = 0
            m += 1
            if m == 60:
                m = 0
                h += 1
    return f"{h:02d}:{m:02d}:{s:02d},{ms:03d}"

def get_color_correction_filter(water_type='saltwater'):
    if water_type == 'saltwater':
        return "curves=r='0/0 0.5/0.58 1/1':b='0/0 0.5/0.45 1/1',"
    elif water_type == 'freshwater':
        return "curves=r='0/0 0.5/0.55 1/1':g='0/0 0.5/0.45 1/1',"
    return ""

def parse_dive_list(dive_list_str):
    if not dive_list_str:
        return []
    return [int(d.strip()) for d in dive_list_str.split(',')]

def load_and_filter_logs(logs_dir, target_dates):
    log_files = glob.glob(os.path.join(logs_dir, "*.csv"))
    if not log_files:
        return pd.DataFrame()
    df = pd.concat([pd.read_csv(f) for f in log_files])
    
    if target_dates:
        # Filter if ISO8601 starts with any of the target dates
        df = df[df['ISO8601'].str[:10].isin(target_dates)]
        
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
    mp4_files = glob.glob(os.path.join(media_dir, "*.MP4"))
    _info(f"Found {len(mp4_files)} .MP4 files. Reading metadata...")
    
    with concurrent.futures.ThreadPoolExecutor(max_workers=min(16, (os.cpu_count() or 4) * 2)) as executor:
        results = executor.map(lambda f: get_meta(f, min_width=1000), mp4_files)
        for m in results:
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
    """Finds the best hardware encoder actually supported by the current system."""
    for enc in ['h264_videotoolbox', 'h264_nvenc', 'h264_qsv', 'h264_amf', 'h264_vaapi']:
        try:
            cmd = [
                ffmpeg_bin, '-v', 'error', '-y', '-f', 'lavfi', 
                '-i', 'color=size=1920x1080:rate=1:duration=0.1',
                '-c:v', enc, '-f', 'null', '-'
            ]
            if subprocess.run(cmd, capture_output=True, timeout=2).returncode == 0:
                return enc
        except Exception:  # pragma: no cover
            continue
    return 'libx264'

def build_ffmpeg_cmd(ffmpeg_bin, s_start, s_dur, in_path, vf, out_path, hw_encoder='h264_videotoolbox'):
    base_cmd = [ffmpeg_bin, '-y', '-ss', str(s_start), '-t', str(s_dur), '-i', in_path, '-vf', vf]
    if hw_encoder != 'libx264':
        base_cmd.extend(['-c:v', hw_encoder, '-b:v', '80M', '-r', '60'])
    else:
        base_cmd.extend(['-c:v', 'libx264', '-crf', '18', '-preset', 'fast', '-r', '60'])
    base_cmd.extend(['-c:a', 'aac', '-b:a', '320k', out_path])
    return base_cmd

def process_dive(dive_id, dive, windows, videos, calc_offset, temp_dir, output_file, water_type, ffmpeg_bin, hw_encoder):
    list_path = os.path.join(temp_dir, f"list_{dive_id}.txt")
    srt_path = os.path.join(temp_dir, f"sub_{dive_id}.srt")
    
    current_virtual_time = 0.0
    srt_idx = 1
    has_clips = False

    with open(list_path, 'w') as f_list, open(srt_path, 'w') as f_srt:
        for (w_start, w_end) in windows:
            for v in videos:
                v_start = v['ts'] + calc_offset
                v_end = v_start + v['dur']

                overlap_start = max(w_start, v_start)
                overlap_end = min(w_end, v_end)

                if overlap_start < overlap_end:
                    has_clips = True
                    s_start = overlap_start - v_start
                    s_dur = overlap_end - overlap_start
                    
                    # Avoid escaping issues with absolute paths in concat file
                    safe_vpath = v['path'].replace("'", "'\\''")
                    f_list.write(f"file '{safe_vpath}'\n")
                    f_list.write(f"inpoint {s_start:.3f}\n")
                    f_list.write(f"outpoint {(s_start + s_dur):.3f}\n")
                    
                    slice_df = dive[(dive['Time'] >= overlap_start) & (dive['Time'] <= overlap_end)]
                    for idx_s in range(len(slice_df)):
                        row = slice_df.iloc[idx_s]
                        rel_t = row['Time'] - overlap_start
                        rel_t = max(0, rel_t)

                        if idx_s + 1 < len(slice_df):
                            next_rel_t = slice_df.iloc[idx_s+1]['Time'] - overlap_start
                            end_t = min(next_rel_t, s_dur)
                        else:
                            end_t = min(rel_t + 1.0, s_dur)

                        f_srt.write(f"{srt_idx}\n")
                        f_srt.write(f"{format_srt_time(current_virtual_time + rel_t)} --> {format_srt_time(current_virtual_time + end_t)}\n")
                        # Add the text
                        f_srt.write(f"Depth: {row['Depth']}m | Temp: {row['Temperature']}C\n\n")
                        srt_idx += 1
                        
                    current_virtual_time += s_dur

    if not has_clips:
        return False

    escaped_srt = os.path.relpath(srt_path).replace('\\', '/')
    cc_filter = get_color_correction_filter(water_type=water_type)
    
    # Properly format the subtitles string
    # Replace literal colons in escaped_srt path with \\: for ffmpeg
    escaped_srt = srt_path.replace("\\", "\\\\").replace(":", "\\:")
    # Place in Top Right (Alignment=9) with 1px outline style
    vf_arg = f"{cc_filter}subtitles=f='{escaped_srt}':force_style='FontSize=5,Alignment=9,BorderStyle=1,Outline=1,Shadow=1,MarginV=20,MarginR=20,FontName=Arial'"

    cmd = [
        ffmpeg_bin, '-y',
        '-f', 'concat', '-safe', '0', '-i', list_path,
        '-map', '0:v:0', '-map', '0:a:0?',  # Strictly copy ONLY the first video and first audio track (strips telemetry hidden in secondary audio/data tracks)
        '-vf', vf_arg,
        '-colorspace', 'bt709', '-color_primaries', 'bt709', '-color_trc', 'bt709', '-color_range', 'pc',
        '-c:v', hw_encoder, '-b:v', '80M', '-r', '60',
        '-c:a', 'aac', '-b:a', '320k',
        '-movflags', '+faststart',
        os.path.abspath(output_file)
    ]
    
    res = run_cmd(cmd, total_duration=current_virtual_time)
    return res.returncode == 0 and os.path.exists(output_file)

def main(args=None):
    parser = argparse.ArgumentParser()
    parser.add_argument("--date", required=False, default=None)
    parser.add_argument("--logs_dir", required=False, default=os.environ.get("LOGS_DIR"))
    parser.add_argument("--media_dir", required=False, default=os.environ.get("SEARCH_DIR"))
    parser.add_argument("--output", required=False)
    parser.add_argument("--mode", choices=['highlights', 'full'], default='full')
    parser.add_argument("--offset", type=int, default=None, help="Force manual offset in seconds.")
    parser.add_argument("--dive_list", type=str, default="", help="Comma-separated list of dive IDs.")
    parser.add_argument("--gap", type=int, default=900, help="Seconds of gap to split session.")
    parser.add_argument("--water", choices=['saltwater', 'freshwater', 'none'], default='none', help="Water type.")
    parser.add_argument("--info", action="store_true", help="Print detected dives and exit without rendering.")

    parsed = parser.parse_args(args)
    
    if not parsed.logs_dir or not parsed.media_dir:
        print("Error: --logs_dir and --media_dir are required if LOGS_DIR and SEARCH_DIR are not set in .env")
        return 1

    videos = discover_videos(parsed.media_dir)
    _info(f"Indexed High-Res Videos (all): {len(videos)}")
    
    if not videos:
        print("Error: No high-res videos found in the media directory.")
        return 1

    # Extract unique dates from video timestamps
    target_dates = [parsed.date] if parsed.date else list(set([
        datetime.datetime.fromtimestamp(v['ts'], timezone.utc).strftime('%Y-%m-%d')
        for v in videos
    ]))

    display_date = parsed.date if parsed.date else f"Auto-discovered ({len(target_dates)} days)"
    safe_date_name = parsed.date if parsed.date else "multiday"
        
    if not parsed.output:
        base = os.path.join(os.path.expanduser("~"), "Movies", f"dive_{safe_date_name}")
        if parsed.dive_list:
            base += f"_dive{parsed.dive_list.replace(',', '_')}"
        if parsed.mode == 'highlights':
            base += "_highlights"
        parsed.output = base + ".mp4"

    temp_dir_name = f"temp_slices_{parsed.mode}_{safe_date_name}_{os.getpid()}"
    temp_dir_display = os.path.abspath(temp_dir_name)
    _info("\n========================================")
    _info("🎬 PARALENZ HEADLESS RENDERER")
    _info("========================================")
    _info(f"📅 Date:       {display_date}")
    _info(f"🌊 Dives:      {parsed.dive_list if parsed.dive_list else 'All detected'}")
    _info(f"🎯 Mode:       {parsed.mode.upper()}")
    _info(f"💧 Water:      {parsed.water.upper()}")
    _info(f"📁 Output:     {parsed.output}")
    _info(f"🛠️  TMP Dir:    {temp_dir_display}")
    _info("========================================\n")

    target_dives = parse_dive_list(parsed.dive_list)

    df = load_and_filter_logs(parsed.logs_dir, target_dates)
    if df.empty:
        print(f"Error: No valid logs matching dates {target_dates} found.")
        return 1

    dives = detect_dives(df, parsed.gap)
    _info(f"Detected Dives: {len(dives)}")
    if not dives:
        print("Error: No valid dives detected in telemetry.")
        return 1

    calc_offset = parsed.offset if parsed.offset is not None else 0
    if parsed.offset is not None:
        _info(f"Using manual offset: {calc_offset}s")
    else:
        _info("Using default zero-offset (Camera RTC Sync).")

    day_start = dives[0]['Time'].min() - 43200
    day_end = dives[-1]['Time'].max() + 43200
    videos = [v for v in videos if (v['ts'] + calc_offset) >= day_start and (v['ts'] + calc_offset) <= day_end]
    _info(f"Filtered to target date: {len(videos)} video(s)")

    if not videos:
        print("Error: No high-res videos found for the target date.")
        return 1

    if parsed.info:
        _info("\n[INFO MODE] Discovered Dives:")
        _info("-" * 65)
        info_counters = {}
        for d_idx, dive in enumerate(dives):
            d_start, d_end = dive['Time'].min(), dive['Time'].max()
            d_date = datetime.datetime.fromtimestamp(d_start, timezone.utc).strftime('%Y-%m-%d')
            d_st = datetime.datetime.fromtimestamp(d_start, timezone.utc).strftime('%H:%M:%S')
            d_et = datetime.datetime.fromtimestamp(d_end, timezone.utc).strftime('%H:%M:%S')
            info_counters[d_date] = info_counters.get(d_date, 0) + 1
            _info(f"Global #{d_idx + 1:02d} | Date: {d_date} | Day Dive #{info_counters[d_date]} | Time: {d_st} - {d_et} UTC")
        _info("-" * 65)
        _info("Exiting without rendering.")
        return 0

    temp_dir = temp_dir_display
    os.makedirs(temp_dir, exist_ok=True)

    try:
        ffmpeg_bin = get_ffmpeg_path()
        hw_encoder = get_best_hardware_encoder(ffmpeg_bin)
        _info(f"Using video encoder: {hw_encoder}")

        all_success = True
        has_processed = False
        dive_counters = {}

        for d_idx, dive in enumerate(dives):
            d_start, d_end = dive['Time'].min(), dive['Time'].max()
            dive_date = datetime.datetime.fromtimestamp(d_start, timezone.utc).strftime('%Y-%m-%d')
            
            if dive_date not in dive_counters:
                dive_counters[dive_date] = 1
            else:
                dive_counters[dive_date] += 1
                
            current_dive_id = dive_counters[dive_date]
            global_dive_id = d_idx + 1

            if target_dives and global_dive_id not in target_dives:
                continue

            _info(f"Processing Dive on {dive_date} (#{current_dive_id} for the day, #{global_dive_id} total): {d_start} to {d_end}")
            windows = calculate_highlight_windows(dive, d_start, d_end, parsed.mode)

            base_out, ext = os.path.splitext(parsed.output)
            
            # Remove "multiday" generic name from output if present, and inject date
            if "multiday" in base_out:
                base_out = base_out.replace("multiday", dive_date)
            elif len(target_dates) > 1 and dive_date not in base_out:
                # Inject date into custom output names during multi-day to prevent overwrites
                base_out = f"{base_out}_{dive_date}"
            
            # Append dive ID if not already there
            if f"dive{current_dive_id}" not in base_out:
                dive_output = f"{base_out}_dive{current_dive_id}{ext}"
            else:
                dive_output = f"{base_out}{ext}"

            success = process_dive(global_dive_id, dive, windows, videos, calc_offset, temp_dir, dive_output, parsed.water, ffmpeg_bin, hw_encoder)
            
            if success:
                has_processed = True
                _info(f"\nSUCCESS! Rendered Dive #{current_dive_id}: {os.path.abspath(dive_output)}")
            else:
                _info(f"\nCRITICAL ERROR: Final concatenation failed for Dive #{current_dive_id}.")
                all_success = False

        if not has_processed:
            print("Error: No correlated clips found.")
            return 1
            
        return 0 if all_success else 1
    finally:
        try:
            shutil.rmtree(temp_dir)
        except Exception:  # pragma: no cover
            pass

if __name__ == "__main__":
    sys.exit(main())
