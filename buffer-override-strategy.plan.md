# Buffer Size Override with Dedicated Strategy + Factory Pattern

## Design Principle - Revised Architecture

**When user specifies `-b` / `--force-buffer-size`: Use dedicated `OverrideStrategy`**

- **User specified `-b 1G`**: Skip algorithm selection, use `OverrideStrategy` with exactly 1GB
- **User didn't specify `-b`**: Do pretest, smart algorithm selection, use recommended defaults
- **Key insight**: Override is a separate concern from algorithm selection
- **Factory pattern**: Clean strategy creation with validation and extensibility

This keeps existing algorithms pure and puts "force buffer" logic in a dedicated class.

## New Architecture

### 1. Progress File Versioning Module

**New File: `src/progress_file_version.py`**

```python
#!/usr/bin/env python3
"""
Progress file version management for wipeit.
"""

class ProgressFileVersion:
    """
    Manages progress file versioning and format migration.

    Version history:
    - v1: Original (device, written, total_size, progress_percent, timestamp)
    - v2: Added device_id, chunk_size, algorithm
    """

    CURRENT_VERSION = 2

    @classmethod
    def migrate_progress_data(cls, progress_data):
        """Migrate v1 → v2: add device_id, chunk_size, algorithm fields."""
        version = progress_data.get('version', 1)

        if version == 1:
            progress_data['version'] = 2
            progress_data.setdefault('device_id', None)
            progress_data.setdefault('chunk_size', None)
            progress_data.setdefault('algorithm', None)  # NEW!
            return progress_data, True, "Upgraded from v1 to v2"

        return progress_data, False, None

    @classmethod
    def validate_progress_data(cls, progress_data):
        """Validate v2 includes required fields."""
        version = progress_data.get('version', 1)

        if version >= 2:
            for field in ['device_id', 'chunk_size', 'algorithm']:
                if field not in progress_data:
                    return False, f"Missing v2 field: {field}"

        return True, None
```

**New File: `src/test_progress_file_version.py`** - 10 comprehensive tests

### 2. The OverrideStrategy Class

**File: `src/wipe_strategy.py`**

```python
class OverrideStrategy(StandardStrategy):
    """
    Buffer override strategy - forces user-specified buffer size.

    Used when user explicitly specifies buffer size with -b/--force-buffer-size.
    """

    def get_strategy_name(self):
        return "buffer_override"
```

### 3. The WipeStrategyFactory Class (Factory Pattern)

**New File: `src/wipe_strategy_factory.py`**

```python
#!/usr/bin/env python3
"""Factory for creating WipeStrategy instances."""

from wipe_strategy import (StandardStrategy, AdaptiveStrategy,
                          SmallChunkStrategy, OverrideStrategy)


class WipeStrategyFactory:
    """
    Factory for creating wipe strategy instances.
    Implements Factory pattern for clean strategy creation.
    """

    # Strategy registry
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
        """Create appropriate WipeStrategy instance."""
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
        """Return list of available algorithm names."""
        return list(cls._strategies.keys())

    @classmethod
    def register_strategy(cls, name, strategy_class):
        """Register a new strategy (for extensibility)."""
        cls._strategies[name] = strategy_class
```

**New File: `src/test_wipe_strategy_factory.py`** - 7 factory tests

### 4. Updated Flow in wipeit.py

**File: `src/wipeit.py`**

#### Step 1: Use ProgressFileVersion for save/load

```python
from progress_file_version import ProgressFileVersion

def save_progress(device, written, size, pretest_results, chunk_size,
                  device_id, algorithm):
    """Save progress including algorithm."""
    progress_data = {
        'device': device,
        'written': written,
        'total_size': size,
        'progress_percent': (written / size) * 100,
        'timestamp': time.time(),
        'pretest_results': pretest_results,
        'chunk_size': chunk_size,
        'device_id': device_id,
        'algorithm': algorithm  # NEW!
    }
    progress_data = ProgressFileVersion.add_version_to_data(progress_data)
    # ... save to file

def load_progress(device):
    """Load progress with version compatibility."""
    # ... load from file
    progress_data, was_migrated, warning = \
        ProgressFileVersion.migrate_progress_data(progress_data)
    if warning:
        print(f"⚠️  {warning}")
    return progress_data
```

#### Step 2: Update handle_resume() to return algorithm

```python
def handle_resume(device):
    """
    Returns: (written, pretest_results, saved_chunk_size, saved_algorithm)
    """
    progress_data = load_progress(device)
    if not progress_data:
        return 0, None, None, None

    saved_algorithm = progress_data.get('algorithm')
    if saved_algorithm:
        print(f"ℹ️  Resuming with {saved_algorithm} algorithm")

    return written, pretest, saved_chunk_size, saved_algorithm
```

#### Step 3: Track if user explicitly specified buffer

```python
def main():
    args = setup_argument_parser().parse_args()

    user_specified_buffer = ('-b' in sys.argv or
                            '--buffer-size' in sys.argv or
                            '--force-buffer-size' in sys.argv)
```

#### Step 4: Update wipe_device() to use saved algorithm

```python
def wipe_device(device, chunk_size=DEFAULT_CHUNK_SIZE, resume=False,
                skip_pretest=False, force_buffer=False):
    """
    Args:
        force_buffer: If True, user explicitly set buffer
    """

    if resume:
        written, pretest, saved_chunk_size, saved_algorithm = \
            handle_resume(device)

        if saved_algorithm:
            # Perfect consistency - use saved algorithm
            algorithm = saved_algorithm
            chunk_size = saved_chunk_size
            print("   (continuing with saved algorithm)")
        elif saved_chunk_size:
            # Old v1 file: treat as override
            chunk_size = saved_chunk_size
            force_buffer = True

    # If user forced buffer, skip pretest
    if not resume or not saved_algorithm:
        if force_buffer:
            print(f"Using user-specified buffer: {chunk_size / MEGABYTE:.0f} MB")
            algorithm = "buffer_override"
        elif disk_type == "HDD" and not skip_pretest:
            pretest_results = handle_hdd_pretest(...)
            algorithm = determine_algorithm(pretest_results)
        else:
            algorithm = "standard"
```

#### Step 5: Replace create_wipe_strategy() with Factory

```python
from wipe_strategy_factory import WipeStrategyFactory

# Remove old create_wipe_strategy() function
# Use factory instead:

strategy = WipeStrategyFactory.create_strategy(
    algorithm=algorithm,
    device_path=device,
    total_size=size,
    chunk_size=chunk_size,
    start_position=written,
    pretest_results=pretest_results,
    progress_callback=save_callback
)
```

### 5. Add --force-buffer-size alias

```python
parser.add_argument(
    '-b', '--buffer-size', '--force-buffer-size',
    default='100M',
    help='Buffer size (default: 100M). When specified, bypasses algorithm '
         'selection and uses this exact buffer size.')
```

### 6. Buffer Size Display

**File: `src/wipe_strategy.py`**

```python
def _display_progress(self, current_speed=None, current_chunk=None):
    """Display progress with buffer size."""
    # ... existing code ...

    # Add buffer size display
    if current_chunk and current_chunk != self.chunk_size:
        buffer_str = f" Buffer: {current_chunk / MEGABYTE:.0f}MB (adaptive)"
    else:
        buffer_str = f" Buffer: {self.chunk_size / MEGABYTE:.0f}MB"

    print(f"\r• Progress: {progress_percent:.1f}% |{bar}| "
          f"{self.written / GIGABYTE:.1f}GB/"
          f"{self.total_size / GIGABYTE:.1f}GB ETA: {eta_str}"
          f"{speed_str}{buffer_str}", end='', flush=True)
```

## Unit Tests

### New Test Files

1. **`src/test_progress_file_version.py`** (10 tests)
   - Version migration
   - Validation
   - Backwards compatibility

2. **`src/test_wipe_strategy_factory.py`** (7 tests)
   - Factory creates all strategy types
   - Unknown algorithm raises ValueError
   - get_available_algorithms()
   - register_strategy()

3. **`src/test_wipeit.py`** - New class: `TestBufferSizeOverride`
   - Override strategy tests
   - Buffer override flow tests
   - Resume with algorithm tests
   - Progress display tests

### Update Existing Tests

- `test_handle_resume_*`: Return 4-tuple instead of 2-tuple
- `test_wipe_device_*`: Add algorithm parameter
- `test_save_progress_*`: Include algorithm in saved data

## Implementation Order

1. Create `src/progress_file_version.py`
2. Create `src/test_progress_file_version.py`
3. Update `save_progress()` to include algorithm
4. Update `load_progress()` with ProgressFileVersion
5. Add `OverrideStrategy` to `wipe_strategy.py`
6. Create `src/wipe_strategy_factory.py`
7. Create `src/test_wipe_strategy_factory.py`
8. Update `handle_resume()` to return 4-tuple
9. Add `--force-buffer-size` alias
10. Detect user-specified buffer in `main()`
11. Update `wipe_device()` signature and logic
12. Replace `create_wipe_strategy()` with Factory
13. Update progress callback to pass algorithm
14. Add buffer display to `_display_progress()`
15. Update `AdaptiveStrategy.wipe()` for chunk display
16. Write `TestBufferSizeOverride` tests
17. Update existing tests for new signatures
18. Update documentation

## Benefits

✅ **Factory pattern**: Encapsulated strategy creation with validation
✅ **Cleaner separation of concerns**: Override logic isolated
✅ **No modifications to existing algorithms**: They remain pure
✅ **Clear semantics**: `-b` means "I know what I want"
✅ **Skip unnecessary work**: No pretest when forcing buffer or resuming
✅ **Easier to test**: Factory and override behavior isolated
✅ **Progress file versioning**: Safe evolution
✅ **Perfect resume consistency**: Preserves exact algorithm and buffer
✅ **Extensible**: Easy to add strategies via registration
✅ **Backwards compatible**: v1 files work seamlessly

## Expected User Experience

**User forces buffer:**
```bash
$ sudo wipeit -b 1G /dev/sdb
Using user-specified buffer: 1024 MB
• Progress: 15% |████░░░░| 19GB/128GB ETA: 01:23:45 Speed: 45MB/s Buffer: 1024MB
<Ctrl+C>

$ sudo wipeit --resume
ℹ️  Resuming with buffer_override algorithm
   (continuing with saved algorithm)
• Progress: 15% |████░░░░| 19GB/128GB ETA: 01:23:45 Speed: 45MB/s Buffer: 1024MB
```

**Smart selection:**
```bash
$ sudo wipeit /dev/sdb
Running HDD pretest...
Using small_chunk algorithm
• Progress: 15% |████░░░░| 19GB/128GB ETA: 01:23:45 Speed: 45MB/s Buffer: 10MB
<Ctrl+C>

$ sudo wipeit --resume
ℹ️  Resuming with small_chunk algorithm
   (continuing with saved algorithm)
• Progress: 15% |████░░░░| 19GB/128GB ETA: 01:23:45 Speed: 45MB/s Buffer: 10MB
```

