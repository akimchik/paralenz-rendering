import unittest
from unittest.mock import patch, MagicMock
import pandas as pd
import os
import sys

from scripts.calc_offset import calculate_time_drift, get_meta

class TestCalcOffset(unittest.TestCase):

    @patch('scripts.utils.subprocess.run')
    def test_get_meta_success(self, mock_run):
        mock_res = MagicMock()
        mock_res.returncode = 0
        mock_res.stdout = '{"format": {"duration": "10.5", "tags": {"creation_time": "2026-06-06T10:00:00.000000Z"}}}'
        mock_run.return_value = mock_res

        with patch('scripts.utils.get_ffprobe_path', return_value="ffprobe"):
            meta = get_meta("test.mp4")
        self.assertIsNotNone(meta)
        self.assertEqual(meta['dur'], 10.5)
        self.assertEqual(meta['ts'], 1780740000.0) # 2026-06-06 10:00:00 UTC

    @patch('scripts.calc_offset.glob.glob')
    @patch('scripts.calc_offset.pd.read_csv')
    @patch('scripts.calc_offset.get_meta')
    def test_calculate_time_drift(self, mock_get_meta, mock_read_csv, mock_glob):
        # 1st call to glob is for CSVs, 2nd call is for MP4s
        mock_glob.side_effect = [['log1.csv'], ['vid1.MP4']]

        # Mock CSV data
        mock_read_csv.return_value = pd.DataFrame({
            'ISO8601': ['2026-06-06T10:00:00Z', '2026-06-06T10:00:10Z'],
            'Time': [1000, 1010],
            'Depth': [2.0, 5.0]
        })

        # Mock video metadata
        mock_get_meta.return_value = {'ts': 900, 'dur': 100, 'path': 'vid1.MP4'}

        res, err = calculate_time_drift("logs_dir", "media_dir", "2026-06-06")

        self.assertIsNone(err)
        self.assertIsNotNone(res)
        self.assertEqual(res['dive_start'], 1000)
        self.assertEqual(res['vid_start'], 900)
        self.assertEqual(res['diff'], 100) # 1000 - 900 = 100s offset

    @patch('scripts.calc_offset.glob.glob')
    def test_calculate_time_drift_no_logs(self, mock_glob):
        mock_glob.return_value = []
        res, err = calculate_time_drift("logs_dir", "media_dir", "2026-06-06")
        self.assertIsNone(res)
        self.assertEqual(err, "No logs found in directory")

    @patch('scripts.calc_offset.calculate_time_drift')
    def test_main_success(self, mock_calc):
        mock_calc.return_value = ({
            'dive_start': 1000,
            'vid_start': 900,
            'first_video': 'test.mp4',
            'diff': 100
        }, None)

        from scripts.calc_offset import main
        args = ['--logs_dir', 'fake', '--media_dir', 'fake', '--date', '2026']
        self.assertEqual(main(args), 0)

    @patch('scripts.calc_offset.calculate_time_drift')
    def test_main_error(self, mock_calc):
        mock_calc.return_value = (None, "Some error")
        from scripts.calc_offset import main
        args = ['--logs_dir', 'fake', '--media_dir', 'fake', '--date', '2026']
        self.assertEqual(main(args), 1)


    @patch('scripts.utils.subprocess.run')
    def test_get_meta_exception(self, mock_run):
        mock_run.side_effect = Exception("FFprobe crashed")
        meta = get_meta('some_file.mp4')
        self.assertIsNone(meta)


    @patch('scripts.utils.subprocess.run')
    def test_get_meta_exception(self, mock_run):
        mock_run.side_effect = Exception("FFprobe crashed")
        meta = get_meta('some_file.mp4')
        self.assertIsNone(meta)

if __name__ == "__main__":
    unittest.main()
