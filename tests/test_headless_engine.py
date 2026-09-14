import unittest
import os
import shutil
import tempfile
import subprocess
import sys
import pandas as pd
import json

@unittest.skipIf(not shutil.which("ffmpeg"), "FFmpeg is required for E2E tests")
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

        # 1. Create Mock Video (4K)
        self.vid_path = os.path.join(self.media_dir, "PARA0001.MP4")
        from scripts.utils import get_ffmpeg_path
        ffmpeg_cmd = get_ffmpeg_path()
        cmd = [
            ffmpeg_cmd, "-y", "-f", "lavfi", "-i", "color=c=blue:s=3840x2160:r=60",
            "-t", "2", "-metadata", f"creation_time={self.start_utc}",
            "-c:v", "libx264", "-pix_fmt", "yuv420p", self.vid_path
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

    def test_end_to_end_render(self):
        output_file = os.path.join(self.test_dir, "final_test.mp4")
        expected_output_file = os.path.join(self.test_dir, "final_test_dive1.mp4")
        cmd = [
            "uv", "run", "scripts/build_headless_movie.py",
            "--date", self.date,
            "--logs_dir", self.logs_dir,
            "--media_dir", self.media_dir,
            "--output", output_file,
            "--mode", "highlights",
            "--offset", "0"
        ]
        res = subprocess.run(cmd, capture_output=True, text=True)
        self.assertTrue(os.path.exists(expected_output_file), f"FFmpeg failed to produce output video.\nStdout: {res.stdout}\nStderr: {res.stderr}")
    def test_zero_offset_render(self):
        """Verify the zero-offset path works when --offset is omitted."""
        output_file = os.path.join(self.test_dir, "final_zero_offset.mp4")
        expected_output_file = os.path.join(self.test_dir, "final_zero_offset_dive1.mp4")
        cmd = [
            "uv", "run", "scripts/build_headless_movie.py",
            "--date", self.date,
            "--logs_dir", self.logs_dir,
            "--media_dir", self.media_dir,
            "--output", output_file,
            "--mode", "highlights"
            # NOTE: No --offset flag — exercises auto-calculation
        ]
        res = subprocess.run(cmd, capture_output=True, text=True)
        self.assertNotIn("TypeError", res.stderr, f"Zero-offset crashed:\nStdout: {res.stdout}\nStderr: {res.stderr}")
        self.assertIn("Using default zero-offset (Camera RTC Sync)", res.stdout, f"Zero-offset message missing:\nStdout: {res.stdout}")
        self.assertTrue(os.path.exists(expected_output_file), f"FFmpeg failed to produce output video.\nStdout: {res.stdout}\nStderr: {res.stderr}")

if __name__ == "__main__":
    unittest.main()
