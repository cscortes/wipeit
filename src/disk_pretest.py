#!/usr/bin/env python3
"""
DiskPretest class for wipeit - HDD pretest operations.

This module provides the DiskPretest class which encapsulates all HDD
pretest functionality including speed testing and algorithm recommendation.
"""

import os
import time

from global_constants import (
    DEFAULT_CHUNK_SIZE,
    HIGH_VARIANCE_THRESHOLD_MBPS,
    LOW_SPEED_THRESHOLD_MBPS,
    MEGABYTE,
)


class PretestResults:
    """
    Results from a disk pretest operation.

    Contains speed measurements, analysis, and algorithm recommendation.
    """

    def __init__(self, speeds, positions, average_speed, speed_variance,
                 recommended_algorithm, reason, timestamp):
        """
        Initialize pretest results.

        Args:
            speeds: List of speeds at each position (MB/s)
            positions: List of position names
            average_speed: Average speed across all positions (MB/s)
            speed_variance: Speed variance (max - min) in MB/s
            recommended_algorithm: Recommended wiping algorithm
            reason: Reason for recommendation
            timestamp: Unix timestamp when test was performed
        """
        self.speeds = speeds
        self.positions = positions
        self.average_speed = average_speed
        self.speed_variance = speed_variance
        self.recommended_algorithm = recommended_algorithm
        self.reason = reason
        self.timestamp = timestamp

    def to_dict(self):
        """
        Convert results to dictionary format.

        Returns:
            dict: Results in legacy format for backward compatibility
        """
        return {
            'speeds': self.speeds,
            'average_speed': self.average_speed,
            'speed_variance': self.speed_variance,
            'analysis': {
                'recommended_algorithm': self.recommended_algorithm,
                'reason': self.reason
            },
            'recommended_algorithm': self.recommended_algorithm,
            'reason': self.reason
        }


class DiskPretest:
    """
    Performs HDD pretest operations to determine optimal wiping algorithm.

    Tests write speeds at different disk positions and recommends the best
    wiping strategy based on performance characteristics.
    """

    def __init__(self, device_path, chunk_size=DEFAULT_CHUNK_SIZE,
                 quiet=False):
        """
        Initialize disk pretest.

        Args:
            device_path: Path to block device (e.g., '/dev/sdb')
            chunk_size: Test chunk size in bytes
            quiet: If True, suppress console output
        """
        self.device_path = device_path
        self.chunk_size = chunk_size
        self.quiet = quiet
        self._last_results = None

    def run_pretest(self):
        """
        Execute the pretest operation.

        Tests write speeds at beginning, middle, and end of disk,
        analyzes results, and recommends optimal algorithm.

        Returns:
            PretestResults: Results object with measurements and
                           recommendation

        Raises:
            OSError: If device cannot be accessed
            IOError: If write operations fail
        """
        try:
            size = self._get_device_size()

            if not self.quiet:
                self._display_header(size)

            test_positions = [
                (0, "beginning"),
                (size // 2, "middle"),
                (size - self.chunk_size, "end")
            ]

            if not self.quiet:
                print(f"• Test positions: {len(test_positions)} locations")

            speeds = []
            position_names = []

            for position, name in test_positions:
                speed = self._test_position(position, name)
                speeds.append(speed)
                position_names.append(name)

            avg_speed, variance = self._analyze_speeds(speeds)
            algorithm, reason = self._determine_algorithm(avg_speed,
                                                          variance)

            results = PretestResults(
                speeds=speeds,
                positions=position_names,
                average_speed=avg_speed,
                speed_variance=variance,
                recommended_algorithm=algorithm,
                reason=reason,
                timestamp=0.0
            )

            self._last_results = results

            if not self.quiet:
                self._display_results(results)

            return results

        except Exception as e:
            if not self.quiet:
                print(f"Pretest failed: {e}")
            return None

    def get_recommendation(self):
        """
        Get algorithm recommendation from last pretest.

        Returns:
            str: Recommended algorithm name, or None if no test run

        Raises:
            RuntimeError: If no pretest has been run yet
        """
        if self._last_results is None:
            raise RuntimeError("No pretest has been run yet")
        return self._last_results.recommended_algorithm

    def _get_device_size(self):
        """
        Get device size in bytes.

        Returns:
            int: Device size in bytes

        Raises:
            OSError: If device size cannot be determined
        """
        from wipeit import get_block_device_size
        return get_block_device_size(self.device_path)

    def _test_position(self, position, name):
        """
        Test write speed at a specific disk position.

        Args:
            position: Byte offset on disk
            name: Position name for display

        Returns:
            float: Write speed in MB/s

        Raises:
            IOError: If write operation fails
        """
        if not self.quiet:
            print(f"• Testing {name} of disk...")

        start_time = time.time()

        with open(self.device_path, 'wb') as f:
            f.seek(position)
            f.write(b'\x00' * self.chunk_size)
            f.flush()
            os.fsync(f.fileno())

        end_time = time.time()
        duration = end_time - start_time
        speed = self.chunk_size / duration / MEGABYTE

        if not self.quiet:
            print(f"    • {name.capitalize()}: {speed:.2f} MB/s")

        return speed

    def _analyze_speeds(self, speeds):
        """
        Analyze speed measurements.

        Args:
            speeds: List of speed measurements in MB/s

        Returns:
            tuple: (average_speed, speed_variance) in MB/s
        """
        avg_speed = sum(speeds) / len(speeds)
        speed_variance = max(speeds) - min(speeds)
        return avg_speed, speed_variance

    def _determine_algorithm(self, avg_speed, variance):
        """
        Determine recommended algorithm based on performance.

        Args:
            avg_speed: Average speed in MB/s
            variance: Speed variance in MB/s

        Returns:
            tuple: (algorithm_name, reason)
        """
        if variance > HIGH_VARIANCE_THRESHOLD_MBPS:
            algorithm = "adaptive_chunk"
            reason = ("High speed variance detected - "
                      "adaptive chunk sizing recommended")
        elif avg_speed < LOW_SPEED_THRESHOLD_MBPS:
            algorithm = "small_chunk"
            reason = ("Low average speed - "
                      "small chunks for better responsiveness")
        else:
            algorithm = "standard"
            reason = "Consistent performance - standard algorithm recommended"

        return algorithm, reason

    def _display_header(self, size):
        """
        Display pretest header information.

        Args:
            size: Device size in bytes
        """
        print("=" * 50)
        print("HDD PRETEST")
        print("=" * 50)
        print("• Performing HDD pretest to optimize wiping algorithm...")
        print("  This will test write speeds at different disk positions.")
        print("  WARNING: This will write test data to the disk!")
        print(f"• Disk size: {size / (1024**3):.2f} GB")
        print(f"• Test chunk size: {self.chunk_size / (1024**2):.0f} MB")

    def _display_results(self, results):
        """
        Display pretest results and recommendation.

        Args:
            results: PretestResults object
        """
        print("\n" + "=" * 50)
        print("PRETEST ANALYSIS")
        print("=" * 50)
        print(f"• Average speed: {results.average_speed:.2f} MB/s")
        print(f"• Speed variance: {results.speed_variance:.2f} MB/s")
        print(f"• Recommended algorithm: {results.recommended_algorithm}")
        print(f"• Reason: {results.reason}")
