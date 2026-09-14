import unittest
from unittest.mock import patch, MagicMock
import os
import sys

from scripts.check_videos import analyze_videos_in_window, get_meta

class TestCheckVideos(unittest.TestCase):

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
        self.assertEqual(meta['path'], "test.mp4")

    @patch('scripts.check_videos.glob.glob')
    @patch('scripts.check_videos.get_meta')
    def test_analyze_videos_in_window(self, mock_get_meta, mock_glob):
        mock_glob.return_value = ['vid1.MP4', 'vid2.MP4', 'lowres.MP4']

        def mock_meta_side_effect(f, **kwargs):
            if 'vid1' in f: return {'ts': 1000, 'dur': 10, 'path': 'vid1.MP4'}
            if 'vid2' in f: return {'ts': 3000, 'dur': 10, 'path': 'vid2.MP4'}
            return None

        mock_get_meta.side_effect = mock_meta_side_effect

        # Window covers vid1 but not vid2
        videos = analyze_videos_in_window("media_dir", 500, 2000)

        self.assertEqual(len(videos), 1)
        self.assertEqual(videos[0]['path'], 'vid1.MP4')

    @patch('scripts.check_videos.analyze_videos_in_window')
    def test_main_success(self, mock_analyze):
        mock_analyze.return_value = [{'ts': 1000, 'dur': 10, 'path': 'vid.mp4'}]
        from scripts.check_videos import main
        args = ['--media_dir', 'fake', '--start', '500', '--end', '2000']
        self.assertEqual(main(args), 0)

    @patch('scripts.check_videos.analyze_videos_in_window')
    def test_main_no_videos(self, mock_analyze):
        mock_analyze.return_value = []
        from scripts.check_videos import main
        args = ['--media_dir', 'fake', '--start', '500', '--end', '2000']
        self.assertEqual(main(args), 1)

if __name__ == "__main__":
    unittest.main()
