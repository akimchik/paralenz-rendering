import unittest
from unittest.mock import patch, MagicMock
import pandas as pd
import os
import sys

# Ensure scripts can be imported

from scripts.build_headless_movie import (
    parse_dive_list,
    detect_dives,
    calculate_highlight_windows,
    format_srt_time,
    load_and_filter_logs,
    discover_videos,
    get_color_correction_filter,
    process_dive,
    main
)

class TestBuildHeadlessMovie(unittest.TestCase):

    def test_parse_dive_list(self):
        self.assertEqual(parse_dive_list(""), [])
        self.assertEqual(parse_dive_list("1"), [1])
        self.assertEqual(parse_dive_list("1, 3, 5"), [1, 3, 5])

    def test_format_srt_time(self):
        self.assertEqual(format_srt_time(0.0), "00:00:00,000")
        self.assertEqual(format_srt_time(3600 + 60 + 5.123), "01:01:05,123")
        self.assertEqual(format_srt_time(3600.999), "01:00:00,999") # Fixed rounding logic

    def test_detect_dives_empty(self):
        self.assertEqual(detect_dives(pd.DataFrame(), 7200), [])

    def test_detect_dives_logic(self):
        df = pd.DataFrame({
            'Time': [100, 105, 110, 8000, 8005, 8010],
            'Depth': [0.5, 2.0, 0.5, 0.0, 0.0, 0.0]
        })
        dives = detect_dives(df, 7200)
        self.assertEqual(len(dives), 1)
        self.assertEqual(len(dives[0]), 3)

    def test_calculate_highlight_windows_full_mode(self):
        df = pd.DataFrame({'Time': [100, 150], 'Depth': [2.0, 5.0]})
        windows = calculate_highlight_windows(df, 100, 150, 'full')
        self.assertEqual(len(windows), 1)
        self.assertEqual(windows[0], (100 - 60, 150 + 60))

    def test_calculate_highlight_windows_highlights_mode(self):
        df = pd.DataFrame({
            'Time': [1000, 1010, 1050, 1100, 1150, 1200],
            'Depth': [1.0, 2.5, 10.0, 25.0, 15.0, 4.0]
        })
        windows = calculate_highlight_windows(df, 1000, 1200, 'highlights')
        self.assertTrue(len(windows) > 0)
        sorted_starts = [w[0] for w in windows]
        self.assertEqual(sorted_starts, sorted(sorted_starts))

    @patch('scripts.build_headless_movie.glob.glob')
    @patch('scripts.build_headless_movie.pd.read_csv')
    def test_load_and_filter_logs(self, mock_read_csv, mock_glob):
        mock_glob.return_value = ['dummy.csv']
        mock_read_csv.return_value = pd.DataFrame({
            'ISO8601': ['2026-06-06T10:00:00Z', '2026-06-07T10:00:00Z'],
            'Time': [1000, 2000]
        })
        
        # Test with date list
        df = load_and_filter_logs('/fake', ['2026-06-06'])
        self.assertEqual(len(df), 1)
        self.assertEqual(df.iloc[0]['Time'], 1000)

        # Test without date list (auto-discover all)
        df_all = load_and_filter_logs('/fake', [])
        self.assertEqual(len(df_all), 2)
        self.assertEqual(df_all.iloc[0]['Time'], 1000)
        self.assertEqual(df_all.iloc[1]['Time'], 2000)

    @patch('subprocess.run')
    def test_get_best_hardware_encoder_nvenc(self, mock_run):
        from scripts.build_headless_movie import get_best_hardware_encoder
        def side_effect(cmd, **kwargs):
            return MagicMock(returncode=0 if 'h264_nvenc' in cmd else 1)
        mock_run.side_effect = side_effect
        self.assertEqual(get_best_hardware_encoder('ffmpeg'), 'h264_nvenc')
        
    @patch('subprocess.run')
    def test_get_best_hardware_encoder_mac(self, mock_run):
        from scripts.build_headless_movie import get_best_hardware_encoder
        def side_effect(cmd, **kwargs):
            return MagicMock(returncode=0 if 'h264_videotoolbox' in cmd else 1)
        mock_run.side_effect = side_effect
        self.assertEqual(get_best_hardware_encoder('ffmpeg'), 'h264_videotoolbox')

    @patch('subprocess.run')
    def test_get_best_hardware_encoder_fallback(self, mock_run):
        from scripts.build_headless_movie import get_best_hardware_encoder
        mock_run.return_value = MagicMock(returncode=1)
        self.assertEqual(get_best_hardware_encoder('ffmpeg'), 'libx264')

    def test_get_color_correction_filter(self):
        self.assertEqual(get_color_correction_filter('none'), "")
        self.assertIn("0.58", get_color_correction_filter('saltwater'))
        self.assertIn("0.55", get_color_correction_filter('freshwater'))

    @patch('scripts.build_headless_movie.glob.glob')
    @patch('scripts.build_headless_movie.get_meta')
    def test_discover_videos(self, mock_get_meta, mock_glob):
        mock_glob.return_value = ['v1.mp4', 'v2.mp4']
        mock_get_meta.side_effect = [{'ts': 2000}, {'ts': 1000}]
        vids = discover_videos('fake_dir')
        self.assertEqual(len(vids), 2)
        self.assertEqual(vids[0]['ts'], 1000)

    @patch('scripts.build_headless_movie.run_cmd')
    @patch('os.path.exists')
    @patch('builtins.open', new_callable=unittest.mock.mock_open)
    def test_process_dive(self, mock_open, mock_exists, mock_run_cmd):
        mock_exists.return_value = True
        mock_run_cmd.return_value.returncode = 0 

        dive = pd.DataFrame({'Time': [1000, 1010], 'Depth': [2.0, 5.0], 'Temperature': [20, 20]})
        windows = [(1000, 1010)]
        videos = [{'ts': 900, 'dur': 1000, 'path': 'vid.mp4'}]

        success = process_dive(1, dive, windows, videos, 0, "temp", "out.mp4", "saltwater", "ffmpeg", "h264_videotoolbox")
        self.assertTrue(success)
        
        calls = mock_run_cmd.call_args_list
        self.assertTrue(len(calls) > 0, "FFmpeg should be called")
        ffmpeg_cmd = calls[0][0][0]
        
        self.assertIn("-vf", ffmpeg_cmd)
        vf_index = ffmpeg_cmd.index("-vf")
        vf_string = ffmpeg_cmd[vf_index + 1]
        
        self.assertIn("curves=r=", vf_string)
        self.assertIn("subtitles=", vf_string)
        self.assertIn("temp/sub_1.srt", vf_string.replace('\\', '/'))

    @patch('scripts.build_headless_movie.load_and_filter_logs')
    @patch('scripts.build_headless_movie.detect_dives')
    @patch('scripts.build_headless_movie.discover_videos')
    @patch('scripts.build_headless_movie.process_dive')
    @patch('os.makedirs')
    @patch('shutil.rmtree')
    def test_main_success(self, mock_rmtree, mock_makedirs, mock_process, mock_discover, mock_detect, mock_load):
        mock_load.return_value = pd.DataFrame({'Time': [1]})
        mock_detect.return_value = [pd.DataFrame({'Time': [1000, 1010]})]
        mock_discover.return_value = [{'ts': 900, 'dur': 200, 'path': 'v.mp4'}]
        mock_process.return_value = True

        args = ['--date', '2026', '--logs_dir', 'l', '--media_dir', 'm', '--output', 'o']
        self.assertEqual(main(args), 0)

    @patch('scripts.build_headless_movie.load_and_filter_logs')
    def test_main_no_logs(self, mock_load):
        mock_load.return_value = pd.DataFrame()
        args = ['--date', '2026', '--logs_dir', 'l', '--media_dir', 'm', '--output', 'o']
        self.assertEqual(main(args), 1)

    @patch('scripts.build_headless_movie.load_and_filter_logs')
    def test_argparse_water_types(self, mock_load):
        from scripts.build_headless_movie import main
        mock_load.return_value = pd.DataFrame()
        try:
            main(['--date', '2026', '--logs_dir', 'l', '--media_dir', 'm', '--output', 'o', '--water', 'freshwater'])
        except SystemExit as e:
            self.fail(f"argparse rejected 'freshwater', exited with {e}")

    @patch('scripts.build_headless_movie.load_and_filter_logs')
    def test_info_mode(self, mock_load):
        from scripts.build_headless_movie import main
        import pandas as pd
        df = pd.DataFrame({
            'ISO8601': ['2026-06-27T10:00:00Z', '2026-06-27T10:01:00Z'],
            'Time': [1.0, 61.0],
            'Depth': [2.0, 3.0],
            'Temperature': [20, 20]
        })
        mock_load.return_value = df
        
        with patch('scripts.build_headless_movie.discover_videos') as mock_discover:
            mock_discover.return_value = [{'ts': 0, 'dur': 100, 'width': 3840, 'path': 'fake.MP4'}]
            import io
            from contextlib import redirect_stdout
            f_out = io.StringIO()
            with redirect_stdout(f_out):
                ret = main(['--date', '1970-01-01', '--logs_dir', 'l', '--media_dir', 'm', '--info'])
            stdout = f_out.getvalue()
            
            self.assertEqual(ret, 0)
            self.assertIn("Global #01 | Date: 1970-01-01 | Day Dive #1 | Time: 00:00:01 - 00:01:01 UTC", stdout)

    @patch('scripts.build_headless_movie.discover_videos')
    @patch('scripts.build_headless_movie.load_and_filter_logs')
    def test_main_exception_handling(self, mock_load, mock_discover):
        from scripts.build_headless_movie import main
        mock_discover.return_value = [{'ts': 1000, 'dur': 100, 'path': 'fake'}]
        mock_load.side_effect = Exception("Simulated fatal error")
        with self.assertRaises(Exception):
            main(['--date', '2026-06-27', '--logs_dir', 'l', '--media_dir', 'm'])

    @patch('scripts.build_headless_movie.subprocess.Popen')
    def test_run_cmd_progress(self, mock_popen):
        import io
        import sys
        from scripts.build_headless_movie import run_cmd
        
        mock_process = MagicMock()
        mock_process.stdout = [
            "frame=  100 fps= 30 q=28.0 size= 2048kB time=00:01:30.00 bitrate=3000.0kbits/s speed=1.5x\n",
            "frame=  200 fps= 30 q=28.0 size= 4096kB time=00:03:00.00 bitrate=3000.0kbits/s speed=1.5x\n"
        ]
        mock_process.returncode = 0
        mock_popen.return_value = mock_process
        
        captured_output = io.StringIO()
        original_stdout = sys.stdout
        sys.stdout = captured_output
        try:
            res = run_cmd(["fake_cmd"], total_duration=360.0)
        finally:
            sys.stdout = original_stdout
            
        output = captured_output.getvalue()
        self.assertIn("00:01:30 / 00:06:00.000 (25.0%)", output)
        self.assertIn("00:03:00 / 00:06:00.000 (50.0%)", output)
        self.assertEqual(res.returncode, 0)
        
    @patch('scripts.build_headless_movie.subprocess.Popen')
    def test_run_cmd_no_total_duration(self, mock_popen):
        import io
        import sys
        from scripts.build_headless_movie import run_cmd
        
        mock_process = MagicMock()
        mock_process.stdout = [
            "time=00:01:30.00\n"
        ]
        mock_process.returncode = 0
        mock_popen.return_value = mock_process
        
        captured_output = io.StringIO()
        original_stdout = sys.stdout
        sys.stdout = captured_output
        try:
            res = run_cmd(["fake_cmd"])
        finally:
            sys.stdout = original_stdout
            
        output = captured_output.getvalue()
        self.assertIn("00:01:30", output)
        self.assertNotIn("%", output)
        self.assertEqual(res.returncode, 0)

if __name__ == "__main__":
    unittest.main()
