#!/usr/bin/env python3
"""
Factory for creating WipeStrategy instances.

Implements the Factory pattern to encapsulate strategy creation logic.
"""

from wipe_strategy import (StandardStrategy, AdaptiveStrategy,
                           SmallChunkStrategy, OverrideStrategy)


class WipeStrategyFactory:
    """
    Factory for creating wipe strategy instances.

    Encapsulates the logic for selecting and instantiating
    the appropriate strategy based on algorithm type.
    """

    # Strategy registry - maps algorithm names to strategy classes
    _strategies = {
        'standard': StandardStrategy,
        'adaptive_chunk': AdaptiveStrategy,
        'small_chunk': SmallChunkStrategy,
        'buffer_override': OverrideStrategy
    }

    @classmethod
    def create_strategy(cls, algorithm, device_path, total_size, chunk_size,
                        start_position=0, pretest_results=None,
                        progress_callback=None):
        """
        Create appropriate WipeStrategy instance.

        Args:
            algorithm: Strategy algorithm name
            device_path: Path to block device
            total_size: Total device size in bytes
            chunk_size: Chunk size for writing
            start_position: Starting position (for resume)
            pretest_results: Optional pretest results
            progress_callback: Optional progress callback

        Returns:
            WipeStrategy instance

        Raises:
            ValueError: If algorithm is not recognized
        """
        if algorithm not in cls._strategies:
            available = list(cls._strategies.keys())
            raise ValueError(f"Unknown algorithm: {algorithm}. "
                             f"Available: {available}")

        strategy_class = cls._strategies[algorithm]
        return strategy_class(device_path, total_size, chunk_size,
                              start_position, pretest_results,
                              progress_callback)

    @classmethod
    def get_available_algorithms(cls):
        """
        Return list of available algorithm names.

        Returns:
            list: Available algorithm names
        """
        return list(cls._strategies.keys())

    @classmethod
    def register_strategy(cls, name, strategy_class):
        """
        Register a new strategy (for extensibility).

        Args:
            name: Algorithm name
            strategy_class: Strategy class to register
        """
        cls._strategies[name] = strategy_class
