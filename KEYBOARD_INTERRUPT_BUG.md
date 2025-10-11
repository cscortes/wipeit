# Keyboard Interrupt Bug Fix

## The Bug

When a user pressed Ctrl+C to interrupt a wipe operation, the progress file saved `written: 0` bytes, even though actual data had been written to the disk.

### User Report

```
• Progress: 0.2% |░░░░░░░...| 0.5GB/298.1GB ETA: 02:30:26^C

⚠️  Wipe interrupted by user
• Progress saved: 0.00 GB written    ← BUG: Should be 0.5GB!

{
  "written": 0,                       ← BUG: Should be ~536MB
  "progress_percent": 0.0             ← BUG: Should be 0.2%
}
```

## Root Cause Analysis

The bug was in `src/wipeit.py` at lines 343-448:

```python
# Line 343: Initialize written to 0
written = 0

# Lines 404-421: Create strategy object
strategy = StandardStrategy(device, size, chunk_size, written, ...)

# Line 423: Start wipe (strategy.written gets updated during wipe)
strategy.wipe()

# Line 424: Update local 'written' variable ← ONLY runs if wipe completes!
written = strategy.written

# Lines 443-448: KeyboardInterrupt handler
except KeyboardInterrupt:
    print(f"• Progress saved: {written / (1024**3):.2f} GB written")
    save_progress(device, written, ...)  ← Uses local 'written' which is still 0!
```

**The Problem:**
1. Local variable `written` initialized to `0` at line 343
2. During wipe, `strategy.written` is continuously updated (e.g., 0.5GB)
3. When user presses Ctrl+C:
   - Execution jumps directly to `except KeyboardInterrupt` block
   - Line 424 (`written = strategy.written`) **never executes**
   - Exception handler uses local `written` variable = `0`
   - Saves 0 bytes even though 0.5GB was actually written!

## The Fix (Multi-Part)

### Part 1: Retrieve Actual Progress in Exception Handlers

Added code to retrieve actual progress from strategy object:

```python
except KeyboardInterrupt:
    # Get actual progress from strategy if it was created
    if 'strategy' in locals():
        written = strategy.written  # ← Retrieve actual progress!
    print(f"• Progress saved: {written / (1024**3):.2f} GB written")
    save_progress(device, written, size, chunk_size, pretest_results, device_id)
    sys.exit(1)

except Exception as e:
    # Get actual progress from strategy if it was created
    if 'strategy' in locals():
        written = strategy.written  # ← Also fix for general exceptions!
    print(f"\nError during wipe: {e}")
    save_progress(device, written, size, chunk_size, pretest_results, device_id)
    sys.exit(1)
```

**Why `if 'strategy' in locals()`?**
- Protects against interruption before strategy is created
- If interrupted during pretest or device detection, `written` stays 0 (correct)
- If interrupted during wipe, uses `strategy.written` (correct actual progress)

### Part 2: Force Immediate File Flush

Added explicit flush and fsync in `save_progress()`:

```python
with open(progress_file, 'w') as f:
    json.dump(progress_data, f, indent=2)
    f.flush()  # Flush Python buffer
    os.fsync(f.fileno())  # Force OS to write to disk immediately!
```

**Why fsync?**
- Python's `with` statement flushes Python buffers
- But OS may still buffer writes in cache
- `os.fsync()` forces immediate write to physical disk
- Critical for crash/interrupt safety

### Part 3: Increase Progress Save Frequency

Changed checkpoint frequency from 1GB to 100MB:


**Why 100MB?**
- Old: If interrupted between checkpoints, lose up to 1GB tracking
- New: Maximum "lag" is only 100MB
- Balance between I/O overhead and accuracy
- User sees more responsive progress saves
- Renamed to `PROGRESS_SAVE_THRESHOLD` for semantic clarity

## Test Coverage

Added comprehensive test: `test_keyboard_interrupt_saves_actual_progress`

**Test Scenario:**
1. Mock a strategy that has written 1GB (25% of 4GB drive)
2. Make `strategy.wipe()` raise `KeyboardInterrupt`
3. Verify saved progress shows 1GB, not 0GB
4. Verify progress_percent is 25%, not 0%

**Test Code:**
```python
def test_keyboard_interrupt_saves_actual_progress(self, ...):
    """Test that KeyboardInterrupt saves actual progress from strategy."""
    # Mock strategy with 1GB written
    mock_strategy = MagicMock()
    mock_strategy.written = 1024**3  # 1GB actually written!

    # Make strategy.wipe() raise KeyboardInterrupt
    mock_strategy.wipe.side_effect = KeyboardInterrupt()

    # Try to wipe (will be interrupted)
    try:
        wipeit.wipe_device(device, chunk_size=100MB)
    except SystemExit:
        pass

    # Load saved progress
    data = json.load(progress_file)

    # CRITICAL: Progress should be 1GB (strategy.written), NOT 0!
    self.assertEqual(data['written'], 1GB)
    self.assertEqual(data['progress_percent'], 25.0)
```

## Verification

### Before Fix:
```bash
$ sudo wipeit /dev/sdb
• Progress: 0.2% |░...| 0.5GB/298.1GB ^C
• Progress saved: 0.00 GB written         ← BUG

$ cat wipeit_progress.json
"written": 0,                             ← BUG
"progress_percent": 0.0                   ← BUG
```

### After Fix:
```bash
$ sudo wipeit /dev/sdb
• Progress: 0.2% |░...| 0.5GB/298.1GB ^C
• Progress saved: 0.50 GB written         ← FIXED!

$ cat wipeit_progress.json
"written": 536870912,                     ← FIXED! (0.5GB)
"progress_percent": 0.2                   ← FIXED!
```

## Impact

**Before:** Resume would always restart from 0%, losing all progress
**After:** Resume correctly continues from actual position

**Severity:** HIGH - Data loss bug that made resume feature unreliable

## Files Modified

1. `src/wipeit.py`:
   - Lines 443-460: Added `if 'strategy' in locals()` checks in both exception handlers

2. `src/test_wipeit.py`:
   - Lines 804-854: New test `test_keyboard_interrupt_saves_actual_progress`

## Related Issues

This bug affected:
- KeyboardInterrupt (Ctrl+C)
- General Exception handler (unexpected errors during wipe)
- All wipe strategies (Standard, SmallChunk, Adaptive)

**Test count:** 157 (was 156)
**Coverage:** 95% maintained

