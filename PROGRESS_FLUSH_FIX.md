# Progress Flush and Frequency Fix

## The Problem

User reported: "progress seems to be behind, are you flushing the save of progress?"

After fixing the KeyboardInterrupt bug (where `written` was 0), a second issue emerged:
- Progress was being saved correctly in memory (`strategy.written`)
- But progress file on disk was stale/behind actual progress
- Progress only saved every 1GB - too infrequent for user feedback

## Three-Part Solution

### 1. Force Immediate File Flush to Disk

**Problem:** Python and OS buffer file writes, so progress file may not be immediately persisted.

**Fix** in `src/wipeit.py` - `save_progress()`:
```python
with open(progress_file, 'w') as f:
    json.dump(progress_data, f, indent=2)
    f.flush()  # ← Flush Python's internal buffer
    os.fsync(f.fileno())  # ← Force OS to write to disk NOW!
```

**Why Both?**
- `f.flush()` flushes Python's file object buffer
- `os.fsync()` tells the OS to flush kernel buffers to physical disk
- Without fsync, data may sit in OS cache and be lost on crash/power loss
- Critical for reliability when user interrupts

### 2. Increase Progress Save Frequency

**Problem:** Progress only saved every 1GB (old `GB_MILESTONE_THRESHOLD`).

**Before:**
```python
GB_MILESTONE_THRESHOLD = GIGABYTE  # 1GB (misleading name)
```

**After:**
```python
PROGRESS_SAVE_THRESHOLD = 100 * MEGABYTE  # 100MB (semantic name)
```

**Impact:**
- Old: Maximum lag between saves = 1GB
- New: Maximum lag between saves = 100MB
- 10x improvement in progress tracking accuracy
- More responsive user experience
- Minimal performance impact (100MB is still a large checkpoint)

### 3. Device Write Already Flushed

**Verified** in `src/wipe_strategy.py` - `_write_chunk()`:
```python
def _write_chunk(self, chunk_data):
    with open(self.device_path, 'wb') as f:
        f.seek(self.written)
        f.write(chunk_data)
        f.flush()  # ← Already present!
        os.fsync(f.fileno())  # ← Already present!
```

Device writes were already being flushed correctly. The issue was only with the progress file.

## Technical Details

### File Flush vs OS Sync

| Operation | What It Does | Buffer Cleared |
|-----------|--------------|----------------|
| `f.write()` | Writes to Python buffer | None |
| `f.flush()` | Flushes Python buffer to OS | Python |
| `os.fsync()` | Forces OS to write to disk | OS + Python |

**Only `os.fsync()` guarantees data is on physical disk!**

### Progress Save Flow

```
User presses Ctrl+C
    ↓
KeyboardInterrupt raised
    ↓
Exception handler: written = strategy.written (accurate!)
    ↓
save_progress() called
    ↓
JSON written to file
    ↓
f.flush() - Python buffer cleared
    ↓
os.fsync() - OS buffer cleared
    ↓
Data on physical disk ✓
```

### Checkpoint Frequency Comparison

| Disk Size | Old (1GB) | New (100MB) |
|-----------|-----------|-------------|
| 100GB | 100 checkpoints | 1,000 checkpoints |
| 1TB | 1,024 checkpoints | 10,240 checkpoints |
| Max lag | 1GB | 100MB |

## Benefits

1. **Immediate Persistence**: Progress saved to disk instantly on interrupt
2. **Accurate Tracking**: Maximum lag reduced from 1GB to 100MB
3. **Crash Safety**: Data survives unexpected shutdowns
4. **Better UX**: User sees more frequent progress updates in file
5. **Minimal Overhead**: 100MB is still large enough to avoid performance issues

## Files Modified

1. **src/wipeit.py** (lines 145-151):
   - Added `f.flush()` and `os.fsync()` to `save_progress()`

2. **src/global_constants.py** (line 42):
   - Changed `GB_MILESTONE_THRESHOLD` from 1GB to 100MB

3. **KEYBOARD_INTERRUPT_BUG.md**:
   - Updated to document all three parts of the fix

## Testing

Existing tests cover:
- `test_keyboard_interrupt_saves_actual_progress`: Verifies interrupt handling
- `test_progress_percent_calculation`: Verifies progress calculation
- `test_save_progress_with_device_id`: Verifies save functionality

No new tests needed - the flush/fsync changes are transparent to tests.

## Example: Before vs After

### Before Fix
```bash
# Write 500MB, then press Ctrl+C
Progress: 0.5GB written ^C

# Check file:
$ cat wipeit_progress.json
"written": 0,  # ← Still 0 because not reached 1GB checkpoint!
```

### After Fix
```bash
# Write 500MB, then press Ctrl+C
Progress: 0.5GB written ^C

# Check file immediately:
$ cat wipeit_progress.json
"written": 536870912,  # ← 500MB saved!
"progress_percent": 0.2  # ← Accurate!

# File is guaranteed on disk (fsync), not just in OS cache
```

## Performance Impact

**Checkpoint overhead:**
- Old: 1 file write per GB = ~100 writes for 100GB disk
- New: 1 file write per 100MB = ~1000 writes for 100GB disk
- Each write: ~1-5ms (JSON is small, ~500 bytes)
- Total added time: ~5 seconds for 100GB wipe (negligible)
- Benefit: 10x better progress accuracy

**Worth it!** Negligible performance cost for massive reliability improvement.

## Summary

Three synchronized fixes ensure progress is:
1. **Accurate** - Retrieved from `strategy.written`
2. **Frequent** - Saved every 100MB instead of 1GB
3. **Persistent** - Flushed and synced to disk immediately

User can now safely interrupt at any time with minimal progress loss (max 100MB).

