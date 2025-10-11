# Resume Bug Investigation

## The Bug

User reports that `--resume` flag fails to find previous progress, even though the progress file exists and is valid.

### User's Experience

**Step 1: Run without --resume (works!)**
```bash
$ sudo src/wipeit.py /dev/sdb
==================================================
RESUME OPTIONS
==================================================
Found previous wipe sessions that can be resumed:

• Device: /dev/sdb
  Progress: 0.36% complete
  Written: 1.06 GB / 298.09 GB
  Started: Sat Oct 11 17:13:21 2025
```

**Step 2: Progress file exists and is valid**
```bash
$ cat wipeit_progress.json
{
  "device": "/dev/sdb",
  "written": 1142947840,
  "total_size": 320072933376,
  "progress_percent": 0.3570898132324555,
  ...
  "device_id": {
    "serial": "VFM201R2E81GYN",
    "model": "Hitachi_HDT725032VLA360",
    "size": 320072933376
  }
}
```

**Step 3: Run with --resume (FAILS!)**
```bash
$ sudo src/wipeit.py /dev/sdb --resume
...
No previous progress found for this device  ← BUG!
Starting fresh wipe...
```

## Analysis

### Two Different Code Paths

**Without `--resume` (works):**
1. Calls `display_resume_info()`
2. Which calls `find_resume_files()`
3. Which loads JSON file **without** device verification
4. Works perfectly

**With `--resume` (fails):**
1. Calls `load_progress(device)`
2. Which loads JSON file **with** full device verification
3. Creates `DeviceDetector(device)`
4. Calls `get_unique_id()` to verify serial/model/size
5. Fails and returns `None` (but why?)

### Possible Causes

1. **Exception in DeviceDetector**:
   - Permission issue (unlikely - running as sudo)
   - Device not accessible
   - Exception caught and silently ignored

2. **Device verification failure**:
   - Serial mismatch → would call sys.exit(1) and show error
   - Size mismatch → would call sys.exit(1) and show error
   - Model mismatch → no check for this currently

3. **Silent exception**:
   - Exception at line 257-261 catches and returns None
   - But no error message shown to user

## Debug Changes Added

### 1. Better Error Reporting in load_progress()

Added traceback printing to see actual exception:

```python
except Exception as e:
    print(f"🚨 Error loading progress file: {e}")
    import traceback
    traceback.print_exc()  # ← Show full stack trace
    return None
```

### 2. Better Resume Status Display

Added dedicated section to show what's happening:

```python
if args.resume:
    print("\n" + "=" * 70)
    print("RESUME STATUS")
    print("=" * 70)
    progress_data = load_progress(args.device)
    if not progress_data:
        print("🚨 No previous progress found for this device")
    else:
        print("✓ Found previous session")
        print(f"• Progress: {percent:.2f}% complete")
        print(f"• Written: {written_gb:.2f} GB / {total_gb:.2f} GB")
```

### 3. Device Identity Warning Enhanced

Made warning more visible:

```python
except Exception as e:
    print(f"⚠️  Warning: Could not verify device identity: {e}")
    print("   Continuing anyway (backwards compatibility)")
```

## Next Steps

1. User should run with `--resume` again
2. The enhanced error output will show:
   - Exact exception message
   - Full stack trace
   - Which part of `load_progress()` is failing

3. Once we see the actual error, we can fix the root cause

## Hypothesis

My current hypothesis is that `DeviceDetector.get_unique_id()` is throwing an exception that's being caught by the inner exception handler at line 251-254, which continues execution and returns the progress_data. But perhaps there's a second exception somewhere that we're not seeing?

Or perhaps the file doesn't exist when `load_progress()` is called due to a race condition or unexpected deletion?

The debug output will reveal the truth!

## Files Modified

- `src/wipeit.py`:
  - Lines 251-254: Enhanced device identity warning
  - Lines 257-261: Added traceback printing for exceptions
  - Lines 587-605: Enhanced resume status display with better formatting

## Expected Output After Fix

```bash
$ sudo src/wipeit.py /dev/sdb --resume

======================================================================
RESUME STATUS
======================================================================
✓ Found previous session
• Progress: 0.36% complete
• Written: 1.06 GB / 298.09 GB
Resuming wipe from 0.36% complete

[... continues with wipe ...]
```

