#!/usr/bin/env python3
"""
Unit tests for progress_file_version module.
"""

import unittest
from progress_file_version import ProgressFileVersion


class TestProgressFileVersion(unittest.TestCase):
    """Test progress file versioning and migration."""

    def test_current_version_is_2(self):
        """Verify current version is 2."""
        self.assertEqual(ProgressFileVersion.get_current_version(), 2)

    def test_add_version_to_data(self):
        """Test adding version to progress data."""
        data = {'device': '/dev/sdb', 'written': 1000}
        result = ProgressFileVersion.add_version_to_data(data)
        self.assertEqual(result['version'], 2)
        self.assertEqual(result['device'], '/dev/sdb')

    def test_migrate_v1_to_v2(self):
        """Test migration from v1 to v2 format."""
        v1_data = {
            'device': '/dev/sdb',
            'written': 1000,
            'total_size': 10000,
            'progress_percent': 10.0,
            'timestamp': 123456.0
            # No version field - defaults to v1
        }

        migrated, was_migrated, warning = \
            ProgressFileVersion.migrate_progress_data(v1_data)

        self.assertTrue(was_migrated)
        self.assertEqual(migrated['version'], 2)
        self.assertIn('device_id', migrated)
        self.assertIsNone(migrated['device_id'])
        self.assertIn('chunk_size', migrated)
        self.assertIsNone(migrated['chunk_size'])
        self.assertIn('algorithm', migrated)
        self.assertIsNone(migrated['algorithm'])
        self.assertIn('v1', warning)

    def test_migrate_v2_no_changes(self):
        """Test v2 data requires no migration."""
        v2_data = {
            'version': 2,
            'device': '/dev/sdb',
            'written': 1000,
            'total_size': 10000,
            'progress_percent': 10.0,
            'timestamp': 123456.0,
            'device_id': {'serial': 'ABC123'},
            'chunk_size': 104857600,
            'algorithm': 'adaptive_chunk'
        }

        migrated, was_migrated, warning = \
            ProgressFileVersion.migrate_progress_data(v2_data)

        self.assertFalse(was_migrated)
        self.assertEqual(migrated['version'], 2)
        self.assertIsNone(warning)

    def test_migrate_future_version_warns(self):
        """Test future version produces warning."""
        future_data = {
            'version': 999,
            'device': '/dev/sdb',
            'written': 1000,
            'total_size': 10000,
            'progress_percent': 10.0,
            'timestamp': 123456.0
        }

        migrated, was_migrated, warning = \
            ProgressFileVersion.migrate_progress_data(future_data)

        self.assertFalse(was_migrated)
        self.assertIn('999', warning)
        self.assertIn('newer version', warning.lower())

    def test_validate_v1_data_valid(self):
        """Test validation of valid v1 data."""
        v1_data = {
            'device': '/dev/sdb',
            'written': 1000,
            'total_size': 10000,
            'progress_percent': 10.0,
            'timestamp': 123456.0
        }

        is_valid, error = \
            ProgressFileVersion.validate_progress_data(v1_data)
        self.assertTrue(is_valid)
        self.assertIsNone(error)

    def test_validate_v2_data_valid(self):
        """Test validation of valid v2 data."""
        v2_data = {
            'version': 2,
            'device': '/dev/sdb',
            'written': 1000,
            'total_size': 10000,
            'progress_percent': 10.0,
            'timestamp': 123456.0,
            'device_id': {'serial': 'ABC123'},
            'chunk_size': 104857600,
            'algorithm': 'adaptive_chunk'
        }

        is_valid, error = \
            ProgressFileVersion.validate_progress_data(v2_data)
        self.assertTrue(is_valid)
        self.assertIsNone(error)

    def test_validate_missing_required_field(self):
        """Test validation fails on missing required field."""
        invalid_data = {
            'device': '/dev/sdb',
            'written': 1000
            # Missing total_size, progress_percent, timestamp
        }

        is_valid, error = \
            ProgressFileVersion.validate_progress_data(invalid_data)
        self.assertFalse(is_valid)
        self.assertIn('Missing required field', error)

    def test_validate_v2_missing_new_fields(self):
        """Test v2 validation fails on missing v2-specific fields."""
        invalid_v2 = {
            'version': 2,
            'device': '/dev/sdb',
            'written': 1000,
            'total_size': 10000,
            'progress_percent': 10.0,
            'timestamp': 123456.0
            # Missing device_id, chunk_size, algorithm
        }

        is_valid, error = \
            ProgressFileVersion.validate_progress_data(invalid_v2)
        self.assertFalse(is_valid)
        self.assertIn('v2 field', error)

    def test_validate_v2_with_none_values(self):
        """Test v2 data valid even with None for new fields."""
        v2_data = {
            'version': 2,
            'device': '/dev/sdb',
            'written': 1000,
            'total_size': 10000,
            'progress_percent': 10.0,
            'timestamp': 123456.0,
            'device_id': None,  # Can be None
            'chunk_size': None,   # Can be None
            'algorithm': None   # Can be None
        }

        is_valid, error = \
            ProgressFileVersion.validate_progress_data(v2_data)
        self.assertTrue(is_valid)
        self.assertIsNone(error)


if __name__ == '__main__':
    unittest.main()
