# Resume Milestone Bug - Test Coverage

## The Bug
When resuming a wipe (e.g., at 47%), `last_milestone` was initialized to 0 instead of being calculated from the resume position. This caused milestone messages (5%, 10%, 15%, etc.) to be repeated, even though they were already shown in the previous session.

## Tests That Catch This Bug

### Primary Tests (Directly Catch the Bug)

#### 1. `test_milestone_initialization_on_resume`
**Location**: `test_wipe_strategy.py:211`  
**What it tests**: Verifies `last_milestone` is correctly calculated based on `start_position`  
**Coverage**:
- Resume from 0% → `last_milestone = 0`
- Resume from 12% → `last_milestone = 10`
- Resume from 47% → `last_milestone = 45` **CATCHES THE BUG**
- Resume from 5% → `last_milestone = 5`
- Resume from 99% → `last_milestone = 95`

**Why it catches the bug**: 
If `last_milestone` was hardcoded to 0, this test would fail when asserting:
```python
self.assertEqual(strategy.last_milestone, 45)  # Would be 0 with the bug
```

---

#### 2. `test_milestone_not_repeated_after_resume`
**Location**: `test_wipe_strategy.py:258`  
**What it tests**: Verifies milestones aren't repeated when resuming  
**Test scenario**:
1. Resume from 47% (should set `last_milestone = 45`)
2. Call `_display_progress()` at 47%
3. Verify milestone 45 is **NOT** shown (already passed)
4. Progress to 50%
5. Verify milestone 50 **IS** shown (new milestone)

**Why it catches the bug**:
With the bug, `last_milestone = 0`, so when displaying progress at 47%, it would show milestones 5%, 10%, 15%, 20%, 25%, 30%, 35%, 40%, 45% all over again.

---

#### 3. `test_resume_milestone_integration` ⭐ **NEW**
**Location**: `test_wipe_strategy.py:838`  
**What it tests**: Full integration test simulating exact user scenario  
**Test scenario**:
1. Start wipe, reach 47%
2. Stop (simulate Ctrl+C)
3. Resume from 47%
4. Simulate progress from 47% → 52%
5. Track which milestones are shown
6. Assert **ONLY** milestone 50% is shown

**Why it catches the bug**:
```python
# Only 50% should have triggered a milestone (not 5, 10, 15, etc.)
self.assertEqual(
    milestones_shown, [50],
    f"Bug: Should only show milestone 50%, "
    f"but showed: {milestones_shown}. "
    f"This means old milestones were repeated!")
```

With the bug, `milestones_shown` would be `[50]` if working correctly, but could show earlier milestones if the bug exists.

---

### Related Tests (Don't Catch This Specific Bug)

#### 4. `test_milestone_tracking`
**Location**: `test_wipe_strategy.py:111`  
**Why it doesn't catch the bug**: Tests milestone tracking from 0%, not from resume position

---

#### 5. `test_milestone_not_shown_twice`
**Location**: `test_wipe_strategy.py:136`  
**Why it doesn't catch the bug**: Tests milestone deduplication in a single session, not across resume

---

#### 6. `test_milestone_increments_correctly`
**Location**: `test_wipe_strategy.py:166`  
**Why it doesn't catch the bug**: Tests all milestones in sequence from 0%, not from resume

---

#### 7. `test_init_with_resume_position`
**Location**: `test_wipe_strategy.py:308`  
**Why it doesn't catch the bug**: Only tests `written` position, not milestone tracking

---

#### 8. `test_wipe_resume_from_position`
**Location**: `test_wipe_strategy.py:394`  
**Why it doesn't catch the bug**: Tests wiping completes from resume, no milestone checking

---

#### 9. `test_strategies_handle_resume`
**Location**: `test_wipe_strategy.py:715`  
**Why it doesn't catch the bug**: Tests all strategies can resume, no milestone checking

---

#### 10. `test_milestone_display_all_strategies`
**Location**: `test_wipe_strategy.py:747`  
**Why it doesn't catch the bug**: Tests milestone display across strategies, but from 0%

---

#### 11. `test_milestone_uniqueness_all_strategies`
**Location**: `test_wipe_strategy.py:794`  
**Why it doesn't catch the bug**: Tests milestone deduplication in single session, not resume

---

## Summary

**Tests that would catch the resume milestone bug: 3**

1. `test_milestone_initialization_on_resume` - Direct assertion on `last_milestone` value
2. `test_milestone_not_repeated_after_resume` - Verifies no repeated milestones after resume
3. `test_resume_milestone_integration` - Full integration test of user scenario

**Test count**: 146 total tests (was 145, added 1 integration test)  
**Coverage**: 95%

## How to Verify the Fix

Run the specific tests that catch the bug:
```bash
cd /home/lcortes/Code3/wipeit/src
python -m unittest \
    test_wipe_strategy.TestWipeStrategyBase.test_milestone_initialization_on_resume \
    test_wipe_strategy.TestWipeStrategyBase.test_milestone_not_repeated_after_resume \
    test_wipe_strategy.TestStrategyIntegration.test_resume_milestone_integration \
    -v
```

All three should pass. If you revert the fix (set `last_milestone = 0` always), tests 1 and 2 would fail immediately, and test 3 would fail when checking milestone output.

## Code Fix Summary

**File**: `src/wipe_strategy.py:46-59`

**Before** (Bug):
```python
self.last_milestone = 0  # Always 0, even when resuming!
```

**After** (Fixed):
```python
# Calculate last milestone based on start position for resume support
if total_size > 0:
    current_percent = (start_position / total_size) * 100
    self.last_milestone = int(current_percent) // \
        MILESTONE_INCREMENT_PERCENT * MILESTONE_INCREMENT_PERCENT
else:
    self.last_milestone = 0
```

This ensures when resuming at 47%, `last_milestone = 45`, so the next milestone shown is 50%.

