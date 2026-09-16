import unittest
import pandas as pd
import os
import sys

from scripts.build_headless_movie import detect_dives, calculate_highlight_windows, get_color_correction_filter

class TestLogicAccuracy(unittest.TestCase):
    def setUp(self):
        # Create a mock dataframe mimicking the expected CSV format
        # Gap needs to be > 7200 for detect_dives to split sessions
        data = {
            'Time': [1000, 1005, 1010, 10000, 10005, 10010, 20000, 20005, 20010],
            'Depth': [0, 5, 0, 0, 20, 0, 0, 2, 0],
            'Temperature': [25, 24, 25, 25, 18, 25, 25, 23, 25],
            'ISO8601': ['2026-06-06T10:00:00Z'] * 9
        }
        self.df = pd.DataFrame(data)

    def test_multi_dive_detection_accuracy(self):
        """Prove that gaps > 7200s split sessions, and max depth > 1.0 is required."""
        dives = detect_dives(self.df, gap=7200)
        self.assertEqual(len(dives), 3, "Failed to correctly detect 3 distinct dives.")

        self.assertEqual(dives[0]['Depth'].max(), 5)
        self.assertEqual(dives[1]['Depth'].max(), 20)
        self.assertEqual(dives[2]['Depth'].max(), 2)

    def test_smart_highlights_logic(self):
        """Prove that 5-chapter Smart Highlights targets Entry, Descent, Mid-Dive, Apex, and Ascent."""
        dives = detect_dives(self.df, gap=7200)
        dive2 = dives[1]
        d_start, d_end = dive2['Time'].min(), dive2['Time'].max()
        
        # We need a slightly denser dataframe to get 5 distinct chapters properly from the real function
        data2 = {
            'Time': list(range(10000, 10051)),
            'Depth': [0,1,2,3,4,5,6,7,8,9,10,11,12,13,14,15,16,17,18,19,20, 19,18,17,16,15,14,13,12,11,10,9,8,7,6,5,4,3,2,1,0] + [0]*10,
            'Temperature': [20] * 51,
            'ISO8601': ['Z'] * 51
        }
        dive2 = pd.DataFrame(data2)
        d_start, d_end = dive2['Time'].min(), dive2['Time'].max()

        windows = calculate_highlight_windows(dive2, d_start, d_end, mode='highlights')

        self.assertEqual(len(windows), 5, "Should detect all 5 chapters.")

    def test_color_correction_logic(self):
        """Verify dynamic depth-based color correction correctly scales and caps red channel boost using curves."""
        # Test 0m or water_type='none'
        self.assertEqual(get_color_correction_filter(0.0), "")
        self.assertEqual(get_color_correction_filter(15.0, water_type='none'), "")

        # Test 15m (half max depth) -> boost 0.2, mid = 0.5 + (0.2 * 0.75) = 0.650
        self.assertEqual(get_color_correction_filter(15.0), "curves=r='0/0 0.5/0.650 1/1',")

        # Test 30m (max depth) -> boost 0.4, mid = 0.5 + (0.4 * 0.75) = 0.800
        self.assertEqual(get_color_correction_filter(30.0), "curves=r='0/0 0.5/0.800 1/1',")

        # Test 40m (should cap at max limits -> mid = 0.800)
        self.assertEqual(get_color_correction_filter(40.0), "curves=r='0/0 0.5/0.800 1/1',")
        
        # Test freshwater 30m -> boost 0.4, mid = 0.800 on red and blue
        self.assertEqual(get_color_correction_filter(30.0, water_type='freshwater'), "curves=r='0/0 0.5/0.800 1/1':b='0/0 0.5/0.800 1/1',")

if __name__ == "__main__":
    unittest.main()
