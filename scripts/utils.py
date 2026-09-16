import os
import shutil
import json
import subprocess
from datetime import datetime, timezone

def get_ffmpeg_path() -> str:
    path = shutil.which("ffmpeg")
    if not path:
        raise FileNotFoundError("ffmpeg not found on PATH. Please install FFmpeg.")
    return path

def get_ffprobe_path() -> str:
    path = shutil.which("ffprobe")
    if not path:
        raise FileNotFoundError("ffprobe not found on PATH. Please install FFmpeg.")
    return path

def get_meta(file_path: str, min_width: int = 0, basename_only: bool = False):
    """
    Extract video metadata using ffprobe.

    Args:
        file_path: Absolute or relative path to the media file.
        min_width: If > 0, skips files where the video width is smaller than this.
        basename_only: If True, returns only the basename of the file in the 'path' key.

    Returns:
        dict containing 'ts' (timestamp), 'dur' (duration), 'width' (optional), and 'path',
        or None if parsing fails or min_width is not met.
    """
    try:
        cmd = [
            get_ffprobe_path(), '-v', 'quiet', '-select_streams', 'v:0',
            '-show_entries', 'format_tags=creation_time:format=duration:stream=width,height',
            '-of', 'json', file_path
        ]
        res = subprocess.run(cmd, capture_output=True, text=True, timeout=10)
        if res.returncode != 0:
            return None

        d = json.loads(res.stdout)

        fmt = d.get('format', {})
        tags = fmt.get('tags', {})
        dur = float(fmt.get('duration', 0))

        streams = d.get('streams', [])
        width = int(streams[0].get('width', 0)) if streams else 0

        ts = tags.get('creation_time')
        if ts:
            if min_width > 0 and width < min_width:
                return None
            dt = datetime.strptime(ts[:19], '%Y-%m-%dT%H:%M:%S').replace(tzinfo=timezone.utc)
            path_val = os.path.basename(file_path) if basename_only else file_path
            return {'ts': dt.timestamp(), 'dur': dur, 'width': width, 'path': path_val}
    except Exception as e:  # pragma: no cover
        print(f"Error parsing metadata for {file_path}: {e}")  # pragma: no cover
    return None
