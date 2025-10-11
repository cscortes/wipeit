#!/usr/bin/env python3
"""
Unit tests for disk_pretest - HDD pretest operations.
"""

import unittest
from io import StringIO
from unittest.mock import mock_open, patch

from disk_pretest import DiskPretest, PretestResults
from global_constants import (
    DEFAULT_CHUNK_SIZE,
    GIGABYTE,
    HIGH_VARIANCE_THRESHOLD_MBPS,
    LOW_SPEED_THRESHOLD_MBPS,
    MEGABYTE,
)


class TestPretestResults(unittest.TestCase):
    """Test PretestResults class."""

    def test_init(self):
        """Test PretestResults initialization."""
        speeds = [100.0, 90.0, 80.0]
        positions = ['beginning', 'middle', 'end']
        results = PretestResults(
            speeds=speeds,
            positions=positions,
            average_speed=90.0,
            speed_variance=20.0,
            recommended_algorithm='standard',
            reason='Test reason',
            timestamp=1234567890.0
        )

        self.assertEqual(results.speeds, speeds)
        self.assertEqual(results.positions, positions)
        self.assertEqual(results.average_speed, 90.0)
        self.assertEqual(results.speed_variance, 20.0)
        self.assertEqual(results.recommended_algorithm, 'standard')
        self.assertEqual(results.reason, 'Test reason')
        self.assertEqual(results.timestamp, 1234567890.0)

    def test_to_dict(self):
        """Test conversion to dictionary format."""
        results = PretestResults(
            speeds=[100.0, 90.0, 80.0],
            positions=['beginning', 'middle', 'end'],
            average_speed=90.0,
            speed_variance=20.0,
            recommended_algorithm='adaptive_chunk',
            reason='High variance',
            timestamp=1234567890.0
        )

        result_dict = results.to_dict()

        self.assertEqual(result_dict['speeds'], [100.0, 90.0, 80.0])
        self.assertEqual(result_dict['average_speed'], 90.0)
        self.assertEqual(result_dict['speed_variance'], 20.0)
        self.assertEqual(result_dict['recommended_algorithm'],
                         'adaptive_chunk')
        self.assertEqual(result_dict['reason'], 'High variance')
        self.assertIn('analysis', result_dict)
        self.assertEqual(result_dict['analysis']['recommended_algorithm'],
                         'adaptive_chunk')
        self.assertEqual(result_dict['analysis']['reason'],
                         'High variance')


class TestDiskPretest(unittest.TestCase):
    """Test DiskPretest class."""

    def test_init(self):
        """Test DiskPretest initialization."""
        pretest = DiskPretest('/dev/sdb', DEFAULT_CHUNK_SIZE)

        self.assertEqual(pretest.device_path, '/dev/sdb')
        self.assertEqual(pretest.chunk_size, DEFAULT_CHUNK_SIZE)
        self.assertFalse(pretest.quiet)
        self.assertIsNone(pretest._last_results)

    def test_init_with_quiet(self):
        """Test DiskPretest initialization with quiet mode."""
        pretest = DiskPretest('/dev/sdb', DEFAULT_CHUNK_SIZE, quiet=True)

        self.assertTrue(pretest.quiet)

    def test_get_recommendation_without_test(self):
        """Test get_recommendation raises error without pretest."""
        pretest = DiskPretest('/dev/sdb', DEFAULT_CHUNK_SIZE)

        with self.assertRaises(RuntimeError):
            pretest.get_recommendation()


class TestPretestExecution(unittest.TestCase):
    """Test pretest execution methods."""

    @patch('disk_pretest.DiskPretest._get_device_size')
    @patch('builtins.open', new_callable=mock_open)
    @patch('os.fsync')
    @patch('time.time')
    def test_test_position(self, mock_time, mock_fsync, mock_file,
                           mock_get_size):
        """Test _test_position method."""
        mock_time.side_effect = [1000.0, 1001.0]
        mock_file_handle = mock_file.return_value.__enter__.return_value
        mock_file_handle.fileno.return_value = 3

        pretest = DiskPretest('/dev/sdb', 100 * MEGABYTE, quiet=True)
        speed = pretest._test_position(0, 'beginning')

        self.assertIsInstance(speed, float)
        self.assertGreater(speed, 0)
        mock_file_handle.seek.assert_called_once_with(0)
        mock_file_handle.write.assert_called_once()

    @patch('disk_pretest.DiskPretest._get_device_size')
    @patch('builtins.open', new_callable=mock_open)
    @patch('os.fsync')
    @patch('time.time')
    def test_test_position_with_output(self, mock_time, mock_fsync,
                                       mock_file, mock_get_size):
        """Test _test_position with console output."""
        mock_time.side_effect = [1000.0, 1001.0]
        mock_file_handle = mock_file.return_value.__enter__.return_value
        mock_file_handle.fileno.return_value = 3

        pretest = DiskPretest('/dev/sdb', 100 * MEGABYTE, quiet=False)

        with patch('sys.stdout', new_callable=StringIO) as mock_stdout:
            pretest._test_position(0, 'beginning')

        output = mock_stdout.getvalue()
        self.assertIn('Testing beginning', output)
        self.assertIn('Beginning:', output)

    @patch('disk_pretest.DiskPretest._get_device_size')
    @patch('builtins.open', new_callable=mock_open)
    @patch('os.fsync')
    @patch('time.time')
    def test_run_pretest(self, mock_time, mock_fsync, mock_file,
                         mock_get_size):
        """Test run_pretest method."""
        mock_get_size.return_value = 100 * GIGABYTE
        time_values = [1000.0 + i * 1.0 for i in range(10)]
        mock_time.side_effect = time_values

        mock_file_handle = mock_file.return_value.__enter__.return_value
        mock_file_handle.fileno.return_value = 3

        pretest = DiskPretest('/dev/sdb', 100 * MEGABYTE, quiet=True)
        results = pretest.run_pretest()

        self.assertIsNotNone(results)
        self.assertIsInstance(results, PretestResults)
        self.assertEqual(len(results.speeds), 3)
        self.assertEqual(len(results.positions), 3)
        self.assertGreater(results.average_speed, 0)
        self.assertGreaterEqual(results.speed_variance, 0)
        self.assertIn(results.recommended_algorithm,
                      ['standard', 'adaptive_chunk', 'small_chunk'])

    @patch('disk_pretest.DiskPretest._get_device_size')
    @patch('builtins.open', new_callable=mock_open)
    @patch('os.fsync')
    @patch('time.time')
    def test_run_pretest_with_output(self, mock_time, mock_fsync, mock_file,
                                     mock_get_size):
        """Test run_pretest with console output."""
        mock_get_size.return_value = 100 * GIGABYTE
        time_values = [1000.0 + i * 1.0 for i in range(10)]
        mock_time.side_effect = time_values

        mock_file_handle = mock_file.return_value.__enter__.return_value
        mock_file_handle.fileno.return_value = 3

        pretest = DiskPretest('/dev/sdb', 100 * MEGABYTE, quiet=False)

        with patch('sys.stdout', new_callable=StringIO) as mock_stdout:
            pretest.run_pretest()

        output = mock_stdout.getvalue()
        self.assertIn('HDD PRETEST', output)
        self.assertIn('PRETEST ANALYSIS', output)
        self.assertIn('Average speed:', output)
        self.assertIn('Speed variance:', output)
        self.assertIn('Recommended algorithm:', output)

    @patch('disk_pretest.DiskPretest._get_device_size')
    def test_run_pretest_error_handling(self, mock_get_size):
        """Test run_pretest handles errors gracefully."""
        mock_get_size.side_effect = OSError("Permission denied")

        pretest = DiskPretest('/dev/sdb', 100 * MEGABYTE, quiet=True)
        results = pretest.run_pretest()

        self.assertIsNone(results)

    @patch('disk_pretest.DiskPretest._get_device_size')
    @patch('builtins.open', new_callable=mock_open)
    @patch('os.fsync')
    @patch('time.time')
    def test_get_recommendation_after_test(self, mock_time, mock_fsync,
                                           mock_file, mock_get_size):
        """Test get_recommendation after running pretest."""
        mock_get_size.return_value = 100 * GIGABYTE
        time_values = [1000.0 + i * 1.0 for i in range(10)]
        mock_time.side_effect = time_values

        mock_file_handle = mock_file.return_value.__enter__.return_value
        mock_file_handle.fileno.return_value = 3

        pretest = DiskPretest('/dev/sdb', 100 * MEGABYTE, quiet=True)
        results = pretest.run_pretest()

        recommendation = pretest.get_recommendation()
        self.assertEqual(recommendation, results.recommended_algorithm)


class TestAnalysis(unittest.TestCase):
    """Test analysis methods."""

    def test_analyze_speeds(self):
        """Test _analyze_speeds method."""
        pretest = DiskPretest('/dev/sdb', DEFAULT_CHUNK_SIZE, quiet=True)
        speeds = [100.0, 90.0, 80.0]

        avg_speed, variance = pretest._analyze_speeds(speeds)

        self.assertEqual(avg_speed, 90.0)
        self.assertEqual(variance, 20.0)

    def test_analyze_speeds_same_values(self):
        """Test _analyze_speeds with identical speeds."""
        pretest = DiskPretest('/dev/sdb', DEFAULT_CHUNK_SIZE, quiet=True)
        speeds = [100.0, 100.0, 100.0]

        avg_speed, variance = pretest._analyze_speeds(speeds)

        self.assertEqual(avg_speed, 100.0)
        self.assertEqual(variance, 0.0)

    def test_analyze_speeds_extreme_variance(self):
        """Test _analyze_speeds with extreme variance."""
        pretest = DiskPretest('/dev/sdb', DEFAULT_CHUNK_SIZE, quiet=True)
        speeds = [200.0, 150.0, 10.0]

        avg_speed, variance = pretest._analyze_speeds(speeds)

        self.assertAlmostEqual(avg_speed, 120.0, places=1)
        self.assertEqual(variance, 190.0)


class TestAlgorithmRecommendation(unittest.TestCase):
    """Test algorithm recommendation logic."""

    def test_determine_algorithm_high_variance(self):
        """Test high variance recommends adaptive_chunk."""
        pretest = DiskPretest('/dev/sdb', DEFAULT_CHUNK_SIZE, quiet=True)
        avg_speed = 150.0
        variance = HIGH_VARIANCE_THRESHOLD_MBPS + 10

        algorithm, reason = pretest._determine_algorithm(avg_speed, variance)

        self.assertEqual(algorithm, 'adaptive_chunk')
        self.assertIn('variance', reason.lower())

    def test_determine_algorithm_low_speed(self):
        """Test low speed recommends small_chunk."""
        pretest = DiskPretest('/dev/sdb', DEFAULT_CHUNK_SIZE, quiet=True)
        avg_speed = LOW_SPEED_THRESHOLD_MBPS - 10
        variance = 10.0

        algorithm, reason = pretest._determine_algorithm(avg_speed, variance)

        self.assertEqual(algorithm, 'small_chunk')
        self.assertIn('speed', reason.lower())

    def test_determine_algorithm_standard(self):
        """Test normal performance recommends standard."""
        pretest = DiskPretest('/dev/sdb', DEFAULT_CHUNK_SIZE, quiet=True)
        avg_speed = 150.0
        variance = 10.0

        algorithm, reason = pretest._determine_algorithm(avg_speed, variance)

        self.assertEqual(algorithm, 'standard')
        self.assertIn('Consistent', reason)

    def test_determine_algorithm_boundary_high_variance(self):
        """Test boundary: exactly at high variance threshold."""
        pretest = DiskPretest('/dev/sdb', DEFAULT_CHUNK_SIZE, quiet=True)
        avg_speed = 150.0
        variance = HIGH_VARIANCE_THRESHOLD_MBPS + 1

        algorithm, reason = pretest._determine_algorithm(avg_speed, variance)

        self.assertEqual(algorithm, 'adaptive_chunk')

    def test_determine_algorithm_boundary_low_speed(self):
        """Test boundary: exactly at low speed threshold."""
        pretest = DiskPretest('/dev/sdb', DEFAULT_CHUNK_SIZE, quiet=True)
        avg_speed = LOW_SPEED_THRESHOLD_MBPS - 1
        variance = 10.0

        algorithm, reason = pretest._determine_algorithm(avg_speed, variance)

        self.assertEqual(algorithm, 'small_chunk')


class TestIntegration(unittest.TestCase):
    """Integration tests for complete workflow."""

    @patch('disk_pretest.DiskPretest._get_device_size')
    @patch('builtins.open', new_callable=mock_open)
    @patch('os.fsync')
    @patch('time.time')
    def test_full_pretest_workflow(self, mock_time, mock_fsync, mock_file,
                                   mock_get_size):
        """Test complete pretest workflow."""
        mock_get_size.return_value = 100 * GIGABYTE
        time_values = [1000.0 + i * 1.0 for i in range(10)]
        mock_time.side_effect = time_values

        mock_file_handle = mock_file.return_value.__enter__.return_value
        mock_file_handle.fileno.return_value = 3

        pretest = DiskPretest('/dev/sdb', 100 * MEGABYTE, quiet=True)
        results = pretest.run_pretest()

        self.assertIsNotNone(results)

        result_dict = results.to_dict()
        self.assertIn('speeds', result_dict)
        self.assertIn('average_speed', result_dict)
        self.assertIn('speed_variance', result_dict)
        self.assertIn('analysis', result_dict)
        self.assertIn('recommended_algorithm', result_dict)
        self.assertIn('reason', result_dict)

        recommendation = pretest.get_recommendation()
        self.assertEqual(recommendation, result_dict['recommended_algorithm'])

    @patch('disk_pretest.DiskPretest._get_device_size')
    @patch('builtins.open', new_callable=mock_open)
    @patch('os.fsync')
    @patch('time.time')
    def test_backward_compatibility_format(self, mock_time, mock_fsync,
                                           mock_file, mock_get_size):
        """Test results match legacy format for backward compatibility."""
        mock_get_size.return_value = 100 * GIGABYTE

        time_values = [1000.0 + i * 1.0 for i in range(10)]
        mock_time.side_effect = time_values

        mock_file_handle = mock_file.return_value.__enter__.return_value
        mock_file_handle.fileno.return_value = 3

        pretest = DiskPretest('/dev/sdb', 100 * MEGABYTE, quiet=True)
        results = pretest.run_pretest()
        result_dict = results.to_dict()

        required_keys = [
            'speeds', 'average_speed', 'speed_variance',
            'analysis', 'recommended_algorithm', 'reason'
        ]
        for key in required_keys:
            self.assertIn(key, result_dict)

        self.assertIn('recommended_algorithm', result_dict['analysis'])
        self.assertIn('reason', result_dict['analysis'])

        self.assertEqual(
            result_dict['recommended_algorithm'],
            result_dict['analysis']['recommended_algorithm']
        )
        self.assertEqual(
            result_dict['reason'],
            result_dict['analysis']['reason']
        )


if __name__ == '__main__':
    test_suite = unittest.TestSuite()

    test_classes = [
        TestPretestResults,
        TestDiskPretest,
        TestPretestExecution,
        TestAnalysis,
        TestAlgorithmRecommendation,
        TestIntegration,
    ]

    for test_class in test_classes:
        tests = unittest.TestLoader().loadTestsFromTestCase(test_class)
        test_suite.addTests(tests)

    runner = unittest.TextTestRunner(verbosity=2)
    result = runner.run(test_suite)

    import sys
    sys.exit(0 if result.wasSuccessful() else 1)
