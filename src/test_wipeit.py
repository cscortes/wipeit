#!/usr/bin/env python3
"""
Unit tests for wipeit - Secure device wiping utility
"""

import argparse
import json
import os
import subprocess  # noqa: F401 - used in @patch decorator strings
import sys
import time
import unittest
from io import StringIO
from unittest.mock import MagicMock, mock_open, patch

# Import modules from the same directory
import wipeit
from disk_pretest import DiskPretest
from global_constants import (
    GIGABYTE,
    MEGABYTE,
    PROGRESS_FILE_NAME,
    TERABYTE,
    TEST_CHUNK_SIZE_100MB,
    TEST_DEVICE_SIZE_100GB,
    TEST_DEVICE_SIZE_100MB,
    TEST_TIME_1_HOUR_SECONDS,
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
        self.test_progress_file = PROGRESS_FILE_NAME

        # Clean up any existing test progress files
        if os.path.exists(self.test_progress_file):
            os.remove(self.test_progress_file)

    def tearDown(self):
        """Clean up test environment."""
        if os.path.exists(self.test_progress_file):
            os.remove(self.test_progress_file)

    def test_progress_file_constant(self):
        """Test PROGRESS_FILE_NAME constant is defined correctly."""
        from global_constants import PROGRESS_FILE_NAME

        # Should be the expected filename
        self.assertEqual(PROGRESS_FILE_NAME, 'wipeit_progress.json')

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

    def test_clear_progress(self):
        """Test clearing progress file."""
        # Create a test progress file
        wipeit.save_progress(self.test_device, 1024, 4096, 100)
        self.assertTrue(os.path.exists(self.test_progress_file))

        # Clear it
        wipeit.clear_progress()
        self.assertFalse(os.path.exists(self.test_progress_file))

    def test_clear_progress_nonexistent(self):
        """Test clearing nonexistent progress file."""
        # Should not raise an exception
        wipeit.clear_progress()

    def test_progress_percent_calculation(self):
        """Test that progress_percent is correctly calculated when saving."""
        test_cases = [
            (0, TEST_TOTAL_SIZE_4GB, 0.0, "0% progress"),
            (TEST_TOTAL_SIZE_4GB // 4, TEST_TOTAL_SIZE_4GB,
             25.0, "25% progress"),
            (TEST_TOTAL_SIZE_4GB // 2, TEST_TOTAL_SIZE_4GB,
             50.0, "50% progress"),
            (3 * TEST_TOTAL_SIZE_4GB // 4, TEST_TOTAL_SIZE_4GB,
             75.0, "75% progress"),
            (TEST_TOTAL_SIZE_4GB, TEST_TOTAL_SIZE_4GB,
             100.0, "100% progress"),
            (50 * GIGABYTE, 100 * GIGABYTE, 50.0, "50GB/100GB"),
            (1 * GIGABYTE, 10 * GIGABYTE, 10.0, "1GB/10GB"),
        ]

        for written, total, expected_percent, description in test_cases:
            with self.subTest(case=description):
                wipeit.save_progress(
                    self.test_device, written, total, TEST_CHUNK_SIZE_100MB)

                with open(self.test_progress_file, 'r') as f:
                    data = json.load(f)

                self.assertAlmostEqual(
                    data['progress_percent'], expected_percent, places=2,
                    msg=f"Progress percent mismatch for {description}: "
                    f"expected {expected_percent}%, "
                    f"got {data['progress_percent']}%")

                # Also verify written and total_size are saved correctly
                self.assertEqual(
                    data['written'], written,
                    msg=f"Written bytes mismatch for {description}")
                self.assertEqual(
                    data['total_size'], total,
                    msg=f"Total size mismatch for {description}")

    def test_save_progress_with_device_id(self):
        """Test saving progress with device unique identifier."""
        device_id = {
            'serial': 'TEST123456',
            'model': 'TestDrive_Model',
            'size': TEST_TOTAL_SIZE_4GB
        }

        wipeit.save_progress(
            self.test_device, TEST_WRITTEN_1GB, TEST_TOTAL_SIZE_4GB,
            TEST_CHUNK_SIZE_100MB, None, device_id)

        with open(self.test_progress_file, 'r') as f:
            data = json.load(f)

        self.assertIn('device_id', data)
        self.assertEqual(data['device_id']['serial'], 'TEST123456')
        self.assertEqual(data['device_id']['model'], 'TestDrive_Model')
        self.assertEqual(data['device_id']['size'], TEST_TOTAL_SIZE_4GB)

    @patch('wipeit.DeviceDetector')
    def test_load_progress_verifies_device_id(self, mock_detector_class):
        """Test that load_progress verifies device identity."""
        device_id = {
            'serial': 'TEST123456',
            'model': 'TestDrive_Model',
            'size': TEST_TOTAL_SIZE_4GB
        }

        # Create progress file with device_id
        test_data = {
            'device': self.test_device,
            'written': TEST_WRITTEN_1GB,
            'total_size': TEST_TOTAL_SIZE_4GB,
            'chunk_size': TEST_CHUNK_SIZE_100MB,
            'timestamp': time.time(),
            'progress_percent': 25.0,
            'device_id': device_id
        }

        with open(self.test_progress_file, 'w') as f:
            json.dump(test_data, f)

        # Mock DeviceDetector to return matching ID
        mock_detector = MagicMock()
        mock_detector.get_unique_id.return_value = device_id
        mock_detector_class.return_value = mock_detector

        # Should load successfully
        result = wipeit.load_progress(self.test_device)
        self.assertIsNotNone(result)
        self.assertEqual(result['device_id']['serial'], 'TEST123456')

    @patch('wipeit.sys.exit')
    @patch('wipeit.DeviceDetector')
    def test_load_progress_rejects_mismatched_serial(
            self, mock_detector_class, mock_exit):
        """Test that load_progress halts on mismatched serial number."""
        saved_device_id = {
            'serial': 'ORIGINAL123',
            'model': 'TestDrive_Model',
            'size': TEST_TOTAL_SIZE_4GB
        }

        current_device_id = {
            'serial': 'DIFFERENT456',  # Different serial!
            'model': 'TestDrive_Model',
            'size': TEST_TOTAL_SIZE_4GB
        }

        # Create progress file with original device_id
        test_data = {
            'device': self.test_device,
            'written': TEST_WRITTEN_1GB,
            'total_size': TEST_TOTAL_SIZE_4GB,
            'chunk_size': TEST_CHUNK_SIZE_100MB,
            'timestamp': time.time(),
            'progress_percent': 25.0,
            'device_id': saved_device_id
        }

        with open(self.test_progress_file, 'w') as f:
            json.dump(test_data, f)

        # Mock DeviceDetector to return different serial
        mock_detector = MagicMock()
        mock_detector.get_unique_id.return_value = current_device_id
        mock_detector_class.return_value = mock_detector

        # Capture output to verify error message
        with patch('builtins.print') as mock_print:
            wipeit.load_progress(self.test_device)

        # Should call sys.exit(1) to halt execution
        mock_exit.assert_called_once_with(1)

        # Verify error message was displayed
        output = ' '.join([str(call) for call in mock_print.call_args_list])
        self.assertIn('DEVICE MISMATCH ERROR', output)
        self.assertIn('ORIGINAL123', output)
        self.assertIn('DIFFERENT456', output)
        self.assertIn('WHAT TO DO', output)

    @patch('wipeit.sys.exit')
    @patch('wipeit.DeviceDetector')
    def test_load_progress_rejects_mismatched_size(
            self, mock_detector_class, mock_exit):
        """Test that load_progress halts on mismatched device size."""
        saved_device_id = {
            'serial': 'TEST123456',
            'model': 'TestDrive_Model',
            'size': TEST_TOTAL_SIZE_4GB
        }

        current_device_id = {
            'serial': 'TEST123456',
            'model': 'TestDrive_Model',
            'size': TEST_TOTAL_SIZE_4GB * 2  # Different size!
        }

        # Create progress file
        test_data = {
            'device': self.test_device,
            'written': TEST_WRITTEN_1GB,
            'total_size': TEST_TOTAL_SIZE_4GB,
            'chunk_size': TEST_CHUNK_SIZE_100MB,
            'timestamp': time.time(),
            'progress_percent': 25.0,
            'device_id': saved_device_id
        }

        with open(self.test_progress_file, 'w') as f:
            json.dump(test_data, f)

        # Mock DeviceDetector to return different size
        mock_detector = MagicMock()
        mock_detector.get_unique_id.return_value = current_device_id
        mock_detector_class.return_value = mock_detector

        # Capture output to verify error message
        with patch('builtins.print') as mock_print:
            wipeit.load_progress(self.test_device)

        # Should call sys.exit(1) to halt execution
        mock_exit.assert_called_once_with(1)

        # Verify error message was displayed
        output = ' '.join([str(call) for call in mock_print.call_args_list])
        self.assertIn('DEVICE MISMATCH ERROR', output)
        self.assertIn('size does not match', output)
        self.assertIn('WHAT TO DO', output)


class TestResumeFileFunctions(unittest.TestCase):
    """Test resume file detection and display functions."""

    def setUp(self):
        """Set up test environment."""
        self.test_progress_file = PROGRESS_FILE_NAME

        # Clean up any existing test progress file
        if os.path.exists(self.test_progress_file):
            os.remove(self.test_progress_file)

    def tearDown(self):
        """Clean up test environment."""
        if os.path.exists(self.test_progress_file):
            os.remove(self.test_progress_file)

    def test_find_resume_file_none(self):
        """Test finding resume file when none exist."""
        result = wipeit.find_resume_file()
        self.assertIsNone(result)

    def test_find_resume_file_with_valid_file(self):
        """Test finding resume file with valid file."""
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

        result = wipeit.find_resume_file()
        self.assertIsNotNone(result)
        self.assertEqual(result['device'], '/dev/sdb')

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
        self.assertIn('Found previous wipe session', output)
        self.assertIn('/dev/sdb', output)
        self.assertIn('25.00% complete', output)


class TestUtilityFunctions(unittest.TestCase):
    """Test utility functions extracted from wipe_device."""

    def test_calculate_average_speed_normal(self):
        """Test calculate_average_speed with normal values."""
        # 100 MB in 10 seconds = 10 MB/s
        speed = wipeit.calculate_average_speed(100 * MEGABYTE, 10.0)
        self.assertAlmostEqual(speed, 10.0, places=2)

    def test_calculate_average_speed_zero_time(self):
        """Test calculate_average_speed with zero time."""
        # Should return 0.0 to avoid division by zero
        speed = wipeit.calculate_average_speed(100 * MEGABYTE, 0.0)
        self.assertEqual(speed, 0.0)

    def test_calculate_average_speed_large_values(self):
        """Test calculate_average_speed with large values."""
        # 1 GB in 100 seconds = 10 MB/s
        speed = wipeit.calculate_average_speed(GIGABYTE, 100.0)
        self.assertAlmostEqual(speed, 10.24, places=2)

    def test_create_wipe_strategy_standard(self):
        """Test create_wipe_strategy creates StandardStrategy."""
        strategy = wipeit.create_wipe_strategy(
            'standard', '/dev/sdb', 1000, 100, 0, None, lambda w, t, c: None)
        self.assertIsInstance(strategy, wipeit.StandardStrategy)

    def test_create_wipe_strategy_adaptive(self):
        """Test create_wipe_strategy creates AdaptiveStrategy."""
        pretest_results = {'recommended_algorithm': 'adaptive_chunk'}
        strategy = wipeit.create_wipe_strategy(
            'adaptive_chunk', '/dev/sdb', 1000, 100, 0,
            pretest_results, lambda w, t, c: None)
        self.assertIsInstance(strategy, wipeit.AdaptiveStrategy)

    def test_create_wipe_strategy_small_chunk(self):
        """Test create_wipe_strategy creates SmallChunkStrategy."""
        strategy = wipeit.create_wipe_strategy(
            'small_chunk', '/dev/sdb', 1000, 100, 0, None,
            lambda w, t, c: None)
        self.assertIsInstance(strategy, wipeit.SmallChunkStrategy)

    @patch('wipeit.load_progress')
    def test_handle_resume_no_progress(self, mock_load_progress):
        """Test handle_resume when no progress exists."""
        mock_load_progress.return_value = None

        with patch('sys.stdout', new_callable=StringIO):
            written, pretest = wipeit.handle_resume('/dev/sdb')

        self.assertEqual(written, 0)
        self.assertIsNone(pretest)

    @patch('wipeit.load_progress')
    def test_handle_resume_with_progress(self, mock_load_progress):
        """Test handle_resume with existing progress."""
        progress = {
            'written': 1000000,
            'progress_percent': 50.0,
            'timestamp': time.time(),
            'pretest_results': {'recommended_algorithm': 'adaptive'}
        }
        mock_load_progress.return_value = progress

        with patch('sys.stdout', new_callable=StringIO):
            written, pretest = wipeit.handle_resume('/dev/sdb')

        self.assertEqual(written, 1000000)
        self.assertEqual(pretest, {'recommended_algorithm': 'adaptive'})

    @patch('wipeit.load_progress')
    def test_handle_resume_with_progress_no_pretest(self, mock_load_progress):
        """Test handle_resume with progress but no pretest results."""
        progress = {
            'written': 500000,
            'progress_percent': 25.0,
            'timestamp': time.time()
        }
        mock_load_progress.return_value = progress

        with patch('sys.stdout', new_callable=StringIO):
            written, pretest = wipeit.handle_resume('/dev/sdb')

        self.assertEqual(written, 500000)
        self.assertIsNone(pretest)

    def test_handle_hdd_pretest_uses_existing(self):
        """Test handle_hdd_pretest uses existing pretest results."""
        existing = {'recommended_algorithm': 'adaptive_chunk'}

        with patch('sys.stdout', new_callable=StringIO):
            result = wipeit.handle_hdd_pretest(
                '/dev/sdb', 100, existing, 0, 1000, {})

        self.assertEqual(result, existing)

    @patch('wipeit.save_progress')
    @patch('wipeit.DiskPretest')
    def test_handle_hdd_pretest_runs_new(self, mock_pretest_class,
                                         mock_save_progress):
        """Test handle_hdd_pretest runs new pretest when no existing
        results."""
        # Mock DiskPretest instance and its run_pretest method
        mock_pretest_instance = MagicMock()
        mock_results = MagicMock()
        mock_results.to_dict.return_value = {
            'recommended_algorithm': 'small_chunk'
        }
        mock_pretest_instance.run_pretest.return_value = mock_results
        mock_pretest_class.return_value = mock_pretest_instance

        with patch('sys.stdout', new_callable=StringIO):
            result = wipeit.handle_hdd_pretest(
                '/dev/sdb', 100, None, 0, 1000, {'serial': '123'})

        # Verify DiskPretest was instantiated with correct args
        mock_pretest_class.assert_called_once_with('/dev/sdb', 100)
        # Verify run_pretest was called
        mock_pretest_instance.run_pretest.assert_called_once()
        # Verify save_progress was called
        mock_save_progress.assert_called_once()
        # Verify result matches
        self.assertEqual(result, {'recommended_algorithm': 'small_chunk'})

    @patch('wipeit.save_progress')
    @patch('wipeit.DiskPretest')
    def test_handle_hdd_pretest_failed(self, mock_pretest_class,
                                       mock_save_progress):
        """Test handle_hdd_pretest when pretest fails."""
        # Mock DiskPretest instance that returns None (failure)
        mock_pretest_instance = MagicMock()
        mock_pretest_instance.run_pretest.return_value = None
        mock_pretest_class.return_value = mock_pretest_instance

        with patch('sys.stdout', new_callable=StringIO):
            result = wipeit.handle_hdd_pretest(
                '/dev/sdb', 100, None, 0, 1000, {'serial': '123'})

        # Verify pretest was attempted
        mock_pretest_instance.run_pretest.assert_called_once()
        # Verify save_progress was NOT called
        mock_save_progress.assert_not_called()
        # Verify result is None
        self.assertIsNone(result)

    def test_setup_argument_parser_returns_parser(self):
        """Test setup_argument_parser returns ArgumentParser instance."""
        parser = wipeit.setup_argument_parser()
        self.assertIsInstance(parser, argparse.ArgumentParser)

    def test_setup_argument_parser_has_device_arg(self):
        """Test setup_argument_parser configures device argument."""
        parser = wipeit.setup_argument_parser()
        args = parser.parse_args(['/dev/sdb'])
        self.assertEqual(args.device, '/dev/sdb')

    def test_setup_argument_parser_has_buffer_size_arg(self):
        """Test setup_argument_parser configures buffer-size argument."""
        parser = wipeit.setup_argument_parser()
        args = parser.parse_args(['-b', '1G', '/dev/sdb'])
        self.assertEqual(args.buffer_size, '1G')

    def test_setup_argument_parser_has_resume_arg(self):
        """Test setup_argument_parser configures resume argument."""
        parser = wipeit.setup_argument_parser()
        args = parser.parse_args(['--resume', '/dev/sdb'])
        self.assertTrue(args.resume)

    def test_setup_argument_parser_has_skip_pretest_arg(self):
        """Test setup_argument_parser configures skip-pretest argument."""
        parser = wipeit.setup_argument_parser()
        args = parser.parse_args(['--skip-pretest', '/dev/sdb'])
        self.assertTrue(args.skip_pretest)

    def test_setup_argument_parser_has_list_arg(self):
        """Test setup_argument_parser configures list argument."""
        parser = wipeit.setup_argument_parser()
        args = parser.parse_args(['--list'])
        self.assertTrue(args.list)


class TestDeviceInfoFunctions(unittest.TestCase):
    """Test device information functions."""

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
        self.assertIn('wipeit 1.4.2', output)

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
        self.test_progress_file = PROGRESS_FILE_NAME
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
    @patch('wipeit.DeviceDetector.get_block_device_size')
    @patch('wipeit.DeviceDetector')
    @patch('wipeit.load_progress', return_value=None)
    @patch('wipeit.clear_progress')
    @patch('sys.exit')
    def test_main_shows_resume_prompt_when_progress_exists(
            self, mock_exit, mock_clear_progress, mock_load_progress,
            mock_detector_class, mock_size, mock_input, mock_path_exists,
            mock_geteuid):
        """Test that main() displays resume info when progress file exists.

        This is a critical user-facing feature: when starting wipeit with
        a device argument, if a progress file exists, the user should see:
        1. RESUME OPTIONS section with details
        2. "Use --resume flag to continue" message
        """
        # Mock device size
        mock_size.return_value = 1000 * 1024 * 1024 * 1024
        
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
            'Found previous wipe session', output,
            "User should see message about previous session")
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
    @patch('wipeit.DeviceDetector.get_block_device_size')
    @patch('wipeit.DeviceDetector')
    @patch('wipeit.load_progress', return_value=None)
    @patch('wipeit.clear_progress')
    @patch('sys.exit')
    def test_main_no_resume_prompt_when_no_progress(
            self, mock_exit, mock_clear_progress, mock_load_progress,
            mock_detector_class, mock_size, mock_input, mock_path_exists,
            mock_geteuid):
        """Test main() doesn't show resume info when no progress exists."""
        # Mock device size
        mock_size.return_value = 1000 * 1024 * 1024 * 1024
        
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

    @patch('sys.argv', ['wipeit.py', '--resume', '/dev/sdb'])
    @patch('os.geteuid', return_value=0)
    @patch('sys.exit')
    @patch('builtins.input', return_value='n')  # Mock user saying 'no'
    @patch('wipeit.DeviceDetector.get_block_device_size')
    @patch('wipeit.DeviceDetector')
    def test_resume_with_mismatched_device_halts(
            self, mock_detector_class, mock_size, mock_input, mock_exit,
            mock_geteuid):
        """Test that resume with mismatched device halts with clear error."""
        # Mock device size
        mock_size.return_value = 1000 * 1024 * 1024 * 1024
        
        # Create progress file with device_id
        saved_device_id = {
            'serial': 'ORIGINAL_SERIAL_123',
            'model': 'Original_SSD_Model',
            'size': 1000 * 1024 * 1024 * 1024  # 1TB
        }

        progress_data = {
            'device': '/dev/sdb',
            'written': 500 * 1024 * 1024 * 1024,  # 500GB
            'total_size': 1000 * 1024 * 1024 * 1024,  # 1TB
            'chunk_size': 100 * 1024 * 1024,
            'timestamp': time.time(),
            'progress_percent': 50.0,
            'device_id': saved_device_id
        }

        with open(self.test_progress_file, 'w') as f:
            json.dump(progress_data, f)

        # Mock DeviceDetector to return DIFFERENT device
        mock_detector = MagicMock()
        mock_detector.get_unique_id.return_value = {
            'serial': 'DIFFERENT_SERIAL_456',  # Different!
            'model': 'Different_SSD_Model',
            'size': 1000 * 1024 * 1024 * 1024
        }
        mock_detector.is_mounted.return_value = (False, [])  # Not mounted
        mock_detector_class.return_value = mock_detector

        # Capture output
        from io import StringIO
        with patch('sys.stdout', new_callable=StringIO) as mock_stdout:
            wipeit.main()

        output = mock_stdout.getvalue()

        # CRITICAL: Program must halt with sys.exit(1)
        mock_exit.assert_called_with(1)

        # Verify error message is shown
        self.assertIn('DEVICE MISMATCH ERROR', output,
                      "Must show device mismatch error")
        self.assertIn('ORIGINAL_SERIAL_123', output,
                      "Must show expected serial")
        self.assertIn('DIFFERENT_SERIAL_456', output,
                      "Must show current serial")
        self.assertIn('WHAT TO DO', output,
                      "Must provide instructions to user")
        self.assertIn(f'rm {PROGRESS_FILE_NAME}', output,
                      "Must tell user how to clear progress")

    @patch('wipeit.DeviceDetector.get_block_device_size')
    @patch('wipeit.DeviceDetector')
    @patch('wipeit.StandardStrategy')
    @patch('sys.exit')
    def test_keyboard_interrupt_saves_actual_progress(
            self, mock_exit, mock_strategy_class, mock_detector_class,
            mock_get_size):
        """Test that KeyboardInterrupt saves actual progress from strategy."""
        # Setup mocks
        mock_get_size.return_value = TEST_TOTAL_SIZE_4GB

        # Mock detector
        mock_detector = MagicMock()
        mock_detector.detect_type.return_value = ('SSD', 'HIGH', ['Test'])
        mock_detector.get_unique_id.return_value = {
            'serial': 'TEST123',
            'model': 'TestModel',
            'size': TEST_TOTAL_SIZE_4GB
        }
        mock_detector_class.return_value = mock_detector

        # Mock strategy that has written 1GB when interrupted
        mock_strategy = MagicMock()
        mock_strategy.written = TEST_WRITTEN_1GB  # 1GB actually written!

        # Make strategy.wipe() raise KeyboardInterrupt
        mock_strategy.wipe.side_effect = KeyboardInterrupt()
        mock_strategy_class.return_value = mock_strategy

        # Try to wipe (will be interrupted)
        try:
            wipeit.wipe_device(
                '/dev/sdb', chunk_size=TEST_CHUNK_SIZE_100MB)
        except SystemExit:
            pass  # Expected due to mocked sys.exit

        # Verify sys.exit(1) was called
        mock_exit.assert_called_with(1)

        # Load the saved progress
        with open(self.test_progress_file, 'r') as f:
            data = json.load(f)

        # CRITICAL: Progress should be 1GB (strategy.written), NOT 0!
        self.assertEqual(
            data['written'], TEST_WRITTEN_1GB,
            "Bug: KeyboardInterrupt should save strategy.written (1GB), "
            f"not 0! Got: {data['written']}")
        self.assertEqual(
            data['progress_percent'], 25.0,
            f"Bug: Should be 25% progress, got: {data['progress_percent']}%")

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
        wipeit.clear_progress()

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

    @patch('wipeit.DeviceDetector.get_block_device_size')
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
                pretest = DiskPretest('/dev/sdb', TEST_CHUNK_SIZE_100MB)
                results = pretest.run_pretest()
                result = results.to_dict() if results else None

        # Verify pretest was performed
        self.assertIsNotNone(result)
        self.assertIn('recommended_algorithm', result)
        self.assertIn('reason', result)

        # Check output contains expected messages
        output = mock_stdout.getvalue()
        self.assertIn('Performing HDD pretest', output)
        self.assertIn('Testing beginning of disk', output)
        self.assertIn('Testing middle of disk', output)
        self.assertIn('Testing end of disk', output)
        self.assertIn('PRETEST ANALYSIS', output)

    @patch('wipeit.DeviceDetector.get_block_device_size')
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
            pretest = DiskPretest('/dev/sdb', TEST_CHUNK_SIZE_100MB)
            results = pretest.run_pretest()
            result = results.to_dict() if results else None

        # Verify adaptive algorithm is recommended
        self.assertEqual(result['recommended_algorithm'],
                         'adaptive_chunk')

    @patch('wipeit.DeviceDetector.get_block_device_size')
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
            pretest = DiskPretest('/dev/sdb', TEST_CHUNK_SIZE_100MB)
            results = pretest.run_pretest()
            result = results.to_dict() if results else None

        # Verify small chunk algorithm is recommended
        self.assertEqual(result['recommended_algorithm'],
                         'small_chunk')


class TestWipeDeviceIntegration(unittest.TestCase):
    """Test wipe_device function with pretest integration."""

    @patch('wipeit.DeviceDetector.get_block_device_size')
    @patch('wipeit.DeviceDetector')
    @patch('builtins.open', new_callable=mock_open)
    @patch('time.time')
    def test_wipe_device_with_adaptive_chunk(self, mock_time, mock_file,
                                             mock_detector_class, mock_size):
        """Test wipe_device with adaptive chunk - CRITICAL BUG TEST."""
        mock_size.return_value = TEST_DEVICE_SIZE_100MB

        # Mock DeviceDetector
        mock_detector = MagicMock()
        mock_detector.detect_type.return_value = ('HDD', 'HIGH', ['Test'])
        mock_detector.get_unique_id.return_value = {
            'serial': 'TEST123',
            'model': 'TestModel',
            'size': TEST_DEVICE_SIZE_100MB
        }
        mock_detector_class.return_value = mock_detector

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
            mock_results = MagicMock()
            mock_results.to_dict.return_value = mock_pretest_results
            with patch('wipeit.DiskPretest') as mock_pretest_class:
                mock_pretest_class.return_value.run_pretest.return_value = \
                    mock_results
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

    @patch('wipeit.DeviceDetector.get_block_device_size')
    @patch('wipeit.DeviceDetector')
    @patch('builtins.open', new_callable=mock_open)
    @patch('time.time')
    def test_adaptive_chunk_sizing_calculations(
            self, mock_time, mock_file, mock_detector_class, mock_size):
        """Test that adaptive chunk sizing produces integers."""
        mock_size.return_value = 100 * 1024 * 1024

        # Mock DeviceDetector
        mock_detector = MagicMock()
        mock_detector.detect_type.return_value = ('SSD', 'HIGH', ['Test'])
        mock_detector.get_unique_id.return_value = {
            'serial': 'TEST123', 'model': 'TestModel',
            'size': 100 * 1024 * 1024
        }
        mock_detector_class.return_value = mock_detector

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
            mock_results = MagicMock()
            mock_results.to_dict.return_value = mock_pretest_results
            with patch('wipeit.DiskPretest') as mock_pretest_class:
                mock_pretest_class.return_value.run_pretest.return_value = \
                    mock_results
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
        TestUtilityFunctions,
        TestDeviceInfoFunctions,
        TestMainFunction,
        TestIntegration,
        TestHDDPretest,
        TestWipeDeviceIntegration,
    ]

    for test_class in test_classes:
        tests = unittest.TestLoader().loadTestsFromTestCase(test_class)
        test_suite.addTests(tests)

    # Run the tests
    runner = unittest.TextTestRunner(verbosity=2)
    result = runner.run(test_suite)

    # Exit with appropriate code
    sys.exit(0 if result.wasSuccessful() else 1)
