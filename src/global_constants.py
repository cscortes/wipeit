#!/usr/bin/env python3
"""
Global constants for wipeit - Secure device wiping utility.

This module contains all application-wide constants used throughout the codebase.
All constants follow the ALL_CAPS naming convention for easy identification.
"""

# Size multipliers for parsing size strings
KILOBYTE = 1024
MEGABYTE = 1024 * 1024
GIGABYTE = 1024 * 1024 * 1024
TERABYTE = 1024 * 1024 * 1024 * 1024

# Size parsing limits
MIN_SIZE_BYTES = MEGABYTE  # 1MB minimum
MAX_SIZE_BYTES = TERABYTE  # 1TB maximum

# Default chunk sizes
DEFAULT_CHUNK_SIZE = 100 * MEGABYTE  # 100MB
SMALL_CHUNK_SIZE = 10 * MEGABYTE     # 10MB
MAX_SMALL_CHUNK_SIZE = 10 * MEGABYTE  # 10MB max for small chunk algorithm

# Progress file expiration (24 hours in seconds)
PROGRESS_FILE_EXPIRY_SECONDS = 24 * 3600

# Time conversion constants
SECONDS_PER_MINUTE = 60
SECONDS_PER_HOUR = 3600
MINUTES_PER_HOUR = 60

# Display formatting
DISPLAY_LINE_WIDTH = 70

# Speed thresholds for algorithm selection
LOW_SPEED_THRESHOLD_MBPS = 50  # MB/s
HIGH_VARIANCE_THRESHOLD_MBPS = 100  # MB/s

# Progress milestone thresholds
MILESTONE_INCREMENT_PERCENT = 5  # 5% increments
GB_MILESTONE_THRESHOLD = GIGABYTE  # 1GB milestone threshold

# Test constants
TEST_DEVICE_SIZE_100MB = 100 * MEGABYTE
TEST_DEVICE_SIZE_100GB = 100 * GIGABYTE
TEST_DEVICE_SIZE_1GB = GIGABYTE
TEST_DEVICE_SIZE_4GB = 4 * GIGABYTE
TEST_DEVICE_SIZE_1TB = TERABYTE

# Speed test constants
TEST_SPEED_1000_MBPS = 1000  # MB/s
TEST_SPEED_250_MBPS = 250    # MB/s
TEST_SPEED_200_MBPS = 200    # MB/s
TEST_SPEED_10_MBPS = 10      # MB/s
TEST_SPEED_50_MBPS = 50      # MB/s

# Progress test data
TEST_WRITTEN_1GB = GIGABYTE
TEST_TOTAL_SIZE_4GB = 4 * GIGABYTE
TEST_CHUNK_SIZE_100MB = 100 * MEGABYTE

# Time test constants
TEST_TIME_1_HOUR_SECONDS = 3600
TEST_TIME_24_HOURS_PLUS_1_SECOND = 24 * 3600 + 1

# Milestone test thresholds
TEST_MILESTONE_5_PERCENT = 5
TEST_MILESTONE_10_PERCENT = 10
TEST_MILESTONE_50_PERCENT = 50

