#!/usr/bin/env python3
"""
DeviceDetector class for wipeit.

This module provides the DeviceDetector class which encapsulates all device
detection and information gathering functionality.
"""

import fcntl
import os
import struct
import subprocess

from global_constants import BLKGETSIZE64, GIGABYTE


class DeviceDetector:
    """
    Detects and provides information about block devices.

    Handles device size, type detection (HDD/SSD/NVMe), mount status,
    partition information, and device properties.
    """

    def __init__(self, device_path):
        """
        Initialize device detector.

        Args:
            device_path: Path to block device (e.g., '/dev/sdb')
        """
        self.device_path = device_path
        self.device_name = os.path.basename(device_path)
        self._cached_info = {}

    def get_size(self):
        """
        Get device size in bytes using BLKGETSIZE64 ioctl.

        Returns:
            int: Device size in bytes

        Raises:
            FileNotFoundError: If device path does not exist
            PermissionError: If insufficient permissions
            OSError: If ioctl call fails
        """
        return DeviceDetector.get_block_device_size(self.device_path)

    @staticmethod
    def get_block_device_size(device: str) -> int:
        """
        Get the size of a block device in bytes using the BLKGETSIZE64 ioctl.

        This function directly queries the Linux kernel for the device size
        using the BLKGETSIZE64 ioctl command, which returns the device size
        as a 64-bit unsigned integer. This is more reliable than parsing
        /proc or /sys files.

        Args:
            device (str): Path to the block device
                          (e.g., '/dev/sda', '/dev/nvme0n1')

        Returns:
            int: Size of the device in bytes

        Raises:
            FileNotFoundError: If the device path does not exist
            PermissionError: If insufficient permissions to access the device
            OSError: If the ioctl call fails (e.g., not a block device)
        """
        with open(device, 'rb') as fd:
            buf = bytearray(8)
            fcntl.ioctl(fd.fileno(), BLKGETSIZE64, buf)
            return struct.unpack('Q', buf)[0]

    def get_device_properties(self):
        """
        Get device properties from udevadm.

        Returns:
            dict: Device properties (model, serial, etc.)
        """
        try:
            cmd = ['udevadm', 'info', '--query=property', '--name',
                   self.device_path]
            model = subprocess.check_output(cmd).decode()
            lines = model.splitlines()
            info = {line.split('=')[0]: line.split('=')[1]
                    for line in lines if '=' in line}
            return info
        except Exception:
            return {}

    def get_unique_id(self):
        """
        Get unique identifier for the device.

        Returns a dictionary with device identifiers to verify the same
        physical drive is being used when resuming operations.

        Returns:
            dict: Dictionary with 'serial', 'model', 'size' keys
                 (values may be None if not available)
                 - serial: Most unique identifier (e.g., 'S3Z5NB0K123456A')
                 - model: Drive model name (e.g., 'Samsung_SSD_860_EVO')
                 - size: Device size in bytes
        """
        props = self.get_device_properties()
        return {
            'serial': props.get('ID_SERIAL_SHORT'),
            'model': props.get('ID_MODEL'),
            'size': self.get_size() if self.device_path else None
        }

    def detect_type(self):
        """
        Detect storage device type (HDD/SSD/NVMe).

        Returns:
            tuple: (disk_type, confidence_level, detection_details)
                - disk_type: str like "HDD", "SSD", "NVMe SSD"
                - confidence_level: str like "HIGH", "MEDIUM", "LOW"
                - detection_details: list of detection method strings
        """
        try:
            is_rotational = self._check_rotational()
            is_nvme = self._check_nvme_interface()
            is_mmc = self._check_mmc_interface()
            udev_props = self.get_device_properties()
            rpm_indicators = self._analyze_rpm_indicators(udev_props)

            return self._determine_type(is_rotational, is_nvme, is_mmc,
                                        udev_props, rpm_indicators)
        except Exception as e:
            return "UNKNOWN", "LOW", [f"Detection failed: {str(e)}"]

    def _check_rotational(self):
        """Check if device is rotational via sysfs."""
        rotational_path = f"/sys/block/{self.device_name}/queue/rotational"
        if os.path.exists(rotational_path):
            with open(rotational_path, 'r') as f:
                return f.read().strip() == '1'
        return None

    def _check_nvme_interface(self):
        """Check if device uses NVMe interface."""
        return self.device_name.startswith('nvme')

    def _check_mmc_interface(self):
        """Check if device uses MMC/eMMC interface."""
        return self.device_name.startswith('mmc')

    def _analyze_rpm_indicators(self, udev_props):
        """Analyze RPM indicators from udev properties."""
        ssd_indicators = []
        nvme_indicators = []

        if 'ID_ATA_ROTATION_RATE_RPM' in udev_props:
            rpm = udev_props['ID_ATA_ROTATION_RATE_RPM']
            if rpm == '0':
                ssd_indicators.append('zero_rpm')
            else:
                ssd_indicators.append(f'rpm_{rpm}')

        if ('ID_BUS' in udev_props and
                udev_props['ID_BUS'] == 'nvme'):
            nvme_indicators.append('nvme_bus')

        return ssd_indicators, nvme_indicators

    def _detect_from_model_name(self, udev_props):
        """Detect type from model name keywords."""
        model = udev_props.get('ID_MODEL', '').upper()
        if any(keyword in model for keyword in ['SSD', 'SOLID STATE']):
            return "SSD", "MEDIUM", ["SSD mentioned in model name"]
        elif any(keyword in model for keyword in
                 ['HDD', 'HARD DISK', 'HARDDRIVE']):
            return "HDD", "MEDIUM", ["HDD mentioned in model name"]
        return None, None, None

    def _determine_type(self, is_rotational, is_nvme, is_mmc, udev_props,
                        rpm_indicators):
        """Determine device type from all indicators."""
        ssd_indicators, nvme_indicators = rpm_indicators

        if is_nvme or 'nvme_bus' in nvme_indicators:
            return "NVMe SSD", "HIGH", ["NVMe interface detected"]
        elif is_mmc:
            return "eMMC/MMC", "HIGH", ["MMC interface detected"]
        elif is_rotational is False:
            return "SSD", "HIGH", ["Non-rotational device"]
        elif is_rotational is True:
            return "HDD", "HIGH", ["Rotational device"]
        elif 'zero_rpm' in ssd_indicators:
            return "SSD", "MEDIUM", ["Zero RPM indicates SSD"]
        elif any('rpm_' in indicator for indicator in ssd_indicators):
            return "HDD", "MEDIUM", [f"Rotational speed detected: "
                                     f"{ssd_indicators[0]}"]
        else:
            return self._detect_from_model_name(udev_props)

    def is_mounted(self):
        """
        Check if device or partitions are mounted.

        Returns:
            tuple: (is_mounted, mount_info_list)
        """
        try:
            # Check if the device itself is mounted
            mount_output = subprocess.check_output(['mount']).decode()
            device_mounted = self.device_path in mount_output

            # Get detailed mount information using lsblk
            cmd = ['lsblk', '-o', 'NAME,MOUNTPOINT', self.device_path, '-n']
            lsblk_output = subprocess.check_output(cmd).decode()

            mounted_partitions = []
            for line in lsblk_output.strip().split('\n'):
                if line.strip():
                    parts = line.split()
                    if len(parts) >= 2 and parts[1] and parts[1] != '-':
                        mounted_partitions.append(f"/dev/{parts[0]} -> "
                                                  f"{parts[1]}")

            is_mounted = device_mounted or len(mounted_partitions) > 0
            mount_info = mounted_partitions if mounted_partitions else []

            return is_mounted, mount_info
        except Exception:
            return False, []

    def get_partitions(self):
        """
        Get partition information using lsblk.

        Returns:
            str: Formatted partition information
        """
        try:
            cmd = ['lsblk', '-o', 'NAME,SIZE,TYPE,MOUNTPOINTS',
                   self.device_path]
            partitions = subprocess.check_output(cmd).decode()
            return partitions
        except Exception as e:
            return f"Error getting partition info: {e}"

    def display_info(self):
        """Display comprehensive device information."""
        try:
            size = self.get_size()
            properties = self.get_device_properties()
            disk_type, confidence, details = self.detect_type()
            partitions = self.get_partitions()
            is_mounted, mount_info = self.is_mounted()

            self._display_header()
            self._display_basic_info(size, properties)
            self._display_type_info(disk_type, confidence, details)
            self._display_partition_info(partitions)
            self._display_mount_status(is_mounted, mount_info)
        except Exception as e:
            print(f"Error getting info: {e}")

    def _display_header(self):
        """Display information header."""
        print("=" * 70)
        print("DEVICE INFORMATION")
        print("=" * 70)

    def _display_basic_info(self, size, properties):
        """Display basic device information."""
        print(f"• Device: {self.device_path}")
        print(f"• Size: {size / GIGABYTE:.2f} GB")
        if 'ID_MODEL' in properties:
            print(f"• Model: {properties['ID_MODEL']}")
        if 'ID_SERIAL_SHORT' in properties:
            print(f"• Serial: {properties['ID_SERIAL_SHORT']}")

    def _display_type_info(self, disk_type, confidence, details):
        """Display device type information."""
        print(f"• Type: {disk_type} (confidence: {confidence})")
        if details:
            print(f"• Detection details: {', '.join(details)}")

    def _display_partition_info(self, partitions):
        """Display partition information."""
        print("📁 Device and partitions:")
        print(partitions)

    def _display_mount_status(self, is_mounted, mount_info):
        """Display mount status with warnings."""
        if is_mounted:
            print(f"⚠️  WARNING: {self.device_path} or its partitions "
                  f"are mounted!")
            if mount_info:
                print("📌 Mounted partitions:")
                for mount in mount_info:
                    print(f"   • {mount}")
        else:
            print(f"✅ {self.device_path} is not mounted - safe to proceed")
