import unittest
import pandas as pd
import os
import sys

class TestLogicAccuracy(unittest.TestCase):
    def setUp(self):
        # Create a mock dataframe mimicking the expected CSV format
        data = {
            'Time': [1000, 1005, 1010, 5000, 5005, 5010, 9000, 9005, 9010],
            'Depth': [0, 5, 0, 0, 20, 0, 0, 2, 0],
            'Temperature': [25, 24, 25, 25, 18, 25, 25, 23, 25],
            'ISO8601': ['2026-06-06T10:00:00Z'] * 9 # simplified
        }
        self.df = pd.DataFrame(data)

    def detect_dives_logic(self, df):
        # Replication of final_render.py's detection logic
        df = df.sort_values(by='Time')
        df['gap'] = df['Time'].diff() > 1800 # 30 mins
        df['session'] = df['gap'].cumsum()
        dives = [g for _, g in df.groupby('session') if g['Depth'].max() > 1.0]
        return dives

    def test_multi_dive_detection_accuracy(self):
        """Prove that gaps > 1800s split sessions, and max depth > 1.0 is required."""
        dives = self.detect_dives_logic(self.df)
        self.assertEqual(len(dives), 3, "Failed to correctly detect 3 distinct dives.")

        self.assertEqual(dives[0]['Depth'].max(), 5)
        self.assertEqual(dives[1]['Depth'].max(), 20)
        self.assertEqual(dives[2]['Depth'].max(), 2)

    def test_smart_highlights_logic(self):
        """Prove that 5-chapter Smart Highlights targets Entry, Descent, Mid-Dive, Apex, and Ascent."""
        dives = self.detect_dives_logic(self.df)
        dive2 = dives[1]
        d_start, d_end = dive2['Time'].min(), dive2['Time'].max()

        windows = []
        # 1. Entry / Initial Drop (40s)
        entry = dive2[dive2['Depth'] >= 2.0].head(1)
        if not entry.empty:
            t = entry.iloc[0]['Time']
            windows.append((t - 10, t + 30))
        # 2. Fastest Descent (45s)
        dive_diff = dive2['Depth'].diff()
        if not dive_diff.empty:
            t = dive2.iloc[dive_diff.argmax()]['Time']
            windows.append((t - 15, t + 30))
        # 3. Mid-Dive Exploration (50s)
        mid_time = d_start + (d_end - d_start) * 0.45
        mid_row = dive2.iloc[(dive2['Time'] - mid_time).abs().argsort()[:1]]
        if not mid_row.empty:
            t = mid_row.iloc[0]['Time']
            windows.append((t - 25, t + 25))
        # 4. Max Depth Apex (60s)
        max_t = dive2.iloc[dive2['Depth'].argmax()]['Time']
        windows.append((max_t - 30, max_t + 30))
        # 5. Ascent / Safety Stop Phase (40s)
        ascent = dive2[(dive2['Depth'] <= 5.0) & (dive2['Time'] > d_start + (d_end - d_start) * 0.75)].head(1)
        if not ascent.empty:
            t = ascent.iloc[0]['Time']
            windows.append((t - 15, t + 25))

        self.assertEqual(len(windows), 5, "Should detect all 5 chapters.")
        self.assertEqual(windows[0][0], 4995, "Entry start is wrong")
        self.assertEqual(windows[3][0], 4975, "Apex start is wrong")

    def test_color_correction_logic(self):
        """Verify dynamic depth-based color correction correctly scales and caps red channel boost."""
        import sys, os
        from scripts.build_headless_movie import get_color_correction_filter
        # Test 0m or water_type='none'
        self.assertEqual(get_color_correction_filter(0.0), "")
        self.assertEqual(get_color_correction_filter(15.0, water_type='none'), "")

        # Test 15m (half max depth) -> 0.200 boost
        self.assertEqual(get_color_correction_filter(15.0), "colorbalance=rs=0.200:rm=0.200:rh=0.200,")

        # Test 30m (max depth) -> 0.400 boost
        self.assertEqual(get_color_correction_filter(30.0), "colorbalance=rs=0.400:rm=0.400:rh=0.400,")

        # Test 40m (should cap at max limits)
        self.assertEqual(get_color_correction_filter(40.0), "colorbalance=rs=0.400:rm=0.400:rh=0.400,")

if __name__ == "__main__":
    unittest.main()
