#!/usr/bin/env python3
"""Unit tests for WipeStrategyFactory."""

import unittest
from wipe_strategy_factory import WipeStrategyFactory
from wipe_strategy import (StandardStrategy, AdaptiveStrategy,
                           SmallChunkStrategy, OverrideStrategy)


class TestWipeStrategyFactory(unittest.TestCase):
    """Test WipeStrategyFactory."""

    def test_factory_creates_standard_strategy(self):
        """Test factory creates StandardStrategy."""
        strategy = WipeStrategyFactory.create_strategy(
            'standard', '/dev/sdb', 1000000, 1024)
        self.assertIsInstance(strategy, StandardStrategy)

    def test_factory_creates_adaptive_strategy(self):
        """Test factory creates AdaptiveStrategy."""
        strategy = WipeStrategyFactory.create_strategy(
            'adaptive_chunk', '/dev/sdb', 1000000, 1024)
        self.assertIsInstance(strategy, AdaptiveStrategy)

    def test_factory_creates_small_chunk_strategy(self):
        """Test factory creates SmallChunkStrategy."""
        strategy = WipeStrategyFactory.create_strategy(
            'small_chunk', '/dev/sdb', 1000000, 1024)
        self.assertIsInstance(strategy, SmallChunkStrategy)

    def test_factory_creates_override_strategy(self):
        """Test factory creates OverrideStrategy."""
        strategy = WipeStrategyFactory.create_strategy(
            'buffer_override', '/dev/sdb', 1000000, 1024)
        self.assertIsInstance(strategy, OverrideStrategy)

    def test_factory_raises_on_unknown_algorithm(self):
        """Test factory raises ValueError on unknown algorithm."""
        with self.assertRaises(ValueError) as ctx:
            WipeStrategyFactory.create_strategy(
                'unknown_algo', '/dev/sdb', 1000000, 1024)
        self.assertIn('Unknown algorithm', str(ctx.exception))
        self.assertIn('unknown_algo', str(ctx.exception))

    def test_factory_get_available_algorithms(self):
        """Test factory returns available algorithms."""
        algos = WipeStrategyFactory.get_available_algorithms()
        self.assertIn('standard', algos)
        self.assertIn('adaptive_chunk', algos)
        self.assertIn('small_chunk', algos)
        self.assertIn('buffer_override', algos)
        self.assertEqual(len(algos), 4)

    def test_factory_register_new_strategy(self):
        """Test factory can register new strategies."""
        class CustomStrategy(StandardStrategy):
            pass

        WipeStrategyFactory.register_strategy('custom', CustomStrategy)
        strategy = WipeStrategyFactory.create_strategy(
            'custom', '/dev/sdb', 1000000, 1024)
        self.assertIsInstance(strategy, CustomStrategy)

        # Clean up
        del WipeStrategyFactory._strategies['custom']


if __name__ == '__main__':
    unittest.main()
