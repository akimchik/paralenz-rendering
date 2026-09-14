import unittest
from scripts.build_headless_movie import format_srt_time

class TestSRTGeneration(unittest.TestCase):
    def test_format_srt_time_basic(self):
        """Test basic conversions."""
        self.assertEqual(format_srt_time(0), "00:00:00,000")
        self.assertEqual(format_srt_time(1.5), "00:00:01,500")
        self.assertEqual(format_srt_time(61), "00:01:01,000")
        self.assertEqual(format_srt_time(3600), "01:00:00,000")

    def test_format_srt_time_carryover(self):
        """Test the 1000ms carry-over rounding logic."""
        # 3600.999 => ms=999
        self.assertEqual(format_srt_time(3600.999), "01:00:00,999")
        
        # 0.9995 => ms rounds to 1000 => carry over to 1 sec
        self.assertEqual(format_srt_time(0.9996), "00:00:01,000")
        
        # 59.9996 => carry over to 60 sec => carry over to 1 min
        self.assertEqual(format_srt_time(59.9996), "00:01:00,000")
        
        # 3599.9996 => carry over to 1 hour
        self.assertEqual(format_srt_time(3599.9996), "01:00:00,000")

if __name__ == "__main__":
    unittest.main()
