import unittest
from unittest.mock import patch, mock_open
import sys

from scripts.check_versions import check_versions

class TestCheckVersions(unittest.TestCase):
    @patch('sys.exit', side_effect=SystemExit)
    @patch('builtins.open', new_callable=mock_open)
    @patch('os.environ.get')
    @patch('builtins.print')
    def test_check_versions_success(self, mock_print, mock_env, mock_file, mock_exit):
        mock_env.return_value = "feat/v3.2.1-something"
        
        def mock_file_content(filename, *args, **kwargs):
            if "README.md" in filename:
                return mock_open(read_data="# Headless Dive Automation (v3.2.1)")()
            elif "SKILL.md" in filename:
                return mock_open(read_data="Paralenz Rendering Standards (v3.2.1 Modular Architecture)")()
            elif "CHANGELOG.md" in filename:
                return mock_open(read_data="## [v3.2.1]")()
            return mock_open(read_data="")()
            
        mock_file.side_effect = mock_file_content
        
        try:
            check_versions()
        except SystemExit:
            self.fail("check_versions() raised SystemExit unexpectedly")
        mock_exit.assert_not_called()

    @patch('sys.exit', side_effect=SystemExit)
    @patch('builtins.open', new_callable=mock_open)
    @patch('builtins.print')
    def test_check_versions_readme_fail(self, mock_print, mock_file, mock_exit):
        mock_file.return_value = mock_open(read_data="# No version here")()
        with self.assertRaises(SystemExit):
            check_versions()
        mock_exit.assert_called_once_with(1)

    @patch('sys.exit', side_effect=SystemExit)
    @patch('builtins.open', new_callable=mock_open)
    @patch('os.environ.get')
    @patch('builtins.print')
    def test_check_versions_mismatch(self, mock_print, mock_env, mock_file, mock_exit):
        mock_env.return_value = "main"
        
        def mock_file_content(filename, *args, **kwargs):
            if "README.md" in filename:
                return mock_open(read_data="# Headless Dive Automation (v3.2.1)")()
            elif "SKILL.md" in filename:
                return mock_open(read_data="Paralenz Rendering Standards (v3.0.0 Modular Architecture)")()
            elif "CHANGELOG.md" in filename:
                return mock_open(read_data="## [v3.1.0]")()
            return mock_open(read_data="")()
            
        mock_file.side_effect = mock_file_content
        
        with self.assertRaises(SystemExit):
            check_versions()
        mock_exit.assert_called_once_with(1)

if __name__ == "__main__":
    unittest.main()
