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
    concatenate_slices,
    build_overlay_slices,
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
        self.assertEqual(format_srt_time(3600.999), "01:00:00,999")

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
        df = load_and_filter_logs('/fake', '2026-06-06')
        self.assertEqual(len(df), 1)
        self.assertEqual(df.iloc[0]['Time'], 1000)

    def test_get_color_correction_filter(self):
        self.assertEqual(get_color_correction_filter(0), "")
        self.assertEqual(get_color_correction_filter(15.0, water_type='none'), "")
        self.assertEqual(get_color_correction_filter(30.0), "colorbalance=rs=0.400:rm=0.400:rh=0.400,")

    @patch('scripts.build_headless_movie.glob.glob')
    @patch('scripts.build_headless_movie.get_meta')
    def test_discover_videos(self, mock_get_meta, mock_glob):
        mock_glob.return_value = ['vid1.mp4', 'vid2.mp4']
        # Return dicts out of chronological order to test sorting
        mock_get_meta.side_effect = [
            {'ts': 2000, 'dur': 10},
            {'ts': 1000, 'dur': 20}
        ]
        videos = discover_videos('/fake')
        self.assertEqual(len(videos), 2)
        self.assertEqual(videos[0]['ts'], 1000)
        self.assertEqual(videos[1]['ts'], 2000)

    @patch('scripts.build_headless_movie.get_ffmpeg_path', return_value='ffmpeg')
    @patch('scripts.build_headless_movie.run_cmd')
    def test_concatenate_slices(self, mock_run_cmd, mock_get_ffmpeg):
        

        # Test empty
        self.assertFalse(concatenate_slices([], "out.mp4", "temp"))

        # Test success
        mock_run_cmd.return_value.returncode = 0
        with patch('os.path.exists', return_value=True), patch('builtins.open', unittest.mock.mock_open()):
            self.assertTrue(concatenate_slices(["f1.mp4"], "out.mp4", "temp"))

        # Test fail
        mock_run_cmd.return_value.returncode = 1
        with patch('os.path.exists', return_value=False), patch('builtins.open', unittest.mock.mock_open()):
            self.assertFalse(concatenate_slices(["f1.mp4"], "out.mp4", "temp"))

    @patch('scripts.build_headless_movie.get_ffmpeg_path', return_value='ffmpeg')
    @patch('scripts.build_headless_movie.run_cmd')
    @patch('os.path.exists')
    @patch('builtins.open', new_callable=unittest.mock.mock_open)
    def test_build_overlay_slices(self, mock_open, mock_exists, mock_run_cmd, mock_get_ffmpeg):
        
        mock_exists.return_value = True
        mock_run_cmd.return_value.returncode = 0 # success on first try (videotoolbox)

        dives = [pd.DataFrame({'Time': [1000, 1010], 'Depth': [2.0, 5.0], 'Temperature': [20, 20]})]
        videos = [{'ts': 900, 'dur': 1000, 'path': 'vid.mp4'}]

        # Call it
        processed = build_overlay_slices(dives, videos, 0, "temp", "full", [], "saltwater")
        self.assertEqual(len(processed), 1)

    @patch('scripts.build_headless_movie.get_ffmpeg_path', return_value='ffmpeg')
    @patch('scripts.build_headless_movie.run_cmd')
    @patch('os.path.exists')
    @patch('builtins.open', new_callable=unittest.mock.mock_open)
    def test_build_overlay_slices_fallback(self, mock_open, mock_exists, mock_run_cmd, mock_get_ffmpeg):
        
        mock_exists.return_value = True

        # First call fails (videotoolbox), second succeeds (libx264)
        mock_run_cmd.side_effect = [MagicMock(returncode=1), MagicMock(returncode=0)]

        dives = [pd.DataFrame({'Time': [1000, 1010], 'Depth': [2.0, 5.0], 'Temperature': [20, 20]})]
        videos = [{'ts': 900, 'dur': 1000, 'path': 'vid.mp4'}]

        processed = build_overlay_slices(dives, videos, 0, "temp", "full", [], "saltwater")
        self.assertEqual(len(processed), 1)

    @patch('scripts.build_headless_movie.load_and_filter_logs')
    @patch('scripts.build_headless_movie.detect_dives')
    @patch('scripts.build_headless_movie.discover_videos')
    @patch('scripts.build_headless_movie.build_overlay_slices')
    @patch('scripts.build_headless_movie.concatenate_slices')
    @patch('os.makedirs')
    @patch('shutil.rmtree')
    def test_main_success(self, mock_rmtree, mock_makedirs, mock_concat, mock_build, mock_discover, mock_detect, mock_load):
        
        mock_load.return_value = pd.DataFrame({'Time': [1]})
        mock_detect.return_value = [pd.DataFrame({'Time': [1000, 1010]})]
        mock_discover.return_value = [{'ts': 900, 'dur': 200, 'path': 'v.mp4'}]
        mock_build.return_value = {1: ['slice.mp4']}
        mock_concat.return_value = True

        args = ['--date', '2026', '--logs_dir', 'l', '--media_dir', 'm', '--output', 'o']
        self.assertEqual(main(args), 0)

    @patch('scripts.build_headless_movie.load_and_filter_logs')
    def test_main_no_logs(self, mock_load):
        
        mock_load.return_value = pd.DataFrame()
        args = ['--date', '2026', '--logs_dir', 'l', '--media_dir', 'm', '--output', 'o']
        self.assertEqual(main(args), 1)

if __name__ == "__main__":
    unittest.main()
