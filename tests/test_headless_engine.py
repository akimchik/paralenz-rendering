import unittest
import os
import shutil
import tempfile
import subprocess
import sys
import pandas as pd
import json
import io
from contextlib import redirect_stdout, redirect_stderr

from scripts.build_headless_movie import main

def check_ffmpeg_has_subtitles():
    try:
        from scripts.utils import get_ffmpeg_path
        res = subprocess.run([get_ffmpeg_path(), "-filters"], capture_output=True, text=True)
        return "subtitles" in res.stdout
    except Exception:
        return False

def inspect_video(path):
    """Use ffprobe to extract video metadata and return a structured report."""
    if not os.path.exists(path):
        return None

    from scripts.utils import get_ffprobe_path
    cmd = [
        get_ffprobe_path(), "-v", "quiet",
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


@unittest.skipIf(not shutil.which("ffmpeg"), "FFmpeg is required for E2E tests")
@unittest.skipIf(not check_ffmpeg_has_subtitles(), "FFmpeg binary lacks 'subtitles' (libass) filter")
class TestHeadlessEngine(unittest.TestCase):
    def setUp(self):
        self.test_dir = tempfile.mkdtemp()
        self.logs_dir = os.path.join(self.test_dir, "LOGS")
        self.media_dir = os.path.join(self.test_dir, "DCIM")
        os.makedirs(self.logs_dir)
        os.makedirs(self.media_dir)

        self.date = "2026-06-06"
        self.epoch = 1780740000
        self.start_utc = "2026-06-06T10:00:00Z"

        # 1. Create Mock Video (4K with Audio)
        self.vid_path = os.path.join(self.media_dir, "PARA0001.MP4")
        from scripts.utils import get_ffmpeg_path
        ffmpeg_cmd = get_ffmpeg_path()
        cmd = [
            ffmpeg_cmd, "-y", 
            "-f", "lavfi", "-i", "color=c=blue:s=3840x2160:r=60",
            "-f", "lavfi", "-i", "anullsrc=r=48000:cl=stereo",
            "-t", "2", "-metadata", f"creation_time={self.start_utc}",
            "-c:v", "libx264", "-pix_fmt", "yuv420p", 
            "-c:a", "aac",
            self.vid_path
        ]
        res = subprocess.run(cmd, capture_output=True)
        if res.returncode != 0:
            self.skipTest(f"FFmpeg is broken or cannot create video: {res.stderr.decode()}")

        # 2. Create Mock Telemetry
        self.csv_path = os.path.join(self.logs_dir, "LOG01.csv")
        data = {
            'Time': [self.epoch, self.epoch + 1, self.epoch + 2],
            'Temperature': [20.3, 20.1, 19.8],
            'Depth': [2.0, 15.5, 30.2],
            'ISO8601': [self.date + "T10:00:00Z", self.date + "T10:00:01Z", self.date + "T10:00:02Z"]
        }
        pd.DataFrame(data).to_csv(self.csv_path, index=False)

    def tearDown(self):
        shutil.rmtree(self.test_dir)

    def test_end_to_end_render_and_validate(self):
        output_file = os.path.join(self.test_dir, "final_test.mp4")
        expected_output_file = os.path.join(self.test_dir, "final_test_dive1.mp4")
        args = [
            "--date", self.date,
            "--logs_dir", self.logs_dir,
            "--media_dir", self.media_dir,
            "--output", output_file,
            "--mode", "highlights",
            "--offset", "0"
        ]
        f_out = io.StringIO()
        f_err = io.StringIO()
        with redirect_stdout(f_out), redirect_stderr(f_err):
            ret = main(args)
            
        stdout = f_out.getvalue()
        stderr = f_err.getvalue()
        self.assertEqual(ret, 0, f"main() failed:\nStdout: {stdout}\nStderr: {stderr}")
        self.assertTrue(os.path.exists(expected_output_file), f"FFmpeg failed to produce output video.\nStdout: {stdout}\nStderr: {stderr}")

        # Validate the output with inspect_video (port from validate_output.py)
        info = inspect_video(expected_output_file)
        self.assertIsNotNone(info, "ffprobe could not read the output video")
        self.assertEqual(info["width"], 3840)
        self.assertEqual(info["height"], 2160)
        self.assertGreaterEqual(info["fps"], 59.0)
        self.assertEqual(info["codec"], "h264")
        self.assertTrue(info["has_audio"], "Output video must have an audio stream")

    def test_zero_offset_render(self):
        """Verify the zero-offset path works when --offset is omitted."""
        output_file = os.path.join(self.test_dir, "final_zero_offset.mp4")
        expected_output_file = os.path.join(self.test_dir, "final_zero_offset_dive1.mp4")
        args = [
            "--date", self.date,
            "--logs_dir", self.logs_dir,
            "--media_dir", self.media_dir,
            "--output", output_file,
            "--mode", "highlights"
            # NOTE: No --offset flag — exercises auto-calculation
        ]
        f_out = io.StringIO()
        f_err = io.StringIO()
        with redirect_stdout(f_out), redirect_stderr(f_err):
            ret = main(args)
            
        stdout = f_out.getvalue()
        stderr = f_err.getvalue()
        
        self.assertNotIn("TypeError", stderr, f"Zero-offset crashed:\nStdout: {stdout}\nStderr: {stderr}")
        self.assertIn("Using default zero-offset (Camera RTC Sync)", stdout, f"Zero-offset message missing:\nStdout: {stdout}")
        self.assertEqual(ret, 0, f"main() failed:\nStdout: {stdout}\nStderr: {stderr}")
        self.assertTrue(os.path.exists(expected_output_file), f"FFmpeg failed to produce output video.\nStdout: {stdout}\nStderr: {stderr}")

if __name__ == "__main__":
    unittest.main()
