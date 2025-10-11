#!/usr/bin/env python3
"""
WipeStrategy classes for wipeit - Secure device wiping utility.

This module provides the Strategy pattern for different wiping algorithms:
- StandardStrategy: Fixed chunk size wiping
- AdaptiveStrategy: Dynamic chunk sizing based on position and speed
- SmallChunkStrategy: Small chunks for slow/unreliable drives
"""

import os
import time
from abc import ABC, abstractmethod

from global_constants import (
    GB_MILESTONE_THRESHOLD,
    GIGABYTE,
    MAX_SMALL_CHUNK_SIZE,
    MEGABYTE,
    MILESTONE_INCREMENT_PERCENT,
)


class WipeStrategy(ABC):
    """
    Abstract base class for wiping strategies.

    Defines the interface and common functionality for all wiping strategies.
    Subclasses implement specific algorithms for wiping block devices.
    """

    def __init__(self, device_path, total_size, chunk_size,
                 start_position=0, pretest_results=None,
                 progress_callback=None):
        """
        Initialize wipe strategy.

        Args:
            device_path: Path to block device (e.g., '/dev/sdb')
            total_size: Total size of device in bytes
            chunk_size: Base chunk size for writing in bytes
            start_position: Starting position in bytes (for resume)
            pretest_results: Optional pretest results dict
            progress_callback: Optional callback(written, size, chunk_size)
        """
        self.device_path = device_path
        self.total_size = total_size
        self.chunk_size = chunk_size
        self.written = start_position
        self.start_time = time.time()
        self.pretest_results = pretest_results
        self.progress_callback = progress_callback
        self.last_milestone = 0  # Track last shown milestone for finish time

    @abstractmethod
    def wipe(self):
        """
        Execute the wiping strategy.

        Returns:
            bool: True if wipe completed successfully, False otherwise

        Raises:
            KeyboardInterrupt: If user interrupts the wipe
            Exception: On I/O or other errors
        """
        pass

    @abstractmethod
    def get_strategy_name(self):
        """
        Get the name of this strategy.

        Returns:
            str: Strategy name for display/logging
        """
        pass

    def _calculate_eta(self):
        """
        Calculate estimated time remaining.

        Returns:
            str: Formatted ETA string (HH:MM:SS) or "??:??:??"
        """
        elapsed_time = time.time() - self.start_time
        if self.written > 0 and elapsed_time > 0:
            eta_seconds = (self.total_size - self.written) / \
                         (self.written / elapsed_time)
            hours = int(eta_seconds // 3600)
            minutes = int((eta_seconds % 3600) // 60)
            seconds = int(eta_seconds % 60)
            return f"{hours:02d}:{minutes:02d}:{seconds:02d}"
        return "??:??:??"

    def _format_progress_bar(self, bar_length=50):
        """
        Format visual progress bar.

        Args:
            bar_length: Length of progress bar in characters

        Returns:
            str: Formatted progress bar (e.g., "█████░░░░░")
        """
        filled_length = int(bar_length * self.written // self.total_size)
        return '█' * filled_length + '░' * (bar_length - filled_length)

    def _display_progress(self, current_speed=None):
        """
        Display progress information.

        Args:
            current_speed: Optional current speed in MB/s
        """
        progress_percent = (self.written / self.total_size) * 100
        eta_str = self._calculate_eta()
        bar = self._format_progress_bar()

        speed_str = ""
        if current_speed is not None:
            speed_str = f" Speed: {current_speed:.1f}MB/s"

        print(f"\r• Progress: {progress_percent:.1f}% |{bar}| "
              f"{self.written / GIGABYTE:.1f}GB/"
              f"{self.total_size / GIGABYTE:.1f}GB ETA: {eta_str}"
              f"{speed_str}", end='', flush=True)

        # Display estimated finish time at 5% milestones
        current_milestone = int(progress_percent) // \
            MILESTONE_INCREMENT_PERCENT * MILESTONE_INCREMENT_PERCENT
        if (current_milestone > self.last_milestone and
                current_milestone % MILESTONE_INCREMENT_PERCENT == 0 and
                self.written > 0):
            self.last_milestone = current_milestone
            # Calculate estimated finish time
            elapsed_time = time.time() - self.start_time
            if elapsed_time > 0:
                eta_seconds = (self.total_size - self.written) / \
                             (self.written / elapsed_time)
                estimated_finish = time.time() + eta_seconds
                finish_time_str = time.strftime(
                    "%I:%M %p", time.localtime(estimated_finish))
                print(f"\n• Estimated Finish Time: {finish_time_str}",
                      flush=True)

    def _save_progress_checkpoint(self):
        """
        Trigger progress checkpoint save via callback.

        Calls the progress_callback if provided, allowing external code
        to handle progress file operations.
        """
        if self.progress_callback:
            self.progress_callback(self.written, self.total_size,
                                   self.chunk_size)

    def _write_chunk(self, chunk_data):
        """
        Write a chunk of data to the device.

        Args:
            chunk_data: Bytes to write

        Returns:
            float: Time taken to write chunk in seconds

        Raises:
            IOError: If write fails
        """
        chunk_start_time = time.time()
        with open(self.device_path, 'wb') as f:
            f.seek(self.written)
            f.write(chunk_data)
            f.flush()
            os.fsync(f.fileno())
        return time.time() - chunk_start_time


class StandardStrategy(WipeStrategy):
    """
    Standard wiping strategy with fixed chunk size.

    Writes data in fixed-size chunks sequentially through the device.
    Simple and reliable, suitable for most SSDs and consistent HDDs.
    """

    def get_strategy_name(self):
        """
        Get the name of this strategy.

        Returns:
            str: "standard"
        """
        return "standard"

    def wipe(self):
        """
        Execute standard wiping with fixed chunk size.

        Returns:
            bool: True if wipe completed successfully

        Raises:
            KeyboardInterrupt: If user interrupts the wipe
            Exception: On I/O or other errors
        """
        while self.written < self.total_size:
            current_chunk_size = min(self.chunk_size,
                                     self.total_size - self.written)

            chunk_data = b'\x00' * current_chunk_size
            self._write_chunk(chunk_data)

            self.written += current_chunk_size

            self._display_progress()

            if self.written % GB_MILESTONE_THRESHOLD == 0:
                self._save_progress_checkpoint()

        print()
        return True


class SmallChunkStrategy(StandardStrategy):
    """
    Small chunk wiping strategy for slow/unreliable drives.

    Uses smaller chunk sizes (max 10MB) for better responsiveness
    and progress tracking on slow devices.
    """

    def __init__(self, device_path, total_size, chunk_size,
                 start_position=0, pretest_results=None,
                 progress_callback=None):
        """
        Initialize small chunk strategy.

        Args:
            device_path: Path to block device
            total_size: Total size of device in bytes
            chunk_size: Base chunk size (will be capped at 10MB)
            start_position: Starting position in bytes (for resume)
            pretest_results: Optional pretest results dict
            progress_callback: Optional progress callback function
        """
        limited_chunk_size = min(chunk_size, MAX_SMALL_CHUNK_SIZE)
        super().__init__(device_path, total_size, limited_chunk_size,
                         start_position, pretest_results, progress_callback)

    def get_strategy_name(self):
        """
        Get the name of this strategy.

        Returns:
            str: "small_chunk"
        """
        return "small_chunk"


class AdaptiveStrategy(WipeStrategy):
    """
    Adaptive wiping strategy with dynamic chunk sizing.

    Adjusts chunk size based on disk position and write speed:
    - Beginning (0-10%): Larger chunks (faster outer tracks)
    - Middle (10-90%): Adaptive based on speed
    - End (90-100%): Smaller chunks (slower inner tracks)

    Tracks speed samples to optimize performance on HDDs.
    """

    def __init__(self, device_path, total_size, chunk_size,
                 start_position=0, pretest_results=None,
                 progress_callback=None):
        """
        Initialize adaptive strategy.

        Args:
            device_path: Path to block device
            total_size: Total size of device in bytes
            chunk_size: Base chunk size for calculations
            start_position: Starting position in bytes (for resume)
            pretest_results: Optional pretest results dict
            progress_callback: Optional progress callback function
        """
        super().__init__(device_path, total_size, chunk_size,
                         start_position, pretest_results, progress_callback)
        self._speed_samples = []

    def get_strategy_name(self):
        """
        Get the name of this strategy.

        Returns:
            str: "adaptive_chunk"
        """
        return "adaptive_chunk"

    def _calculate_adaptive_chunk_size(self):
        """
        Calculate adaptive chunk size based on position and speed.

        Returns:
            int: Calculated chunk size in bytes (guaranteed integer)
        """
        position_ratio = self.written / self.total_size

        if position_ratio < 0.1:
            current_chunk_size = int(self.chunk_size * 2)
        elif position_ratio > 0.9:
            current_chunk_size = int(self.chunk_size * 0.5)
        else:
            if len(self._speed_samples) > 0:
                recent_samples = self._speed_samples[-5:]
                avg_speed = sum(recent_samples) / len(recent_samples)
                if avg_speed < 50:
                    current_chunk_size = int(self.chunk_size * 0.5)
                elif avg_speed > 200:
                    current_chunk_size = int(self.chunk_size * 1.5)
                else:
                    current_chunk_size = self.chunk_size
            else:
                current_chunk_size = self.chunk_size

        current_chunk_size = max(MEGABYTE,
                                 min(current_chunk_size,
                                     self.total_size - self.written))

        return int(current_chunk_size)

    def wipe(self):
        """
        Execute adaptive wiping with dynamic chunk sizing.

        Returns:
            bool: True if wipe completed successfully

        Raises:
            KeyboardInterrupt: If user interrupts the wipe
            Exception: On I/O or other errors
        """
        while self.written < self.total_size:
            current_chunk_size = self._calculate_adaptive_chunk_size()

            chunk_data = b'\x00' * current_chunk_size
            chunk_duration = self._write_chunk(chunk_data)

            if chunk_duration > 0:
                chunk_speed = current_chunk_size / chunk_duration / MEGABYTE
                self._speed_samples.append(chunk_speed)
            else:
                chunk_speed = 0

            self.written += current_chunk_size

            self._display_progress(current_speed=chunk_speed)

            if self.written % GB_MILESTONE_THRESHOLD == 0:
                self._save_progress_checkpoint()

        print()
        return True
