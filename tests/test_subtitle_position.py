import pytest
from scripts.build_headless_movie import build_ffmpeg_cmd, get_color_correction_filter

def test_subtitle_alignment_is_top_right():
    # We want to make sure Alignment=7 is in the script
    with open('scripts/build_headless_movie.py', 'r') as f:
        content = f.read()
    
    assert "Alignment=7" in content, "The subtitle Alignment must be 7 (Top Right in SSA format)"
    assert "MarginV=" in content
    assert "MarginR=" in content
