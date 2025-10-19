#!/usr/bin/env python3
"""
Progress file version management for wipeit.

Handles versioning and migration of progress files to maintain
backwards compatibility as the file format evolves.
"""


class ProgressFileVersion:
    """
    Manages progress file versioning and format migration.

    Version history:
    - v1: Original format (device, written, total_size, progress_percent,
          timestamp)
    - v2: Added device_id (for auto-detect), chunk_size (for buffer
          consistency), algorithm (for resume consistency)
    """

    CURRENT_VERSION = 2

    @classmethod
    def get_current_version(cls):
        """Return the current progress file version."""
        return cls.CURRENT_VERSION

    @classmethod
    def add_version_to_data(cls, progress_data):
        """
        Add version number to progress data before saving.

        Args:
            progress_data: Dictionary of progress data

        Returns:
            Dictionary with version field added
        """
        progress_data['version'] = cls.CURRENT_VERSION
        return progress_data

    @classmethod
    def migrate_progress_data(cls, progress_data):
        """
        Migrate progress data from older versions to current format.

        Handles backwards compatibility by:
        - Detecting version (defaults to v1 if missing)
        - Migrating v1 -> v2 (adds device_id, chunk_size, algorithm fields)
        - Warning on future versions

        Args:
            progress_data: Dictionary loaded from progress file

        Returns:
            tuple: (migrated_data, was_migrated, warning_message)
                - migrated_data: Updated progress data
                - was_migrated: True if migration was performed
                - warning_message: String message or None
        """
        version = progress_data.get('version', 1)
        was_migrated = False
        warning_message = None

        if version == 1:
            # Migrate v1 to v2
            was_migrated = True
            progress_data['version'] = cls.CURRENT_VERSION
            # Add new fields with None defaults (backwards compatible)
            progress_data.setdefault('device_id', None)
            progress_data.setdefault('chunk_size', None)
            progress_data.setdefault('algorithm', None)
            warning_message = ("Found older progress file format (v1), "
                               f"upgraded to v{cls.CURRENT_VERSION}")

        elif version > cls.CURRENT_VERSION:
            # Future version - warn but attempt to continue
            warning_message = (f"Progress file is from newer version "
                               f"(v{version}), current version is "
                               f"v{cls.CURRENT_VERSION}. "
                               f"May have compatibility issues.")

        elif version == cls.CURRENT_VERSION:
            # Current version - no migration needed
            pass

        return progress_data, was_migrated, warning_message

    @classmethod
    def validate_progress_data(cls, progress_data):
        """
        Validate that progress data has required fields for its version.

        Args:
            progress_data: Dictionary of progress data

        Returns:
            tuple: (is_valid, error_message)
        """
        version = progress_data.get('version', 1)

        # Required fields for all versions
        required_v1_fields = ['device', 'written', 'total_size',
                              'progress_percent', 'timestamp']

        for field in required_v1_fields:
            if field not in progress_data:
                return False, f"Missing required field: {field}"

        # Additional fields for v2+
        if version >= 2:
            # These fields should exist but can be None
            if 'device_id' not in progress_data:
                return False, "Missing v2 field: device_id"
            if 'chunk_size' not in progress_data:
                return False, "Missing v2 field: chunk_size"
            if 'algorithm' not in progress_data:
                return False, "Missing v2 field: algorithm"

        return True, None
