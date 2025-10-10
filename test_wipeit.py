#!/usr/bin/env python3
"""
Unit tests for wipeit - Secure device wiping utility
"""

import unittest
import tempfile
import os
import json
import time
import sys
from unittest.mock import patch, mock_open, MagicMock
from io import StringIO

# Add the current directory to the path so we can import wipeit
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import wipeit


class TestParseSize(unittest.TestCase):
    """Test the parse_size function for buffer size parsing."""

    def test_valid_sizes(self):
        """Test parsing of valid size strings."""
        test_cases = [
            ('1M', 1024 * 1024),
            ('100M', 100 * 1024 * 1024),
            ('1G', 1024 * 1024 * 1024),
            ('500M', 500 * 1024 * 1024),
            ('1T', 1024 * 1024 * 1024 * 1024),
            ('0.5G', int(0.5 * 1024 * 1024 * 1024)),
            ('2.5G', int(2.5 * 1024 * 1024 * 1024)),
        ]

        for size_str, expected in test_cases:
            with self.subTest(size=size_str):
                result = wipeit.parse_size(size_str)
                self.assertEqual(result, expected)

    def test_case_insensitive(self):
        """Test that size parsing is case insensitive."""
        self.assertEqual(wipeit.parse_size('1m'), 1024 * 1024)
        self.assertEqual(wipeit.parse_size('1g'), 1024 * 1024 * 1024)
        self.assertEqual(wipeit.parse_size('1t'), 1024 * 1024 * 1024 * 1024)

    def test_invalid_sizes(self):
        """Test that invalid size strings raise ValueError."""
        invalid_sizes = [
            '500K',  # Wrong suffix
            '2T',    # Too large
            '0.5M',  # Too small
            'ABC',   # Not a number
            '100',   # No suffix
            '100MB', # Wrong suffix format
            '1.5.2G', # Invalid decimal
        ]

        for size_str in invalid_sizes:
            with self.subTest(size=size_str):
                with self.assertRaises(ValueError):
                    wipeit.parse_size(size_str)

    def test_empty_string(self):
        """Test that empty string raises IndexError."""
        with self.assertRaises(IndexError):
            wipeit.parse_size('')

    def test_boundary_values(self):
        """Test boundary values (1M minimum, 1T maximum)."""
        # Test minimum valid size
        self.assertEqual(wipeit.parse_size('1M'), 1024 * 1024)

        # Test maximum valid size
        self.assertEqual(wipeit.parse_size('1T'), 1024 * 1024 * 1024 * 1024)

        # Test just under minimum
        with self.assertRaises(ValueError):
            wipeit.parse_size('0.9M')

        # Test just over maximum
        with self.assertRaises(ValueError):
            wipeit.parse_size('1.1T')


class TestProgressFileFunctions(unittest.TestCase):
    """Test progress file management functions."""

    def setUp(self):
        """Set up test environment."""
        self.test_device = '/dev/sdb'
        self.test_progress_file = 'wipeit_progress_sdb.json'

        # Clean up any existing test progress files
        if os.path.exists(self.test_progress_file):
            os.remove(self.test_progress_file)

    def tearDown(self):
        """Clean up test environment."""
        if os.path.exists(self.test_progress_file):
            os.remove(self.test_progress_file)

    def test_get_progress_file(self):
        """Test progress file path generation."""
        result = wipeit.get_progress_file(self.test_device)
        expected = 'wipeit_progress_sdb.json'
        self.assertEqual(result, expected)

        # Test with different device
        result = wipeit.get_progress_file('/dev/nvme0n1')
        expected = 'wipeit_progress_nvme0n1.json'
        self.assertEqual(result, expected)

    def test_save_progress(self):
        """Test saving progress to file."""
        written = 1024 * 1024 * 1024  # 1GB
        total_size = 4 * 1024 * 1024 * 1024  # 4GB
        chunk_size = 100 * 1024 * 1024  # 100MB

        wipeit.save_progress(self.test_device, written, total_size, chunk_size)

        # Check that file was created
        self.assertTrue(os.path.exists(self.test_progress_file))

        # Check file contents
        with open(self.test_progress_file, 'r') as f:
            data = json.load(f)

        self.assertEqual(data['device'], self.test_device)
        self.assertEqual(data['written'], written)
        self.assertEqual(data['total_size'], total_size)
        self.assertEqual(data['chunk_size'], chunk_size)
        self.assertEqual(data['progress_percent'], 25.0)
        self.assertIn('timestamp', data)

    def test_load_progress(self):
        """Test loading progress from file."""
        # Create a test progress file
        test_data = {
            'device': self.test_device,
            'written': 1024 * 1024 * 1024,
            'total_size': 4 * 1024 * 1024 * 1024,
            'chunk_size': 100 * 1024 * 1024,
            'timestamp': time.time(),
            'progress_percent': 25.0
        }

        with open(self.test_progress_file, 'w') as f:
            json.dump(test_data, f)

        # Test loading
        result = wipeit.load_progress(self.test_device)
        self.assertIsNotNone(result)
        self.assertEqual(result['device'], self.test_device)
        self.assertEqual(result['written'], test_data['written'])

    def test_load_progress_nonexistent(self):
        """Test loading progress from nonexistent file."""
        result = wipeit.load_progress('/dev/nonexistent')
        self.assertIsNone(result)

    def test_load_progress_expired(self):
        """Test loading progress from expired file."""
        # Create an expired progress file (older than 24 hours)
        test_data = {
            'device': self.test_device,
            'written': 1024 * 1024 * 1024,
            'total_size': 4 * 1024 * 1024 * 1024,
            'chunk_size': 100 * 1024 * 1024,
            'timestamp': time.time() - 86401,  # 24 hours + 1 second ago
            'progress_percent': 25.0
        }

        with open(self.test_progress_file, 'w') as f:
            json.dump(test_data, f)

        result = wipeit.load_progress(self.test_device)
        self.assertIsNone(result)

    def test_load_progress_wrong_device(self):
        """Test loading progress with wrong device."""
        test_data = {
            'device': '/dev/sdc',  # Different device
            'written': 1024 * 1024 * 1024,
            'total_size': 4 * 1024 * 1024 * 1024,
            'chunk_size': 100 * 1024 * 1024,
            'timestamp': time.time(),
            'progress_percent': 25.0
        }

        with open(self.test_progress_file, 'w') as f:
            json.dump(test_data, f)

        result = wipeit.load_progress(self.test_device)
        self.assertIsNone(result)

    def test_clear_progress(self):
        """Test clearing progress file."""
        # Create a test progress file
        wipeit.save_progress(self.test_device, 1024, 4096, 100)
        self.assertTrue(os.path.exists(self.test_progress_file))

        # Clear it
        wipeit.clear_progress(self.test_device)
        self.assertFalse(os.path.exists(self.test_progress_file))

    def test_clear_progress_nonexistent(self):
        """Test clearing nonexistent progress file."""
        # Should not raise an exception
        wipeit.clear_progress('/dev/nonexistent')


class TestResumeFileFunctions(unittest.TestCase):
    """Test resume file detection and display functions."""

    def setUp(self):
        """Set up test environment."""
        self.test_progress_files = [
            'wipeit_progress_sdb.json',
            'wipeit_progress_sdc.json'
        ]

        # Clean up any existing test progress files
        for file in self.test_progress_files:
            if os.path.exists(file):
                os.remove(file)

    def tearDown(self):
        """Clean up test environment."""
        for file in self.test_progress_files:
            if os.path.exists(file):
                os.remove(file)

    def test_find_resume_files_empty(self):
        """Test finding resume files when none exist."""
        result = wipeit.find_resume_files()
        self.assertEqual(len(result), 0)

    def test_find_resume_files_with_valid_files(self):
        """Test finding resume files with valid files."""
        # Create test progress files
        test_data = {
            'device': '/dev/sdb',
            'written': 1024 * 1024 * 1024,
            'total_size': 4 * 1024 * 1024 * 1024,
            'chunk_size': 100 * 1024 * 1024,
            'timestamp': time.time(),
            'progress_percent': 25.0
        }

        with open('wipeit_progress_sdb.json', 'w') as f:
            json.dump(test_data, f)

        result = wipeit.find_resume_files()
        self.assertEqual(len(result), 1)
        self.assertEqual(result[0]['device'], '/dev/sdb')

    def test_find_resume_files_with_expired_files(self):
        """Test finding resume files with expired files."""
        # Create expired progress file
        test_data = {
            'device': '/dev/sdb',
            'written': 1024 * 1024 * 1024,
            'total_size': 4 * 1024 * 1024 * 1024,
            'chunk_size': 100 * 1024 * 1024,
            'timestamp': time.time() - 86401,  # Expired
            'progress_percent': 25.0
        }

        with open('wipeit_progress_sdb.json', 'w') as f:
            json.dump(test_data, f)

        result = wipeit.find_resume_files()
        self.assertEqual(len(result), 0)

    def test_display_resume_info_no_files(self):
        """Test display_resume_info with no resume files."""
        result = wipeit.display_resume_info()
        self.assertFalse(result)

    def test_display_resume_info_with_files(self):
        """Test display_resume_info with resume files."""
        # Create test progress file
        test_data = {
            'device': '/dev/sdb',
            'written': 1024 * 1024 * 1024,
            'total_size': 4 * 1024 * 1024 * 1024,
            'chunk_size': 100 * 1024 * 1024,
            'timestamp': time.time(),
            'progress_percent': 25.0
        }

        with open('wipeit_progress_sdb.json', 'w') as f:
            json.dump(test_data, f)

        # Capture output
        with patch('sys.stdout', new_callable=StringIO) as mock_stdout:
            result = wipeit.display_resume_info()

        self.assertTrue(result)
        output = mock_stdout.getvalue()
        self.assertIn('Found pending wipe operations', output)
        self.assertIn('/dev/sdb', output)
        self.assertIn('25.00% complete', output)


class TestDeviceInfoFunctions(unittest.TestCase):
    """Test device information functions."""

    @patch('subprocess.check_output')
    def test_get_device_info(self, mock_check_output):
        """Test getting device information."""
        # Mock subprocess outputs
        mock_check_output.side_effect = [
            b'1073741824\n',  # blockdev --getsize64
            b'ID_MODEL=Samsung_SSD\nID_SERIAL_SHORT=12345\n',  # udevadm info
            b'NAME SIZE TYPE MOUNTPOINTS\nsdb 1G disk\n',  # lsblk
            b'/dev/sda1 on /boot\n',  # mount
        ]

        with patch('sys.stdout', new_callable=StringIO) as mock_stdout:
            wipeit.get_device_info('/dev/sdb')

        output = mock_stdout.getvalue()
        self.assertIn('Device: /dev/sdb', output)
        self.assertIn('Size: 1.00 GB', output)
        self.assertIn('Model: Samsung_SSD', output)
        self.assertIn('Serial: 12345', output)

    @patch('subprocess.check_output')
    def test_list_all_devices(self, mock_check_output):
        """Test listing all devices."""
        # Mock subprocess outputs
        mock_check_output.side_effect = [
            b'NAME TYPE\nsda disk\nsdb disk\n',  # lsblk -dno NAME,TYPE
            b'1073741824\n',  # blockdev --getsize64 (for sda)
            b'ID_MODEL=Samsung_SSD\n',  # udevadm info (for sda)
            b'NAME SIZE TYPE MOUNTPOINTS\nsda 1G disk\n',  # lsblk (for sda)
            b'/dev/sda1 on /boot\n',  # mount (for sda)
            b'2147483648\n',  # blockdev --getsize64 (for sdb)
            b'ID_MODEL=USB_Drive\n',  # udevadm info (for sdb)
            b'NAME SIZE TYPE MOUNTPOINTS\nsdb 2G disk\n',  # lsblk (for sdb)
            b'/dev/sda1 on /boot\n',  # mount (for sdb)
        ]

        with patch('sys.stdout', new_callable=StringIO) as mock_stdout:
            wipeit.list_all_devices()

        output = mock_stdout.getvalue()
        self.assertIn('Device: /dev/sda', output)
        self.assertIn('Device: /dev/sdb', output)


class TestMainFunction(unittest.TestCase):
    """Test the main function and argument parsing."""

    @patch('sys.argv', ['wipeit.py', '--help'])
    @patch('sys.stdout', new_callable=StringIO)
    def test_help_option(self, mock_stdout):
        """Test that --help option works."""
        with self.assertRaises(SystemExit) as cm:
            wipeit.main()

        self.assertEqual(cm.exception.code, 0)
        output = mock_stdout.getvalue()
        self.assertIn('usage:', output)
        self.assertIn('--help', output)
        self.assertIn('--version', output)
        self.assertIn('--resume', output)
        self.assertIn('--buffer-size', output)

    @patch('sys.argv', ['wipeit.py', '--version'])
    @patch('sys.stdout', new_callable=StringIO)
    def test_version_option(self, mock_stdout):
        """Test that --version option works."""
        with self.assertRaises(SystemExit) as cm:
            wipeit.main()

        self.assertEqual(cm.exception.code, 0)
        output = mock_stdout.getvalue()
        self.assertIn('wipeit 0.1.0', output)

    @patch('sys.argv', ['wipeit.py'])
    @patch('os.geteuid', return_value=0)  # Mock root user
    @patch('wipeit.display_resume_info', return_value=False)
    @patch('wipeit.list_all_devices')
    def test_main_no_args_as_root(self, mock_list_devices, mock_display_resume, mock_geteuid):
        """Test main function with no arguments as root."""
        wipeit.main()
        mock_display_resume.assert_called_once()
        mock_list_devices.assert_called_once()

    @patch('sys.argv', ['wipeit.py'])
    @patch('os.geteuid', return_value=1000)  # Mock non-root user
    @patch('wipeit.display_resume_info', return_value=False)
    @patch('sys.exit')
    def test_main_no_args_as_non_root(self, mock_exit, mock_display_resume, mock_geteuid):
        """Test main function with no arguments as non-root."""
        wipeit.main()
        mock_display_resume.assert_called_once()
        mock_exit.assert_called_once_with(1)

    @patch('sys.argv', ['wipeit.py', '/dev/sdb'])
    @patch('os.geteuid', return_value=1000)  # Mock non-root user
    @patch('builtins.input', return_value='n')  # Mock user input
    @patch('sys.exit')
    def test_main_with_device_as_non_root(self, mock_exit, mock_input, mock_geteuid):
        """Test main function with device argument as non-root."""
        wipeit.main()
        mock_exit.assert_called_once_with(1)


class TestIntegration(unittest.TestCase):
    """Integration tests for the complete workflow."""

    def setUp(self):
        """Set up test environment."""
        self.test_progress_file = 'wipeit_progress_test.json'
        if os.path.exists(self.test_progress_file):
            os.remove(self.test_progress_file)

    def tearDown(self):
        """Clean up test environment."""
        if os.path.exists(self.test_progress_file):
            os.remove(self.test_progress_file)

    def test_progress_workflow(self):
        """Test the complete progress save/load/clear workflow."""
        device = '/dev/test'
        written = 1024 * 1024 * 1024
        total_size = 4 * 1024 * 1024 * 1024
        chunk_size = 100 * 1024 * 1024

        # Save progress
        wipeit.save_progress(device, written, total_size, chunk_size)

        # Load progress
        progress = wipeit.load_progress(device)
        self.assertIsNotNone(progress)
        self.assertEqual(progress['written'], written)

        # Clear progress
        wipeit.clear_progress(device)

        # Verify cleared
        progress = wipeit.load_progress(device)
        self.assertIsNone(progress)

    def test_size_parsing_workflow(self):
        """Test size parsing with various inputs."""
        test_cases = [
            ('1M', 1024 * 1024),
            ('100M', 100 * 1024 * 1024),
            ('1G', 1024 * 1024 * 1024),
            ('0.5G', int(0.5 * 1024 * 1024 * 1024)),
        ]

        for size_str, expected in test_cases:
            with self.subTest(size=size_str):
                result = wipeit.parse_size(size_str)
                self.assertEqual(result, expected)


if __name__ == '__main__':
    # Create a test suite
    test_suite = unittest.TestSuite()

    # Add test classes
    test_classes = [
        TestParseSize,
        TestProgressFileFunctions,
        TestResumeFileFunctions,
        TestDeviceInfoFunctions,
        TestMainFunction,
        TestIntegration,
    ]

    for test_class in test_classes:
        tests = unittest.TestLoader().loadTestsFromTestCase(test_class)
        test_suite.addTests(tests)

    # Run the tests
    runner = unittest.TextTestRunner(verbosity=2)
    result = runner.run(test_suite)

    # Exit with appropriate code
    sys.exit(0 if result.wasSuccessful() else 1)
