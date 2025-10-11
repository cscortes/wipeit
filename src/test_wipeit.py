#!/usr/bin/env python3
"""
Unit tests for wipeit - Secure device wiping utility
"""

import json
import os
import subprocess
import sys
import time
import unittest
from io import StringIO
from unittest.mock import MagicMock, mock_open, patch

# Import modules from the same directory
import wipeit
from global_constants import (
    GIGABYTE,
    MEGABYTE,
    TERABYTE,
    TEST_CHUNK_SIZE_100MB,
    TEST_DEVICE_SIZE_100GB,
    TEST_DEVICE_SIZE_100MB,
    TEST_TIME_1_HOUR_SECONDS,
    TEST_TIME_24_HOURS_PLUS_1_SECOND,
    TEST_TOTAL_SIZE_4GB,
    TEST_WRITTEN_1GB,
)


class TestParseSize(unittest.TestCase):
    """Test the parse_size function for buffer size parsing."""

    def test_valid_sizes(self):
        """Test parsing of valid size strings."""
        test_cases = [
            ('1M', MEGABYTE),
            ('100M', 100 * MEGABYTE),
            ('1G', GIGABYTE),
            ('500M', 500 * MEGABYTE),
            ('1T', TERABYTE),
            ('0.5G', int(0.5 * GIGABYTE)),
            ('2.5G', int(2.5 * GIGABYTE)),
        ]

        for size_str, expected in test_cases:
            with self.subTest(size=size_str):
                result = wipeit.parse_size(size_str)
                self.assertEqual(result, expected)

    def test_case_insensitive(self):
        """Test that size parsing is case insensitive."""
        self.assertEqual(wipeit.parse_size('1m'), MEGABYTE)
        self.assertEqual(wipeit.parse_size('1g'), GIGABYTE)
        self.assertEqual(wipeit.parse_size('1t'), TERABYTE)

    def test_invalid_sizes(self):
        """Test that invalid size strings raise ValueError."""
        invalid_sizes = [
            '500K',  # Wrong suffix
            '2T',    # Too large
            '0.5M',  # Too small
            'ABC',   # Not a number
            '100',   # No suffix
            '100MB',  # Wrong suffix format
            '1.5.2G',  # Invalid decimal
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
        self.assertEqual(wipeit.parse_size('1M'), MEGABYTE)

        # Test maximum valid size
        self.assertEqual(wipeit.parse_size('1T'), TERABYTE)

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
        self.test_progress_file = 'wipeit_progress.json'

        # Clean up any existing test progress files
        if os.path.exists(self.test_progress_file):
            os.remove(self.test_progress_file)

    def tearDown(self):
        """Clean up test environment."""
        if os.path.exists(self.test_progress_file):
            os.remove(self.test_progress_file)

    def test_get_progress_file(self):
        """Test progress file path generation."""
        # Should always return the same filename regardless of device
        result = wipeit.get_progress_file(self.test_device)
        expected = 'wipeit_progress.json'
        self.assertEqual(result, expected)

        # Test with different device - should return same filename
        result = wipeit.get_progress_file('/dev/nvme0n1')
        expected = 'wipeit_progress.json'
        self.assertEqual(result, expected)

    def test_save_progress(self):
        """Test saving progress to file."""
        written = TEST_WRITTEN_1GB  # 1GB
        total_size = TEST_TOTAL_SIZE_4GB  # 4GB
        chunk_size = TEST_CHUNK_SIZE_100MB  # 100MB

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
            'written': TEST_WRITTEN_1GB,
            'total_size': TEST_TOTAL_SIZE_4GB,
            'chunk_size': TEST_CHUNK_SIZE_100MB,
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
            'written': TEST_WRITTEN_1GB,
            'total_size': TEST_TOTAL_SIZE_4GB,
            'chunk_size': TEST_CHUNK_SIZE_100MB,
            # 24 hours + 1 second ago
            'timestamp': time.time() - TEST_TIME_24_HOURS_PLUS_1_SECOND,
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
            'written': TEST_WRITTEN_1GB,
            'total_size': TEST_TOTAL_SIZE_4GB,
            'chunk_size': TEST_CHUNK_SIZE_100MB,
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
        self.test_progress_file = 'wipeit_progress.json'

        # Clean up any existing test progress file
        if os.path.exists(self.test_progress_file):
            os.remove(self.test_progress_file)

    def tearDown(self):
        """Clean up test environment."""
        if os.path.exists(self.test_progress_file):
            os.remove(self.test_progress_file)

    def test_find_resume_files_empty(self):
        """Test finding resume files when none exist."""
        result = wipeit.find_resume_files()
        self.assertEqual(len(result), 0)

    def test_find_resume_files_with_valid_files(self):
        """Test finding resume files with valid files."""
        # Create test progress file
        test_data = {
            'device': '/dev/sdb',
            'written': TEST_WRITTEN_1GB,
            'total_size': TEST_TOTAL_SIZE_4GB,
            'chunk_size': TEST_CHUNK_SIZE_100MB,
            'timestamp': time.time(),
            'progress_percent': 25.0
        }

        with open(self.test_progress_file, 'w') as f:
            json.dump(test_data, f)

        result = wipeit.find_resume_files()
        self.assertEqual(len(result), 1)
        self.assertEqual(result[0]['device'], '/dev/sdb')

    def test_find_resume_files_with_expired_files(self):
        """Test finding resume files with expired files."""
        # Create expired progress file
        test_data = {
            'device': '/dev/sdb',
            'written': TEST_WRITTEN_1GB,
            'total_size': TEST_TOTAL_SIZE_4GB,
            'chunk_size': TEST_CHUNK_SIZE_100MB,
            'timestamp': time.time() - 86401,  # Expired
            'progress_percent': 25.0
        }

        with open(self.test_progress_file, 'w') as f:
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
            'written': TEST_WRITTEN_1GB,
            'total_size': TEST_TOTAL_SIZE_4GB,
            'chunk_size': TEST_CHUNK_SIZE_100MB,
            'timestamp': time.time(),
            'progress_percent': 25.0
        }

        with open(self.test_progress_file, 'w') as f:
            json.dump(test_data, f)

        # Capture output
        with patch('sys.stdout', new_callable=StringIO) as mock_stdout:
            result = wipeit.display_resume_info()

        self.assertTrue(result)
        output = mock_stdout.getvalue()
        self.assertIn('Found previous wipe sessions', output)
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
            detector = wipeit.DeviceDetector('/dev/sdb')
            detector.display_info()

        output = mock_stdout.getvalue()
        self.assertIn('Device: /dev/sdb', output)
        self.assertIn('Size: 1.00 GB', output)
        self.assertIn('Model: Samsung_SSD', output)
        self.assertIn('Serial: 12345', output)

    @patch('subprocess.check_output')
    def test_list_all_devices(self, mock_check_output):
        """Test listing all devices."""
        # Mock subprocess outputs for lsblk command in list_all_devices
        mock_check_output.side_effect = [
            b'NAME TYPE\nsda disk\nsdb disk\n',  # lsblk -dno NAME,TYPE
        ]

        # Mock DeviceDetector methods for each device
        with patch('wipeit.DeviceDetector') as mock_detector_class:
            # Create mock detector instances
            mock_detector_sda = MagicMock()
            mock_detector_sdb = MagicMock()

            # Set up the mock to return different instances for different
            # devices
            def mock_detector_side_effect(device_path):
                if device_path == '/dev/sda':
                    return mock_detector_sda
                elif device_path == '/dev/sdb':
                    return mock_detector_sdb
                return MagicMock()

            mock_detector_class.side_effect = mock_detector_side_effect

            with patch('sys.stdout', new_callable=StringIO) as mock_stdout:
                wipeit.list_all_devices()

            # Verify that display_info was called for each device
            mock_detector_sda.display_info.assert_called_once()
            mock_detector_sdb.display_info.assert_called_once()

            output = mock_stdout.getvalue()
            # The output should contain the separator lines
            self.assertIn('---', output)


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
        self.assertIn('wipeit 1.3.1', output)

    @patch('sys.argv', ['wipeit.py'])
    @patch('os.geteuid', return_value=0)  # Mock root user
    @patch('wipeit.display_resume_info', return_value=False)
    @patch('wipeit.list_all_devices')
    def test_main_no_args_as_root(self, mock_list_devices,
                                  mock_display_resume, mock_geteuid):
        """Test main function with no arguments as root."""
        wipeit.main()
        mock_display_resume.assert_called_once()
        mock_list_devices.assert_called_once()

    @patch('sys.argv', ['wipeit.py'])
    @patch('os.geteuid', return_value=1000)  # Mock non-root user
    @patch('wipeit.display_resume_info', return_value=False)
    @patch('sys.exit')
    def test_main_no_args_as_non_root(self, mock_exit, mock_display_resume,
                                      mock_geteuid):
        """Test main function with no arguments as non-root."""
        wipeit.main()
        mock_display_resume.assert_called_once()
        mock_exit.assert_called_once_with(1)

    @patch('sys.argv', ['wipeit.py', '/dev/sdb'])
    @patch('os.geteuid', return_value=1000)  # Mock non-root user
    @patch('builtins.input', return_value='n')  # Mock user input
    @patch('wipeit.display_resume_info', return_value=False)
    @patch('wipeit.DeviceDetector.display_info')
    @patch('wipeit.DeviceDetector.is_mounted', return_value=(False, []))
    @patch('wipeit.load_progress', return_value=None)
    @patch('wipeit.clear_progress')
    @patch('sys.exit')
    def test_main_with_device_as_non_root(self, mock_exit, mock_clear_progress,
                                          mock_load_progress,
                                          mock_check_mounted,
                                          mock_get_info, mock_display_resume,
                                          mock_input, mock_geteuid):
        """Test main function with device argument as non-root."""
        wipeit.main()
        # The function should exit with code 1 due to permission denied
        # Check that exit was called with code 1 at least once
        exit_calls = [call[0][0] for call in mock_exit.call_args_list]
        self.assertIn(1, exit_calls)


class TestIntegration(unittest.TestCase):
    """Integration tests for the complete workflow."""

    def setUp(self):
        """Set up test environment."""
        self.test_progress_file = 'wipeit_progress.json'
        if os.path.exists(self.test_progress_file):
            os.remove(self.test_progress_file)

    def tearDown(self):
        """Clean up test environment."""
        if os.path.exists(self.test_progress_file):
            os.remove(self.test_progress_file)

    @patch('sys.argv', ['wipeit.py', '/dev/sdb'])
    @patch('os.geteuid', return_value=0)
    @patch('os.path.exists', return_value=True)
    @patch('builtins.input', return_value='n')
    @patch('wipeit.DeviceDetector')
    @patch('wipeit.load_progress', return_value=None)
    @patch('wipeit.clear_progress')
    @patch('sys.exit')
    def test_main_shows_resume_prompt_when_progress_exists(
            self, mock_exit, mock_clear_progress, mock_load_progress,
            mock_detector_class, mock_input, mock_path_exists, mock_geteuid):
        """Test that main() displays resume info when progress file exists.

        This is a critical user-facing feature: when starting wipeit with
        a device argument, if a progress file exists, the user should see:
        1. RESUME OPTIONS section with details
        2. "Use --resume flag to continue" message
        """
        # Create real progress file
        test_data = {
            'device': '/dev/sdb',
            'written': 500 * 1024 * 1024 * 1024,  # 500GB
            'total_size': 1000 * 1024 * 1024 * 1024,  # 1TB
            'chunk_size': 100 * 1024 * 1024,
            'timestamp': time.time(),
            'progress_percent': 50.0
        }
        with open(self.test_progress_file, 'w') as f:
            json.dump(test_data, f)

        # Mock DeviceDetector
        mock_detector = MagicMock()
        mock_detector.is_mounted.return_value = (False, [])
        mock_detector_class.return_value = mock_detector

        # Capture output
        with patch('sys.stdout', new_callable=StringIO) as mock_stdout:
            wipeit.main()

        output = mock_stdout.getvalue()

        # CRITICAL CHECKS: Verify user sees resume information
        self.assertIn(
            'RESUME OPTIONS', output,
            "User should see RESUME OPTIONS header")
        self.assertIn(
            'Found previous wipe sessions', output,
            "User should see message about previous sessions")
        self.assertIn(
            '/dev/sdb', output,
            "User should see device name in resume info")
        self.assertIn(
            '50.00% complete', output,
            "User should see progress percentage")
        self.assertIn(
            '500.00 GB / 1000.00 GB', output,
            "User should see written/total GB")
        self.assertIn(
            'Use --resume flag to continue', output,
            "User should see instruction to use --resume flag")

    @patch('sys.argv', ['wipeit.py', '/dev/sdb'])
    @patch('os.geteuid', return_value=0)
    @patch('os.path.exists', return_value=True)
    @patch('builtins.input', return_value='n')
    @patch('wipeit.DeviceDetector')
    @patch('wipeit.load_progress', return_value=None)
    @patch('wipeit.clear_progress')
    @patch('sys.exit')
    def test_main_no_resume_prompt_when_no_progress(
            self, mock_exit, mock_clear_progress, mock_load_progress,
            mock_detector_class, mock_input, mock_path_exists, mock_geteuid):
        """Test main() doesn't show resume info when no progress exists."""
        # NO progress file created

        # Mock DeviceDetector
        mock_detector = MagicMock()
        mock_detector.is_mounted.return_value = (False, [])
        mock_detector_class.return_value = mock_detector

        # Capture output
        with patch('sys.stdout', new_callable=StringIO) as mock_stdout:
            wipeit.main()

        output = mock_stdout.getvalue()

        # Should NOT see resume messages
        self.assertNotIn(
            'RESUME OPTIONS', output,
            "Should not see RESUME OPTIONS when no progress")
        self.assertNotIn(
            'Use --resume flag to continue', output,
            "Should not see resume instruction when no progress")

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

    def test_milestone_tracking_logic(self):
        """Test the milestone tracking logic for estimated finish time."""
        # Test milestone calculation
        size = 1000

        # Test various progress levels
        test_cases = [
            (50, 5),    # 5% milestone
            (100, 10),  # 10% milestone
            (150, 15),  # 15% milestone
            (200, 20),  # 20% milestone
            (250, 25),  # 25% milestone
            (300, 30),  # 30% milestone
            (350, 35),  # 35% milestone
            (400, 40),  # 40% milestone
            (450, 45),  # 45% milestone
            (500, 50),  # 50% milestone
        ]

        for written, expected_milestone in test_cases:
            current_milestone = int(written / size * 100) // 5 * 5
            self.assertEqual(current_milestone, expected_milestone,
                             f"Failed for written={written}, "
                             f"expected={expected_milestone}, "
                             f"got={current_milestone}")

    @patch('time.time')
    @patch('time.strftime')
    def test_estimated_finish_time_formatting(self, mock_strftime, mock_time):
        """Test the estimated finish time formatting."""
        # Mock current time
        mock_time.return_value = 1640000000  # Fixed timestamp
        mock_strftime.return_value = "07:40 PM"

        # Test time calculation
        current_time = time.time()
        eta_seconds = TEST_TIME_1_HOUR_SECONDS  # 1 hour
        estimated_finish = current_time + eta_seconds
        finish_time_str = time.strftime("%I:%M %p",
                                        time.localtime(estimated_finish))

        # Verify the formatting was called correctly
        mock_strftime.assert_called_with("%I:%M %p",
                                         time.localtime(estimated_finish))
        self.assertEqual(finish_time_str, "07:40 PM")


class TestHDDPretest(unittest.TestCase):
    """Test HDD pretest functionality."""

    @patch('wipeit.get_block_device_size')
    @patch('builtins.open', new_callable=mock_open)
    @patch('os.urandom')
    @patch('time.time')
    def test_pretest_successful(self, mock_time, mock_urandom, mock_file,
                                mock_size):
        """Test successful HDD pretest."""
        # Mock device size
        mock_size.return_value = TEST_DEVICE_SIZE_100GB  # 100GB

        # Mock random data
        mock_urandom.return_value = b'test_data' * 1000

        # Mock time for speed calculation
        mock_time.side_effect = [0, 1, 1, 2, 2, 3]  # Different durations

        # Mock file operations
        mock_file.return_value.__enter__.return_value.seek = MagicMock()
        mock_file.return_value.__enter__.return_value.write = MagicMock()
        mock_file.return_value.__enter__.return_value.flush = MagicMock()
        mock_file.return_value.__enter__.return_value.fileno.return_value = 1

        with patch('os.fsync'):
            with patch('sys.stdout', new_callable=StringIO) as mock_stdout:
                result = wipeit.perform_hdd_pretest('/dev/sdb',
                                                    TEST_CHUNK_SIZE_100MB)

        # Verify pretest was performed
        self.assertIsNotNone(result)
        self.assertIn('analysis', result)
        self.assertIn('recommended_algorithm', result['analysis'])

        # Check output contains expected messages
        output = mock_stdout.getvalue()
        self.assertIn('Performing HDD pretest', output)
        self.assertIn('Testing beginning of disk', output)
        self.assertIn('Testing middle of disk', output)
        self.assertIn('Testing end of disk', output)
        self.assertIn('PRETEST ANALYSIS', output)

    @patch('wipeit.get_block_device_size')
    @patch('builtins.open', new_callable=mock_open)
    @patch('os.urandom')
    @patch('time.time')
    def test_pretest_adaptive_algorithm(self, mock_time, mock_urandom,
                                        mock_file, mock_size):
        """Test pretest recommending adaptive algorithm."""
        # Mock device size
        mock_size.return_value = TEST_DEVICE_SIZE_100GB  # 100GB

        # Mock random data
        mock_urandom.return_value = b'test_data' * 1000

        # Mock time to simulate high speed variance (adaptive algorithm)
        mock_time.side_effect = [0, 0.1, 0.1, 0.5, 0.5, 1.0]

        # Mock file operations
        mock_file.return_value.__enter__.return_value.seek = MagicMock()
        mock_file.return_value.__enter__.return_value.write = MagicMock()
        mock_file.return_value.__enter__.return_value.flush = MagicMock()
        mock_file.return_value.__enter__.return_value.fileno.return_value = 1

        with patch('os.fsync'):
            result = wipeit.perform_hdd_pretest('/dev/sdb',
                                                TEST_CHUNK_SIZE_100MB)

        # Verify adaptive algorithm is recommended
        self.assertEqual(result['analysis']['recommended_algorithm'],
                         'adaptive_chunk')

    @patch('wipeit.get_block_device_size')
    @patch('builtins.open', new_callable=mock_open)
    @patch('os.urandom')
    @patch('time.time')
    def test_pretest_small_chunk_algorithm(self, mock_time, mock_urandom,
                                           mock_file, mock_size):
        """Test pretest recommending small chunk algorithm."""
        # Mock device size
        mock_size.return_value = TEST_DEVICE_SIZE_100GB  # 100GB

        # Mock random data
        mock_urandom.return_value = b'test_data' * 1000

        # Mock time to simulate very slow speeds (small chunk algorithm)
        # Need much slower speeds to trigger small_chunk algorithm
        # (< 50 MB/s average)
        mock_time.side_effect = [0, 10, 10, 20, 20, 30]  # Very slow speeds

        # Mock file operations
        mock_file.return_value.__enter__.return_value.seek = MagicMock()
        mock_file.return_value.__enter__.return_value.write = MagicMock()
        mock_file.return_value.__enter__.return_value.flush = MagicMock()
        mock_file.return_value.__enter__.return_value.fileno.return_value = 1

        with patch('os.fsync'):
            result = wipeit.perform_hdd_pretest('/dev/sdb',
                                                TEST_CHUNK_SIZE_100MB)

        # Verify small chunk algorithm is recommended
        self.assertEqual(result['analysis']['recommended_algorithm'],
                         'small_chunk')


class TestWipeDeviceIntegration(unittest.TestCase):
    """Test wipe_device function with pretest integration."""

    @patch('wipeit.get_block_device_size')
    @patch('builtins.open', new_callable=mock_open)
    @patch('time.time')
    def test_wipe_device_with_adaptive_chunk(self, mock_time, mock_file,
                                             mock_size):
        """Test wipe_device with adaptive chunk - CRITICAL BUG TEST."""
        mock_size.return_value = TEST_DEVICE_SIZE_100MB

        mock_time.return_value = 1000.0
        mock_file.return_value.__enter__.return_value.seek = MagicMock()
        mock_file.return_value.__enter__.return_value.write = MagicMock()
        mock_file.return_value.__enter__.return_value.flush = MagicMock()
        mock_file.return_value.__enter__.return_value.fileno.return_value = 1

        mock_pretest_results = {
            'analysis': {
                'recommended_algorithm': 'adaptive_chunk',
                'average_speed': 50.0,
                'speed_variance': 30.0
            },
            'recommended_algorithm': 'adaptive_chunk'
        }

        with patch('os.fsync'):
            with patch('wipeit.perform_hdd_pretest',
                       return_value=mock_pretest_results):
                with patch('wipeit.DeviceDetector.detect_type',
                           return_value=('HDD', 'HIGH', ['rotational=1'])):
                    with patch('sys.stdout', new_callable=StringIO):
                        try:
                            wipeit.wipe_device('/dev/sdb',
                                               TEST_CHUNK_SIZE_100MB,
                                               skip_pretest=False)
                        except TypeError as e:
                            err_str = ("'float' object cannot be "
                                       "interpreted as an integer")
                            if err_str in str(e):
                                self.fail("CRITICAL BUG: float to int "
                                          "conversion error occurred")
                            else:
                                raise

    @patch('wipeit.get_block_device_size')
    @patch('builtins.open', new_callable=mock_open)
    @patch('time.time')
    def test_adaptive_chunk_sizing_calculations(self, mock_time, mock_file,
                                                mock_size):
        """Test that adaptive chunk sizing produces integers."""
        mock_size.return_value = 100 * 1024 * 1024

        mock_time.return_value = 1000.0
        mock_file.return_value.__enter__.return_value.seek = MagicMock()
        mock_file.return_value.__enter__.return_value.write = MagicMock()
        mock_file.return_value.__enter__.return_value.flush = MagicMock()
        mock_file.return_value.__enter__.return_value.fileno.return_value = 1

        mock_pretest_results = {
            'analysis': {
                'recommended_algorithm': 'adaptive_chunk'
            },
            'recommended_algorithm': 'adaptive_chunk'
        }

        with patch('os.fsync'):
            with patch('wipeit.perform_hdd_pretest',
                       return_value=mock_pretest_results):
                with patch('wipeit.DeviceDetector.detect_type',
                           return_value=('HDD', 'HIGH', ['rotational=1'])):
                    with patch('sys.stdout', new_callable=StringIO):
                        write_calls = []
                        original_write = (mock_file.return_value
                                          .__enter__.return_value.write)

                        def mock_write(data):
                            write_calls.append(len(data))
                            return original_write(data)

                        (mock_file.return_value.__enter__.return_value
                         .write) = mock_write

                        wipeit.wipe_device('/dev/sdb',
                                           TEST_CHUNK_SIZE_100MB,
                                           skip_pretest=False)

                        self.assertGreater(len(write_calls), 0)
                        for size in write_calls:
                            self.assertIsInstance(size, int)


class TestMountChecking(unittest.TestCase):
    """Test mount checking functionality."""

    @patch('wipeit.subprocess.check_output')
    def test_check_device_mounted_not_mounted(self, mock_check_output):
        """Test check_device_mounted when device is not mounted."""
        # Mock mount command output (device not in mount list)
        mock_check_output.side_effect = [
            # mount output
            b'/dev/sda1 on / type ext4 (rw,relatime)\n'
            b'/dev/sda2 on /home type ext4 (rw,relatime)\n',
            b'sdb\nsdb1\n'  # lsblk output (no mountpoints)
        ]

        detector = wipeit.DeviceDetector('/dev/sdb')
        is_mounted, mount_info = detector.is_mounted()

        self.assertFalse(is_mounted)
        self.assertEqual(mount_info, [])
        self.assertEqual(mock_check_output.call_count, 2)

    @patch('wipeit.subprocess.check_output')
    def test_check_device_mounted_device_mounted(self, mock_check_output):
        """Test check_device_mounted when device itself is mounted."""
        # Mock mount command output (device in mount list)
        mock_check_output.side_effect = [
            b'/dev/sdb on /mnt/usb type ext4 (rw,relatime)\n',  # mount output
            b'sdb\nsdb1\n'  # lsblk output
        ]

        detector = wipeit.DeviceDetector('/dev/sdb')
        is_mounted, mount_info = detector.is_mounted()

        self.assertTrue(is_mounted)
        self.assertEqual(mount_info, [])
        self.assertEqual(mock_check_output.call_count, 2)

    @patch('wipeit.subprocess.check_output')
    def test_check_device_mounted_partitions_mounted(self, mock_check_output):
        """Test check_device_mounted when partitions are mounted."""
        # Mock mount command output (device not in mount list)
        mock_check_output.side_effect = [
            b'/dev/sda1 on / type ext4 (rw,relatime)\n',  # mount output
            b'sdb\nsdb1 /mnt/usb\nsdb2 /media/data\n'  # lsblk with mountpoints
        ]

        detector = wipeit.DeviceDetector('/dev/sdb')
        is_mounted, mount_info = detector.is_mounted()

        self.assertTrue(is_mounted)
        self.assertEqual(len(mount_info), 2)
        self.assertIn('/dev/sdb1 -> /mnt/usb', mount_info)
        self.assertIn('/dev/sdb2 -> /media/data', mount_info)
        self.assertEqual(mock_check_output.call_count, 2)

    @patch('wipeit.subprocess.check_output')
    def test_check_device_mounted_error_handling(self, mock_check_output):
        """Test check_device_mounted error handling."""
        # Mock subprocess to raise an exception
        mock_check_output.side_effect = subprocess.CalledProcessError(
            1, 'mount')

        detector = wipeit.DeviceDetector('/dev/sdb')
        is_mounted, mount_info = detector.is_mounted()

        self.assertFalse(is_mounted)
        self.assertEqual(mount_info, [])

    @patch('wipeit.DeviceDetector.is_mounted')
    @patch('wipeit.DeviceDetector.display_info')
    @patch('wipeit.load_progress')
    @patch('wipeit.display_resume_info')
    def test_main_mount_safety_check_mounted(self, mock_display_resume,
                                             mock_load_progress,
                                             mock_get_info,
                                             mock_check_mounted):
        """Test that main function exits when device is mounted."""
        # Mock device is mounted
        mock_check_mounted.return_value = (True, ['/dev/sdb1 -> /mnt/usb'])
        # Mock no previous progress
        mock_load_progress.return_value = None
        # Mock display_resume_info
        mock_display_resume.return_value = False

        # Mock argument parsing
        with patch('argparse.ArgumentParser.parse_args') as mock_parse:
            mock_args = MagicMock()
            mock_args.device = '/dev/sdb'
            mock_args.buffer_size = '100M'
            mock_args.resume = False
            mock_args.skip_pretest = False
            mock_args.list = False
            mock_parse.return_value = mock_args

            # Mock root check
            with patch('os.geteuid', return_value=0):
                # Mock device exists check
                with patch('os.path.exists', return_value=True):
                    # Mock parse_size
                    with patch('wipeit.parse_size',
                               return_value=TEST_CHUNK_SIZE_100MB):
                        # Mock stdout to capture output
                        with patch('sys.stdout', new_callable=StringIO):
                            # Test that SystemExit is raised (sys.exit
                            # behavior)
                            with self.assertRaises(SystemExit) as cm:
                                wipeit.main()
                            # Verify exit code is 1
                            self.assertEqual(cm.exception.code, 1)

        # Verify that is_mounted was called
        # Check if it was called at all
        if mock_check_mounted.call_count == 0:
            self.fail("is_mounted was never called - function may have "
                      "exited early")
        mock_check_mounted.assert_called_once()

    @patch('wipeit.DeviceDetector.is_mounted')
    @patch('wipeit.DeviceDetector.display_info')
    @patch('wipeit.display_resume_info')
    @patch('sys.exit')
    def test_main_mount_safety_check_not_mounted(self, mock_exit,
                                                 mock_display_resume,
                                                 mock_get_info,
                                                 mock_check_mounted):
        """Test that main function continues when device is not mounted."""
        # Mock device is not mounted
        mock_check_mounted.return_value = (False, [])
        # Mock display_resume_info
        mock_display_resume.return_value = False

        # Mock argument parsing
        with patch('argparse.ArgumentParser.parse_args') as mock_parse:
            mock_args = MagicMock()
            mock_args.device = '/dev/sdb'
            mock_args.buffer_size = '100M'
            mock_args.resume = False
            mock_args.skip_pretest = False
            mock_args.list = False
            mock_parse.return_value = mock_args

            # Mock root check
            with patch('os.geteuid', return_value=0):
                # Mock device exists check
                with patch('os.path.exists', return_value=True):
                    # Mock parse_size
                    with patch('wipeit.parse_size',
                               return_value=TEST_CHUNK_SIZE_100MB):
                        # Mock load_progress to return None (no previous
                        # progress)
                        with patch('wipeit.load_progress',
                                   return_value=None):
                            # Mock input to abort
                            with patch('builtins.input', return_value='n'):
                                wipeit.main()

        # Verify that is_mounted was called (mount check happened)
        mock_check_mounted.assert_called_once()
        # The function should have proceeded past the mount check
        # (it may exit later due to user abort, but that's expected)


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
        TestHDDPretest,
        TestWipeDeviceIntegration,
        TestMountChecking,
    ]

    for test_class in test_classes:
        tests = unittest.TestLoader().loadTestsFromTestCase(test_class)
        test_suite.addTests(tests)

    # Run the tests
    runner = unittest.TextTestRunner(verbosity=2)
    result = runner.run(test_suite)

    # Exit with appropriate code
    sys.exit(0 if result.wasSuccessful() else 1)
