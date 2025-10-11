#!/usr/bin/env python3
"""
Unit tests for wipe_strategy - Strategy pattern for wiping algorithms.
"""

import time
import unittest
from unittest.mock import Mock, mock_open, patch

from global_constants import (
    GB_MILESTONE_THRESHOLD,
    GIGABYTE,
    MAX_SMALL_CHUNK_SIZE,
    MEGABYTE,
    TEST_CHUNK_SIZE_100MB,
    TEST_DEVICE_SIZE_100GB,
    TEST_DEVICE_SIZE_100MB,
)
from wipe_strategy import (
    AdaptiveStrategy,
    SmallChunkStrategy,
    StandardStrategy,
    WipeStrategy,
)


class TestWipeStrategyBase(unittest.TestCase):
    """Test WipeStrategy abstract base class."""

    def test_cannot_instantiate_abstract_class(self):
        """Test that abstract base class cannot be instantiated."""
        with self.assertRaises(TypeError):
            WipeStrategy('/dev/sdb', 1000, 100)

    def test_calculate_eta_with_progress(self):
        """Test ETA calculation with progress made."""
        strategy = StandardStrategy('/dev/sdb', 1000 * MEGABYTE,
                                    100 * MEGABYTE, 0)
        strategy.written = 250 * MEGABYTE
        strategy.start_time = time.time() - 100

        eta_str = strategy._calculate_eta()

        self.assertIsInstance(eta_str, str)
        self.assertRegex(eta_str, r'\d{2}:\d{2}:\d{2}')

    def test_calculate_eta_no_progress(self):
        """Test ETA calculation with no progress."""
        strategy = StandardStrategy('/dev/sdb', 1000 * MEGABYTE,
                                    100 * MEGABYTE, 0)
        strategy.written = 0

        eta_str = strategy._calculate_eta()

        self.assertEqual(eta_str, "??:??:??")

    def test_format_progress_bar_empty(self):
        """Test progress bar formatting at 0% progress."""
        strategy = StandardStrategy('/dev/sdb', 1000 * MEGABYTE,
                                    100 * MEGABYTE, 0)
        strategy.written = 0

        bar = strategy._format_progress_bar(10)

        self.assertEqual(bar, '░' * 10)

    def test_format_progress_bar_half(self):
        """Test progress bar formatting at 50% progress."""
        strategy = StandardStrategy('/dev/sdb', 1000 * MEGABYTE,
                                    100 * MEGABYTE, 0)
        strategy.written = 500 * MEGABYTE

        bar = strategy._format_progress_bar(10)

        self.assertEqual(bar, '█' * 5 + '░' * 5)

    def test_format_progress_bar_full(self):
        """Test progress bar formatting at 100% progress."""
        strategy = StandardStrategy('/dev/sdb', 1000 * MEGABYTE,
                                    100 * MEGABYTE, 0)
        strategy.written = 1000 * MEGABYTE

        bar = strategy._format_progress_bar(10)

        self.assertEqual(bar, '█' * 10)

    def test_progress_callback_called(self):
        """Test that progress callback is called when set."""
        callback = Mock()
        strategy = StandardStrategy('/dev/sdb', 1000 * MEGABYTE,
                                    100 * MEGABYTE, 0,
                                    progress_callback=callback)
        strategy.written = 100 * MEGABYTE

        strategy._save_progress_checkpoint()

        callback.assert_called_once_with(100 * MEGABYTE, 1000 * MEGABYTE,
                                         100 * MEGABYTE)

    def test_progress_callback_not_called_when_none(self):
        """Test that missing callback doesn't cause error."""
        strategy = StandardStrategy('/dev/sdb', 1000 * MEGABYTE,
                                    100 * MEGABYTE, 0)

        strategy._save_progress_checkpoint()


class TestStandardStrategy(unittest.TestCase):
    """Test StandardStrategy class."""

    def test_init(self):
        """Test StandardStrategy initialization."""
        strategy = StandardStrategy('/dev/sdb', TEST_DEVICE_SIZE_100MB,
                                    TEST_CHUNK_SIZE_100MB, 0)

        self.assertEqual(strategy.device_path, '/dev/sdb')
        self.assertEqual(strategy.total_size, TEST_DEVICE_SIZE_100MB)
        self.assertEqual(strategy.chunk_size, TEST_CHUNK_SIZE_100MB)
        self.assertEqual(strategy.written, 0)

    def test_init_with_resume_position(self):
        """Test StandardStrategy initialization with resume."""
        start_pos = 50 * MEGABYTE
        strategy = StandardStrategy('/dev/sdb', TEST_DEVICE_SIZE_100MB,
                                    TEST_CHUNK_SIZE_100MB, start_pos)

        self.assertEqual(strategy.written, start_pos)

    def test_get_strategy_name(self):
        """Test StandardStrategy name."""
        strategy = StandardStrategy('/dev/sdb', TEST_DEVICE_SIZE_100MB,
                                    TEST_CHUNK_SIZE_100MB, 0)

        self.assertEqual(strategy.get_strategy_name(), "standard")

    @patch('builtins.open', new_callable=mock_open)
    @patch('os.fsync')
    @patch('time.time')
    def test_wipe_small_device(self, mock_time, mock_fsync, mock_file):
        """Test wiping a small device."""
        device_size = 10 * MEGABYTE
        chunk_size = 5 * MEGABYTE

        mock_time.return_value = 1000.0
        mock_file_handle = mock_file.return_value.__enter__.return_value
        mock_file_handle.fileno.return_value = 3

        strategy = StandardStrategy('/dev/sdb', device_size, chunk_size, 0)

        result = strategy.wipe()

        self.assertTrue(result)
        self.assertEqual(strategy.written, device_size)
        self.assertEqual(mock_file.call_count, 2)

    @patch('builtins.open', new_callable=mock_open)
    @patch('os.fsync')
    @patch('time.time')
    def test_wipe_respects_chunk_size(self, mock_time, mock_fsync, mock_file):
        """Test that wipe uses correct chunk sizes."""
        device_size = 25 * MEGABYTE
        chunk_size = 10 * MEGABYTE

        mock_time.return_value = 1000.0
        mock_file_handle = mock_file.return_value.__enter__.return_value
        mock_file_handle.fileno.return_value = 3

        written_chunks = []

        def capture_write(data):
            written_chunks.append(len(data))

        mock_file_handle.write = capture_write

        strategy = StandardStrategy('/dev/sdb', device_size, chunk_size, 0)
        strategy.wipe()

        self.assertEqual(len(written_chunks), 3)
        self.assertEqual(written_chunks[0], 10 * MEGABYTE)
        self.assertEqual(written_chunks[1], 10 * MEGABYTE)
        self.assertEqual(written_chunks[2], 5 * MEGABYTE)

    @patch('builtins.open', new_callable=mock_open)
    @patch('os.fsync')
    @patch('time.time')
    def test_wipe_with_progress_callback(self, mock_time, mock_fsync,
                                         mock_file):
        """Test wipe calls progress callback at milestones."""
        device_size = 3 * GIGABYTE
        chunk_size = GB_MILESTONE_THRESHOLD

        mock_time.return_value = 1000.0
        mock_file_handle = mock_file.return_value.__enter__.return_value
        mock_file_handle.fileno.return_value = 3

        callback = Mock()
        strategy = StandardStrategy('/dev/sdb', device_size, chunk_size, 0,
                                    progress_callback=callback)

        strategy.wipe()

        self.assertEqual(callback.call_count, 3)

    @patch('builtins.open', new_callable=mock_open)
    @patch('os.fsync')
    @patch('time.time')
    def test_wipe_resume_from_position(self, mock_time, mock_fsync,
                                       mock_file):
        """Test wiping can resume from a position."""
        device_size = 20 * MEGABYTE
        chunk_size = 10 * MEGABYTE
        start_pos = 10 * MEGABYTE

        mock_time.return_value = 1000.0
        mock_file_handle = mock_file.return_value.__enter__.return_value
        mock_file_handle.fileno.return_value = 3

        strategy = StandardStrategy('/dev/sdb', device_size, chunk_size,
                                    start_pos)

        strategy.wipe()

        self.assertEqual(strategy.written, device_size)


class TestSmallChunkStrategy(unittest.TestCase):
    """Test SmallChunkStrategy class."""

    def test_init_limits_chunk_size(self):
        """Test SmallChunkStrategy limits chunk size to 10MB."""
        large_chunk = 100 * MEGABYTE
        strategy = SmallChunkStrategy('/dev/sdb', TEST_DEVICE_SIZE_100MB,
                                      large_chunk, 0)

        self.assertEqual(strategy.chunk_size, MAX_SMALL_CHUNK_SIZE)

    def test_init_preserves_small_chunk_size(self):
        """Test SmallChunkStrategy preserves small chunk sizes."""
        small_chunk = 5 * MEGABYTE
        strategy = SmallChunkStrategy('/dev/sdb', TEST_DEVICE_SIZE_100MB,
                                      small_chunk, 0)

        self.assertEqual(strategy.chunk_size, small_chunk)

    def test_get_strategy_name(self):
        """Test SmallChunkStrategy name."""
        strategy = SmallChunkStrategy('/dev/sdb', TEST_DEVICE_SIZE_100MB,
                                      TEST_CHUNK_SIZE_100MB, 0)

        self.assertEqual(strategy.get_strategy_name(), "small_chunk")

    @patch('builtins.open', new_callable=mock_open)
    @patch('os.fsync')
    @patch('time.time')
    def test_wipe_uses_small_chunks(self, mock_time, mock_fsync, mock_file):
        """Test SmallChunkStrategy uses limited chunk sizes."""
        device_size = 30 * MEGABYTE
        requested_chunk = 100 * MEGABYTE

        mock_time.return_value = 1000.0
        mock_file_handle = mock_file.return_value.__enter__.return_value
        mock_file_handle.fileno.return_value = 3

        written_chunks = []

        def capture_write(data):
            written_chunks.append(len(data))

        mock_file_handle.write = capture_write

        strategy = SmallChunkStrategy('/dev/sdb', device_size,
                                      requested_chunk, 0)
        strategy.wipe()

        for chunk_size in written_chunks[:-1]:
            self.assertLessEqual(chunk_size, MAX_SMALL_CHUNK_SIZE)


class TestAdaptiveStrategy(unittest.TestCase):
    """Test AdaptiveStrategy class."""

    def test_init(self):
        """Test AdaptiveStrategy initialization."""
        strategy = AdaptiveStrategy('/dev/sdb', TEST_DEVICE_SIZE_100GB,
                                    TEST_CHUNK_SIZE_100MB, 0)

        self.assertEqual(strategy.device_path, '/dev/sdb')
        self.assertEqual(strategy.total_size, TEST_DEVICE_SIZE_100GB)
        self.assertEqual(strategy.chunk_size, TEST_CHUNK_SIZE_100MB)
        self.assertEqual(len(strategy._speed_samples), 0)

    def test_get_strategy_name(self):
        """Test AdaptiveStrategy name."""
        strategy = AdaptiveStrategy('/dev/sdb', TEST_DEVICE_SIZE_100GB,
                                    TEST_CHUNK_SIZE_100MB, 0)

        self.assertEqual(strategy.get_strategy_name(), "adaptive_chunk")

    def test_calculate_adaptive_chunk_beginning(self):
        """Test adaptive chunk size at beginning (0-10%)."""
        strategy = AdaptiveStrategy('/dev/sdb', TEST_DEVICE_SIZE_100GB,
                                    TEST_CHUNK_SIZE_100MB, 0)

        strategy.written = 5 * GIGABYTE

        chunk_size = strategy._calculate_adaptive_chunk_size()

        expected = int(TEST_CHUNK_SIZE_100MB * 2)
        self.assertEqual(chunk_size, expected)
        self.assertIsInstance(chunk_size, int)

    def test_calculate_adaptive_chunk_end(self):
        """Test adaptive chunk size at end (90-100%)."""
        strategy = AdaptiveStrategy('/dev/sdb', TEST_DEVICE_SIZE_100GB,
                                    TEST_CHUNK_SIZE_100MB, 0)

        strategy.written = 95 * GIGABYTE

        chunk_size = strategy._calculate_adaptive_chunk_size()

        expected = int(TEST_CHUNK_SIZE_100MB * 0.5)
        self.assertEqual(chunk_size, expected)
        self.assertIsInstance(chunk_size, int)

    def test_calculate_adaptive_chunk_middle_no_samples(self):
        """Test adaptive chunk size in middle with no speed samples."""
        strategy = AdaptiveStrategy('/dev/sdb', TEST_DEVICE_SIZE_100GB,
                                    TEST_CHUNK_SIZE_100MB, 0)

        strategy.written = 50 * GIGABYTE

        chunk_size = strategy._calculate_adaptive_chunk_size()

        self.assertEqual(chunk_size, TEST_CHUNK_SIZE_100MB)
        self.assertIsInstance(chunk_size, int)

    def test_calculate_adaptive_chunk_middle_slow_speed(self):
        """Test adaptive chunk size with slow speed samples."""
        strategy = AdaptiveStrategy('/dev/sdb', TEST_DEVICE_SIZE_100GB,
                                    TEST_CHUNK_SIZE_100MB, 0)

        strategy.written = 50 * GIGABYTE
        strategy._speed_samples = [30, 35, 40, 35, 30]

        chunk_size = strategy._calculate_adaptive_chunk_size()

        expected = int(TEST_CHUNK_SIZE_100MB * 0.5)
        self.assertEqual(chunk_size, expected)
        self.assertIsInstance(chunk_size, int)

    def test_calculate_adaptive_chunk_middle_fast_speed(self):
        """Test adaptive chunk size with fast speed samples."""
        strategy = AdaptiveStrategy('/dev/sdb', TEST_DEVICE_SIZE_100GB,
                                    TEST_CHUNK_SIZE_100MB, 0)

        strategy.written = 50 * GIGABYTE
        strategy._speed_samples = [250, 260, 255, 265, 270]

        chunk_size = strategy._calculate_adaptive_chunk_size()

        expected = int(TEST_CHUNK_SIZE_100MB * 1.5)
        self.assertEqual(chunk_size, expected)
        self.assertIsInstance(chunk_size, int)

    def test_calculate_adaptive_chunk_middle_medium_speed(self):
        """Test adaptive chunk size with medium speed samples."""
        strategy = AdaptiveStrategy('/dev/sdb', TEST_DEVICE_SIZE_100GB,
                                    TEST_CHUNK_SIZE_100MB, 0)

        strategy.written = 50 * GIGABYTE
        strategy._speed_samples = [100, 110, 105, 115, 120]

        chunk_size = strategy._calculate_adaptive_chunk_size()

        self.assertEqual(chunk_size, TEST_CHUNK_SIZE_100MB)
        self.assertIsInstance(chunk_size, int)

    def test_adaptive_chunk_respects_min_size(self):
        """Test adaptive chunk size respects minimum of 1MB."""
        strategy = AdaptiveStrategy('/dev/sdb', 10 * MEGABYTE, MEGABYTE, 0)

        strategy.written = 9 * MEGABYTE
        strategy._speed_samples = [10, 15, 12]

        chunk_size = strategy._calculate_adaptive_chunk_size()

        self.assertGreaterEqual(chunk_size, MEGABYTE)
        self.assertIsInstance(chunk_size, int)

    def test_adaptive_chunk_respects_remaining_size(self):
        """Test adaptive chunk doesn't exceed remaining device size."""
        strategy = AdaptiveStrategy('/dev/sdb', TEST_DEVICE_SIZE_100MB,
                                    50 * MEGABYTE, 0)

        strategy.written = 90 * MEGABYTE

        chunk_size = strategy._calculate_adaptive_chunk_size()

        self.assertLessEqual(chunk_size, 10 * MEGABYTE)
        self.assertIsInstance(chunk_size, int)

    def test_adaptive_chunk_always_returns_int(self):
        """Test adaptive chunk size always returns integers."""
        strategy = AdaptiveStrategy('/dev/sdb', TEST_DEVICE_SIZE_100GB,
                                    TEST_CHUNK_SIZE_100MB, 0)

        test_positions = [
            0,
            5 * GIGABYTE,
            25 * GIGABYTE,
            50 * GIGABYTE,
            75 * GIGABYTE,
            95 * GIGABYTE
        ]

        for position in test_positions:
            strategy.written = position
            strategy._speed_samples = [50, 100, 150, 200, 250]

            chunk_size = strategy._calculate_adaptive_chunk_size()

            with self.subTest(position=position):
                self.assertIsInstance(chunk_size, int)

    @patch('builtins.open', new_callable=mock_open)
    @patch('os.fsync')
    @patch('time.time')
    def test_wipe_tracks_speed_samples(self, mock_time, mock_fsync,
                                       mock_file):
        """Test that adaptive wipe tracks speed samples."""
        device_size = 30 * MEGABYTE
        chunk_size = 10 * MEGABYTE

        time_values = [1000.0 + i * 0.1 for i in range(100)]
        mock_time.side_effect = time_values

        mock_file_handle = mock_file.return_value.__enter__.return_value
        mock_file_handle.fileno.return_value = 3

        strategy = AdaptiveStrategy('/dev/sdb', device_size, chunk_size, 0)
        strategy.wipe()

        self.assertGreater(len(strategy._speed_samples), 0)

    @patch('builtins.open', new_callable=mock_open)
    @patch('os.fsync')
    @patch('time.time')
    def test_wipe_completes_successfully(self, mock_time, mock_fsync,
                                         mock_file):
        """Test that adaptive wipe completes successfully."""
        device_size = 10 * MEGABYTE
        chunk_size = 5 * MEGABYTE

        mock_time.return_value = 1000.0
        mock_file_handle = mock_file.return_value.__enter__.return_value
        mock_file_handle.fileno.return_value = 3

        strategy = AdaptiveStrategy('/dev/sdb', device_size, chunk_size, 0)

        result = strategy.wipe()

        self.assertTrue(result)
        self.assertEqual(strategy.written, device_size)


class TestStrategyIntegration(unittest.TestCase):
    """Integration tests for strategy selection and usage."""

    def test_all_strategies_implement_interface(self):
        """Test that all strategies implement required interface."""
        strategies = [
            StandardStrategy('/dev/sdb', 1000, 100, 0),
            SmallChunkStrategy('/dev/sdb', 1000, 100, 0),
            AdaptiveStrategy('/dev/sdb', 1000, 100, 0)
        ]

        for strategy in strategies:
            with self.subTest(strategy=strategy.__class__.__name__):
                self.assertTrue(hasattr(strategy, 'wipe'))
                self.assertTrue(hasattr(strategy, 'get_strategy_name'))
                self.assertTrue(callable(strategy.wipe))
                self.assertTrue(callable(strategy.get_strategy_name))

    def test_all_strategies_have_unique_names(self):
        """Test that all strategies have unique names."""
        strategies = [
            StandardStrategy('/dev/sdb', 1000, 100, 0),
            SmallChunkStrategy('/dev/sdb', 1000, 100, 0),
            AdaptiveStrategy('/dev/sdb', 1000, 100, 0)
        ]

        names = [s.get_strategy_name() for s in strategies]

        self.assertEqual(len(names), len(set(names)))

    @patch('builtins.open', new_callable=mock_open)
    @patch('os.fsync')
    @patch('time.time')
    def test_strategies_work_with_callbacks(self, mock_time, mock_fsync,
                                            mock_file):
        """Test all strategies work with progress callbacks."""
        mock_time.return_value = 1000.0
        mock_file_handle = mock_file.return_value.__enter__.return_value
        mock_file_handle.fileno.return_value = 3

        callback = Mock()
        device_size = 3 * GIGABYTE
        chunk_size = GIGABYTE

        strategies = [
            StandardStrategy('/dev/sdb', device_size, chunk_size, 0,
                             progress_callback=callback),
            SmallChunkStrategy('/dev/sdb', device_size, chunk_size, 0,
                               progress_callback=callback),
            AdaptiveStrategy('/dev/sdb', device_size, chunk_size, 0,
                             progress_callback=callback)
        ]

        for strategy in strategies:
            callback.reset_mock()
            with self.subTest(strategy=strategy.__class__.__name__):
                strategy.wipe()
                self.assertGreater(callback.call_count, 0)

    @patch('builtins.open', new_callable=mock_open)
    @patch('os.fsync')
    @patch('time.time')
    def test_strategies_handle_resume(self, mock_time, mock_fsync,
                                      mock_file):
        """Test all strategies handle resume correctly."""
        mock_time.return_value = 1000.0
        mock_file_handle = mock_file.return_value.__enter__.return_value
        mock_file_handle.fileno.return_value = 3

        device_size = 20 * MEGABYTE
        chunk_size = 10 * MEGABYTE
        resume_position = 10 * MEGABYTE

        strategies = [
            StandardStrategy('/dev/sdb', device_size, chunk_size,
                             resume_position),
            SmallChunkStrategy('/dev/sdb', device_size, chunk_size,
                               resume_position),
            AdaptiveStrategy('/dev/sdb', device_size, chunk_size,
                             resume_position)
        ]

        for strategy in strategies:
            with self.subTest(strategy=strategy.__class__.__name__):
                self.assertEqual(strategy.written, resume_position)
                strategy.wipe()
                self.assertEqual(strategy.written, device_size)


if __name__ == '__main__':
    test_suite = unittest.TestSuite()

    test_classes = [
        TestWipeStrategyBase,
        TestStandardStrategy,
        TestSmallChunkStrategy,
        TestAdaptiveStrategy,
        TestStrategyIntegration,
    ]

    for test_class in test_classes:
        tests = unittest.TestLoader().loadTestsFromTestCase(test_class)
        test_suite.addTests(tests)

    runner = unittest.TextTestRunner(verbosity=2)
    result = runner.run(test_suite)

    import sys
    sys.exit(0 if result.wasSuccessful() else 1)
