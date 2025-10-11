#!/usr/bin/env python3
"""
Test cases for DeviceDetector class.

This module contains unit tests for the DeviceDetector class,
which handles device detection and information gathering.
"""

import os
import subprocess
import sys
import unittest
from unittest.mock import patch

# Add src directory to path for imports
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import device_detector  # noqa: E402
from global_constants import TEST_DEVICE_SIZE_1TB  # noqa: E402


class TestDeviceDetector(unittest.TestCase):
    """Test DeviceDetector class functionality."""

    def test_init(self):
        """Test DeviceDetector initialization."""
        detector = device_detector.DeviceDetector('/dev/sdb')
        self.assertEqual(detector.device_path, '/dev/sdb')
        self.assertEqual(detector.device_name, 'sdb')
        self.assertEqual(detector._cached_info, {})

    @patch('device_detector.subprocess.check_output')
    def test_get_size(self, mock_check_output):
        """Test get_size method."""
        mock_check_output.return_value = b'1099511627776\n'  # 1TB (1024^4)
        detector = device_detector.DeviceDetector('/dev/sdb')
        size = detector.get_size()
        self.assertEqual(size, TEST_DEVICE_SIZE_1TB)
        mock_check_output.assert_called_once_with(['blockdev', '--getsize64',
                                                   '/dev/sdb'])

    @patch('device_detector.subprocess.check_output')
    def test_get_size_error(self, mock_check_output):
        """Test get_size method with error."""
        mock_check_output.side_effect = subprocess.CalledProcessError(1, 'cmd')
        detector = device_detector.DeviceDetector('/dev/sdb')
        with self.assertRaises(OSError):
            detector.get_size()

    @patch('device_detector.subprocess.check_output')
    def test_get_device_properties(self, mock_check_output):
        """Test get_device_properties method."""
        mock_output = ('ID_MODEL=Samsung_SSD_860\n'
                       'ID_SERIAL_SHORT=1234567890\n'
                       'ID_BUS=ata\n')
        mock_check_output.return_value = mock_output.encode()
        detector = device_detector.DeviceDetector('/dev/sdb')
        props = detector.get_device_properties()
        expected = {
            'ID_MODEL': 'Samsung_SSD_860',
            'ID_SERIAL_SHORT': '1234567890',
            'ID_BUS': 'ata'
        }
        self.assertEqual(props, expected)

    @patch('device_detector.subprocess.check_output')
    def test_get_device_properties_error(self, mock_check_output):
        """Test get_device_properties method with error."""
        mock_check_output.side_effect = subprocess.CalledProcessError(1, 'cmd')
        detector = device_detector.DeviceDetector('/dev/sdb')
        props = detector.get_device_properties()
        self.assertEqual(props, {})

    @patch('device_detector.os.path.exists')
    @patch('builtins.open')
    def test_check_rotational_ssd(self, mock_open, mock_exists):
        """Test _check_rotational for SSD."""
        mock_exists.return_value = True
        mock_open.return_value.__enter__.return_value.read.return_value = '0'
        detector = device_detector.DeviceDetector('/dev/sdb')
        result = detector._check_rotational()
        self.assertFalse(result)

    @patch('device_detector.os.path.exists')
    @patch('builtins.open')
    def test_check_rotational_hdd(self, mock_open, mock_exists):
        """Test _check_rotational for HDD."""
        mock_exists.return_value = True
        mock_open.return_value.__enter__.return_value.read.return_value = '1'
        detector = device_detector.DeviceDetector('/dev/sdb')
        result = detector._check_rotational()
        self.assertTrue(result)

    @patch('device_detector.os.path.exists')
    def test_check_rotational_not_found(self, mock_exists):
        """Test _check_rotational when file doesn't exist."""
        mock_exists.return_value = False
        detector = device_detector.DeviceDetector('/dev/sdb')
        result = detector._check_rotational()
        self.assertIsNone(result)

    def test_check_nvme_interface_true(self):
        """Test _check_nvme_interface for NVMe device."""
        detector = device_detector.DeviceDetector('/dev/nvme0n1')
        result = detector._check_nvme_interface()
        self.assertTrue(result)

    def test_check_nvme_interface_false(self):
        """Test _check_nvme_interface for non-NVMe device."""
        detector = device_detector.DeviceDetector('/dev/sdb')
        result = detector._check_nvme_interface()
        self.assertFalse(result)

    def test_check_mmc_interface_true(self):
        """Test _check_mmc_interface for MMC device."""
        detector = device_detector.DeviceDetector('/dev/mmcblk0')
        result = detector._check_mmc_interface()
        self.assertTrue(result)

    def test_check_mmc_interface_false(self):
        """Test _check_mmc_interface for non-MMC device."""
        detector = device_detector.DeviceDetector('/dev/sdb')
        result = detector._check_mmc_interface()
        self.assertFalse(result)

    def test_analyze_rpm_indicators_zero_rpm(self):
        """Test _analyze_rpm_indicators with zero RPM."""
        udev_props = {'ID_ATA_ROTATION_RATE_RPM': '0'}
        detector = device_detector.DeviceDetector('/dev/sdb')
        ssd_indicators, nvme_indicators = detector._analyze_rpm_indicators(
            udev_props)
        self.assertIn('zero_rpm', ssd_indicators)
        self.assertEqual(nvme_indicators, [])

    def test_analyze_rpm_indicators_with_rpm(self):
        """Test _analyze_rpm_indicators with RPM value."""
        udev_props = {'ID_ATA_ROTATION_RATE_RPM': '7200'}
        detector = device_detector.DeviceDetector('/dev/sdb')
        ssd_indicators, nvme_indicators = detector._analyze_rpm_indicators(
            udev_props)
        self.assertIn('rpm_7200', ssd_indicators)
        self.assertEqual(nvme_indicators, [])

    def test_analyze_rpm_indicators_nvme_bus(self):
        """Test _analyze_rpm_indicators with NVMe bus."""
        udev_props = {'ID_BUS': 'nvme'}
        detector = device_detector.DeviceDetector('/dev/nvme0n1')
        ssd_indicators, nvme_indicators = detector._analyze_rpm_indicators(
            udev_props)
        self.assertEqual(ssd_indicators, [])
        self.assertIn('nvme_bus', nvme_indicators)

    def test_detect_from_model_name_ssd(self):
        """Test _detect_from_model_name for SSD."""
        udev_props = {'ID_MODEL': 'Samsung SSD 860 EVO'}
        detector = device_detector.DeviceDetector('/dev/sdb')
        disk_type, confidence, details = detector._detect_from_model_name(
            udev_props)
        self.assertEqual(disk_type, 'SSD')
        self.assertEqual(confidence, 'MEDIUM')
        self.assertIn('SSD mentioned in model name', details)

    def test_detect_from_model_name_hdd(self):
        """Test _detect_from_model_name for HDD."""
        udev_props = {'ID_MODEL': 'WDC HDD 1TB'}
        detector = device_detector.DeviceDetector('/dev/sdb')
        disk_type, confidence, details = detector._detect_from_model_name(
            udev_props)
        self.assertEqual(disk_type, 'HDD')
        self.assertEqual(confidence, 'MEDIUM')
        self.assertIn('HDD mentioned in model name', details)

    def test_detect_from_model_name_unknown(self):
        """Test _detect_from_model_name for unknown model."""
        udev_props = {'ID_MODEL': 'Unknown Device'}
        detector = device_detector.DeviceDetector('/dev/sdb')
        disk_type, confidence, details = detector._detect_from_model_name(
            udev_props)
        self.assertIsNone(disk_type)
        self.assertIsNone(confidence)
        self.assertIsNone(details)

    def test_determine_type_nvme(self):
        """Test _determine_type for NVMe device."""
        detector = device_detector.DeviceDetector('/dev/nvme0n1')
        result = detector._determine_type(False, True, False, {}, ([], []))
        self.assertEqual(result, ('NVMe SSD', 'HIGH',
                                  ['NVMe interface detected']))

    def test_determine_type_mmc(self):
        """Test _determine_type for MMC device."""
        detector = device_detector.DeviceDetector('/dev/mmcblk0')
        result = detector._determine_type(False, False, True, {}, ([], []))
        self.assertEqual(result, ('eMMC/MMC', 'HIGH',
                                  ['MMC interface detected']))

    def test_determine_type_ssd_non_rotational(self):
        """Test _determine_type for SSD (non-rotational)."""
        detector = device_detector.DeviceDetector('/dev/sdb')
        result = detector._determine_type(False, False, False, {}, ([], []))
        self.assertEqual(result, ('SSD', 'HIGH', ['Non-rotational device']))

    def test_determine_type_hdd_rotational(self):
        """Test _determine_type for HDD (rotational)."""
        detector = device_detector.DeviceDetector('/dev/sdb')
        result = detector._determine_type(True, False, False, {}, ([], []))
        self.assertEqual(result, ('HDD', 'HIGH', ['Rotational device']))

    def test_determine_type_ssd_zero_rpm(self):
        """Test _determine_type for SSD (zero RPM)."""
        detector = device_detector.DeviceDetector('/dev/sdb')
        result = detector._determine_type(None, False, False, {},
                                          (['zero_rpm'], []))
        self.assertEqual(result, ('SSD', 'MEDIUM',
                                  ['Zero RPM indicates SSD']))

    def test_determine_type_hdd_with_rpm(self):
        """Test _determine_type for HDD (with RPM)."""
        detector = device_detector.DeviceDetector('/dev/sdb')
        result = detector._determine_type(None, False, False, {},
                                          (['rpm_7200'], []))
        self.assertEqual(result, ('HDD', 'MEDIUM',
                                  ['Rotational speed detected: rpm_7200']))

    @patch('device_detector.DeviceDetector._check_rotational')
    @patch('device_detector.DeviceDetector._check_nvme_interface')
    @patch('device_detector.DeviceDetector._check_mmc_interface')
    @patch('device_detector.DeviceDetector.get_device_properties')
    @patch('device_detector.DeviceDetector._analyze_rpm_indicators')
    @patch('device_detector.DeviceDetector._determine_type')
    def test_detect_type(self, mock_determine, mock_analyze, mock_props,
                         mock_mmc, mock_nvme, mock_rotational):
        """Test detect_type method."""
        mock_rotational.return_value = False
        mock_nvme.return_value = False
        mock_mmc.return_value = False
        mock_props.return_value = {}
        mock_analyze.return_value = ([], [])
        mock_determine.return_value = ('SSD', 'HIGH', ['Non-rotational'])

        detector = device_detector.DeviceDetector('/dev/sdb')
        result = detector.detect_type()

        self.assertEqual(result, ('SSD', 'HIGH', ['Non-rotational']))
        mock_rotational.assert_called_once()
        mock_nvme.assert_called_once()
        mock_mmc.assert_called_once()
        mock_props.assert_called_once()
        mock_analyze.assert_called_once_with({})
        mock_determine.assert_called_once_with(False, False, False, {},
                                               ([], []))

    @patch('device_detector.DeviceDetector._check_rotational')
    def test_detect_type_error(self, mock_rotational):
        """Test detect_type method with error."""
        mock_rotational.side_effect = Exception('Test error')
        detector = device_detector.DeviceDetector('/dev/sdb')
        result = detector.detect_type()
        self.assertEqual(result, ('UNKNOWN', 'LOW',
                                  ['Detection failed: Test error']))

    @patch('device_detector.subprocess.check_output')
    def test_is_mounted_not_mounted(self, mock_check_output):
        """Test is_mounted when device is not mounted."""
        mock_check_output.side_effect = [
            b'/dev/sda1 on / type ext4 (rw,relatime)\n',
            b'sdb\nsdb1\n'
        ]
        detector = device_detector.DeviceDetector('/dev/sdb')
        is_mounted, mount_info = detector.is_mounted()
        self.assertFalse(is_mounted)
        self.assertEqual(mount_info, [])

    @patch('device_detector.subprocess.check_output')
    def test_is_mounted_device_mounted(self, mock_check_output):
        """Test is_mounted when device itself is mounted."""
        mock_check_output.side_effect = [
            b'/dev/sdb on /mnt/usb type ext4 (rw,relatime)\n',
            b'sdb\nsdb1\n'
        ]
        detector = device_detector.DeviceDetector('/dev/sdb')
        is_mounted, mount_info = detector.is_mounted()
        self.assertTrue(is_mounted)
        self.assertEqual(mount_info, [])

    @patch('device_detector.subprocess.check_output')
    def test_is_mounted_partitions_mounted(self, mock_check_output):
        """Test is_mounted when partitions are mounted."""
        mock_check_output.side_effect = [
            b'/dev/sda1 on / type ext4 (rw,relatime)\n',
            b'sdb\nsdb1 /mnt/usb\nsdb2 /media/data\n'
        ]
        detector = device_detector.DeviceDetector('/dev/sdb')
        is_mounted, mount_info = detector.is_mounted()
        self.assertTrue(is_mounted)
        self.assertEqual(len(mount_info), 2)
        self.assertIn('/dev/sdb1 -> /mnt/usb', mount_info)
        self.assertIn('/dev/sdb2 -> /media/data', mount_info)

    @patch('device_detector.subprocess.check_output')
    def test_is_mounted_error(self, mock_check_output):
        """Test is_mounted with error."""
        mock_check_output.side_effect = subprocess.CalledProcessError(
            1, 'mount')
        detector = device_detector.DeviceDetector('/dev/sdb')
        is_mounted, mount_info = detector.is_mounted()
        self.assertFalse(is_mounted)
        self.assertEqual(mount_info, [])

    @patch('device_detector.subprocess.check_output')
    def test_get_partitions(self, mock_check_output):
        """Test get_partitions method."""
        mock_output = ('NAME   SIZE   TYPE MOUNTPOINTS\n'
                       'sdb    128G   disk\n'
                       '├─sdb1 64G    part\n'
                       '└─sdb2 64G    part\n')
        mock_check_output.return_value = mock_output.encode()
        detector = device_detector.DeviceDetector('/dev/sdb')
        result = detector.get_partitions()
        self.assertEqual(result, mock_output)

    @patch('device_detector.subprocess.check_output')
    def test_get_partitions_error(self, mock_check_output):
        """Test get_partitions method with error."""
        mock_check_output.side_effect = subprocess.CalledProcessError(
            1, 'lsblk')
        detector = device_detector.DeviceDetector('/dev/sdb')
        result = detector.get_partitions()
        self.assertIn('Error getting partition info', result)

    @patch('device_detector.DeviceDetector.get_size')
    @patch('device_detector.DeviceDetector.get_device_properties')
    @patch('device_detector.DeviceDetector.detect_type')
    @patch('device_detector.DeviceDetector.get_partitions')
    @patch('device_detector.DeviceDetector.is_mounted')
    @patch('device_detector.DeviceDetector._display_header')
    @patch('device_detector.DeviceDetector._display_basic_info')
    @patch('device_detector.DeviceDetector._display_type_info')
    @patch('device_detector.DeviceDetector._display_partition_info')
    @patch('device_detector.DeviceDetector._display_mount_status')
    def test_display_info(self, mock_mount, mock_part, mock_type, mock_basic,
                          mock_header, mock_mounted, mock_partitions,
                          mock_detect, mock_props, mock_size):
        """Test display_info method."""
        mock_size.return_value = TEST_DEVICE_SIZE_1TB  # 1TB
        mock_props.return_value = {'ID_MODEL': 'Test SSD'}
        mock_detect.return_value = ('SSD', 'HIGH', ['Non-rotational'])
        mock_partitions.return_value = 'Test partitions'
        mock_mounted.return_value = (False, [])

        detector = device_detector.DeviceDetector('/dev/sdb')
        detector.display_info()

        mock_size.assert_called_once()
        mock_props.assert_called_once()
        mock_detect.assert_called_once()
        mock_partitions.assert_called_once()
        mock_mounted.assert_called_once()
        mock_header.assert_called_once()
        mock_basic.assert_called_once()
        mock_type.assert_called_once()
        mock_part.assert_called_once()
        mock_mount.assert_called_once()

    @patch('device_detector.DeviceDetector.get_size')
    def test_display_info_error(self, mock_size):
        """Test display_info method with error."""
        mock_size.side_effect = Exception('Test error')
        detector = device_detector.DeviceDetector('/dev/sdb')
        with patch('builtins.print') as mock_print:
            detector.display_info()
            mock_print.assert_called_with('Error getting info: Test error')

    def test_display_header(self):
        """Test _display_header method."""
        detector = device_detector.DeviceDetector('/dev/sdb')
        with patch('builtins.print') as mock_print:
            detector._display_header()
            calls = mock_print.call_args_list
            self.assertEqual(len(calls), 3)
            self.assertIn('=' * 70, str(calls[0]))
            self.assertIn('DEVICE INFORMATION', str(calls[1]))
            self.assertIn('=' * 70, str(calls[2]))

    def test_display_basic_info(self):
        """Test _display_basic_info method."""
        detector = device_detector.DeviceDetector('/dev/sdb')
        size = TEST_DEVICE_SIZE_1TB  # 1TB
        properties = {'ID_MODEL': 'Test SSD', 'ID_SERIAL_SHORT': '12345'}

        with patch('builtins.print') as mock_print:
            detector._display_basic_info(size, properties)
            calls = mock_print.call_args_list
            self.assertEqual(len(calls), 4)
            self.assertIn('/dev/sdb', str(calls[0]))
            self.assertIn('1024.00 GB', str(calls[1]))
            self.assertIn('Test SSD', str(calls[2]))
            self.assertIn('12345', str(calls[3]))

    def test_display_type_info(self):
        """Test _display_type_info method."""
        detector = device_detector.DeviceDetector('/dev/sdb')
        disk_type = 'SSD'
        confidence = 'HIGH'
        details = ['Non-rotational device']

        with patch('builtins.print') as mock_print:
            detector._display_type_info(disk_type, confidence, details)
            calls = mock_print.call_args_list
            self.assertEqual(len(calls), 2)
            self.assertIn('SSD (confidence: HIGH)', str(calls[0]))
            self.assertIn('Non-rotational device', str(calls[1]))

    def test_display_partition_info(self):
        """Test _display_partition_info method."""
        detector = device_detector.DeviceDetector('/dev/sdb')
        partitions = 'Test partition info'

        with patch('builtins.print') as mock_print:
            detector._display_partition_info(partitions)
            calls = mock_print.call_args_list
            self.assertEqual(len(calls), 2)
            self.assertIn('📁 Device and partitions:', str(calls[0]))
            self.assertIn('Test partition info', str(calls[1]))

    def test_display_mount_status_not_mounted(self):
        """Test _display_mount_status when not mounted."""
        detector = device_detector.DeviceDetector('/dev/sdb')
        is_mounted = False
        mount_info = []

        with patch('builtins.print') as mock_print:
            detector._display_mount_status(is_mounted, mount_info)
            mock_print.assert_called_once()
            self.assertIn('is not mounted - safe to proceed',
                          str(mock_print.call_args))

    def test_display_mount_status_mounted(self):
        """Test _display_mount_status when mounted."""
        detector = device_detector.DeviceDetector('/dev/sdb')
        is_mounted = True
        mount_info = ['/dev/sdb1 -> /mnt/usb']

        with patch('builtins.print') as mock_print:
            detector._display_mount_status(is_mounted, mount_info)
            calls = mock_print.call_args_list
            self.assertEqual(len(calls), 3)
            self.assertIn('WARNING', str(calls[0]))
            self.assertIn('📌 Mounted partitions:', str(calls[1]))
            self.assertIn('/dev/sdb1 -> /mnt/usb', str(calls[2]))


if __name__ == '__main__':
    unittest.main()
