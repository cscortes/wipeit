# Programming Style

**⚠️ WARNING: This tool is EXTREMELY DESTRUCTIVE and will PERMANENTLY DESTROY data! ⚠️**

**🚨 USE AT YOUR OWN RISK - ALL DATA WILL BE IRREVERSIBLY DESTROYED! 🚨**

- All python programs must have a hard length of 79 characters per line.
- All python doc strings must also have a hard length of 79 characters per line.
- keep routines small, by breaking up larger routines into logical/
reusable functions.
- recommend new classes based on functionality,
to dev in the TODO.md as a low priority item.
- Use only doc strings in functions, not inline comments.
- make sure we have unittest code coverage for all code.
- make sure all dependencies for release and debug are being updated in pyproject.toml

## Import Organization

**All imports MUST be at the top of files** immediately after the module docstring.

### Import Order

Organize imports in the following order, with a blank line between each group:

1. **Standard library imports** (e.g., `os`, `sys`, `time`)
2. **Third-party library imports** (e.g., `numpy`, `pytest`)
3. **Local application imports** (e.g., `from global_constants import ...`)

Example:
```python
#!/usr/bin/env python3
"""
Module docstring here.
"""

import os
import sys
import time

from global_constants import MEGABYTE, GIGABYTE
from device_detector import DeviceDetector
```

### Exception: Circular Dependency Imports

The ONLY acceptable exception to top-level imports is when avoiding circular
dependencies between modules.

In this case:
- Import inside the function/method where it's needed
- Add a comment explaining the circular dependency
- This should be a rare occurrence

Example:
```python
    def run_pretest(self):
        """Run disk pretest."""
        try:
            # Import here to avoid circular dependency (wipeit imports disk_pretest)
            from device_detector import DeviceDetector
            size = DeviceDetector.get_block_device_size(self.device_path)
            # ... rest of method
```

### Rationale

- **Clarity**: All dependencies are visible at the top of the file
- **Performance**: Imports are loaded once when module loads
- **Standards**: Follows PEP 8 and Python community conventions
- **Maintainability**: Easy to see what a module depends on
- **Tooling**: Import sorting tools (isort, black) work better

### Prohibited Patterns

❌ **Bad - Import inside function without reason:**
```python
def process_data():
    import os  # No circular dependency - should be at top!
    return os.path.exists('/tmp/file')
```

❌ **Bad - Multiple imports scattered throughout file:**
```python
import os

def func1():
    pass

import sys  # Wrong - should be at top with os

def func2():
    pass
```

✅ **Good - All imports at top:**
```python
import os
import sys

def func1():
    pass

def func2():
    pass
```

✅ **Good - Exception for circular dependency:**
```python
import os
import sys

def process():
    # Import here to avoid circular dependency
    from module_b import helper
    return helper(data)
```

## Documentation File Organization

**All documentation files MUST be in the `DOCS/` directory** with the following exception:

### Exception: Root Level Documentation
- **`README.md`** - ONLY file allowed at project root level
  - Primary project documentation
  - First file users see on GitHub
  - Contains installation, usage, and quick start information

### Mandatory Location: DOCS/ Directory
All other `.md` files MUST be placed in the `DOCS/` directory, including but not limited to:
- `CHANGES.md` - Changelog and release notes
- `ARCH.md` - Architecture documentation
- `TODO.md` - Task lists and future work
- `PROGRAMMING_STYLE_GUIDE.md` - This file
- `TESTDESIGN.md` - Testing approach and strategy
- `RELEASE_CHECK_LIST.md` - Release process documentation
- `SAFETY_SETUP.md` - Safety and security setup
- `PERFORMANCE-GUIDE.md` - Performance optimization guide
- `CI-CD.md` - Continuous integration documentation
- Any bug analysis or feature documentation files

### Rationale
- **Clean root directory**: Keeps project root uncluttered
- **Organized documentation**: All docs in one place
- **Easy discovery**: Developers know where to find documentation
- **Maintainability**: Easier to manage and update documentation
- **Professional appearance**: Shows well-organized project structure

### Enforcement
- During code review, any `.md` file (except `README.md`) in the project root should be moved to `DOCS/`
- Build scripts and CI/CD pipelines may enforce this rule
- Use `find . -maxdepth 1 -name "*.md" ! -name "README.md"` to check for violations

## Icon Usage

**Minimize icon usage** - icons should only be used for critical alerts and
warnings, not for decoration or visual enhancement.

### Allowed Icons

Only the following icons are permitted:
- **⚠️** (Warning Triangle): For warnings and caution messages
- **🚨** (Police Light): For critical alerts and destructive actions

### Prohibited Icons

All other icons are prohibited, including but not limited to:
- Decorative icons (🔍 🔒 💾 🛡️ 🎯 🔬 ⚡ 🎨 📈 etc.)
- Status icons (✅ ❌ 🔄 ⏰ ⏱️ 🛑 etc.)
- Informational icons (📋 📊 📝 📦 🔧 🏗️ 🧪 ℹ️ etc.)

### Rationale

- **Professionalism**: System utilities should be clean and professional
- **Accessibility**: Icons may not render properly on all terminals
- **Clarity**: Text-based indicators (e.g., "WARNING:", "NOTE:") are clearer
- **Maintenance**: Fewer icons means simpler documentation and code

### Examples

Good:
```python
print("WARNING: This will destroy all data")
print("CRITICAL: Device is mounted - cannot proceed")
```

Bad:
```python
print("🔍 Scanning device...")
print("✅ Operation complete")
print("📊 Progress: 50%")
```

Acceptable (critical warnings only):
```python
print("⚠️ WARNING: This will destroy all data")
print("🚨 CRITICAL: Device is mounted - cannot proceed")
```

## Class Programming Style

### Class Design Principles

- **Single Responsibility**: Each class should have one clear purpose.
  A class that does too much should be split into smaller classes.

- **Encapsulation**: Keep data and methods that operate on that data
  together. Use private methods (prefixed with `_`) for internal logic.

- **Small Methods**: Break complex methods into smaller helper methods.
  Each method should do one thing and do it well.

- **Descriptive Names**: Class names should be nouns (e.g., DeviceDetector).
  Method names should be verbs (e.g., get_size, detect_type).

### Method Organization

Methods in a class should be ordered as follows:
1. `__init__` constructor first
2. Public methods (no underscore prefix)
3. Private/helper methods (underscore prefix)
4. Properties and special methods last

Example:
```python
class DeviceDetector:
    def __init__(self, device_path):
        """Initialize detector."""

    def get_size(self):
        """Public method - get device size."""

    def detect_type(self):
        """Public method - detect device type."""

    def _check_rotational(self):
        """Private helper - check rotation."""

    def _analyze_indicators(self):
        """Private helper - analyze indicators."""
```

### Constructor Guidelines

- Keep `__init__` simple - only initialize instance variables
- Avoid heavy computation or I/O in constructors
- Use private variables with underscore for internal state
- Document all parameters in docstring

Example:
```python
def __init__(self, device_path):
    """
    Initialize device detector.

    Args:
        device_path: Path to block device (e.g., '/dev/sdb')
    """
    self.device_path = device_path
    self.device_name = os.path.basename(device_path)
    self._cached_info = {}  # Private cache
```

### Method Documentation

Every method must have a docstring explaining:
- What the method does (one line summary)
- Parameters (Args section)
- Return values (Returns section)
- Exceptions raised (Raises section, if applicable)

Example:
```python
def detect_type(self):
    """
    Detect storage device type (HDD/SSD/NVMe).

    Returns:
        tuple: (disk_type, confidence_level, detection_details)
            - disk_type: str like "HDD", "SSD", "NVMe SSD"
            - confidence_level: str like "HIGH", "MEDIUM", "LOW"
            - detection_details: list of detection method strings

    Raises:
        OSError: If device cannot be accessed
    """
```

### Helper Methods (Private Methods)

- Prefix with single underscore: `_helper_method()`
- Used for breaking down complex logic
- Should not be called from outside the class
- Still require docstrings (can be shorter)

Example:
```python
def _check_rotational(self):
    """Check if device is rotational via sysfs."""
    rotational_path = f"/sys/block/{self.device_name}/queue/rotational"
    if os.path.exists(rotational_path):
        with open(rotational_path, 'r') as f:
            return f.read().strip() == '1'
    return None
```

### Avoid Long Methods

If a method exceeds 30 lines, consider breaking it into smaller methods.
Use helper methods to improve readability and testability.

Bad:
```python
def detect_type(self):
    """50+ lines of complex logic..."""
```

Good:
```python
def detect_type(self):
    """Detect device type using multiple methods."""
    is_rotational = self._check_rotational()
    is_nvme = self._check_nvme_interface()
    udev_props = self.get_device_properties()
    rpm_indicators = self._analyze_rpm_indicators(udev_props)
    return self._determine_type(is_rotational, is_nvme, rpm_indicators)
```

### Instance Variables vs Local Variables

- Instance variables (self.variable): Data that persists across methods
- Local variables: Temporary data within a method
- Use instance variables sparingly - only for true object state
- Cache expensive operations in instance variables with `_` prefix

Example:
```python
def __init__(self, device_path):
    self.device_path = device_path      # Core state
    self._cached_size = None            # Cached computation

def get_size(self):
    """Get size with caching."""
    if self._cached_size is None:
        self._cached_size = self._compute_size()
    return self._cached_size
```

### Testing Classes

Each class should have a dedicated test class in a separate test file:
- **Test file naming**: `test_<class_name>.py` (e.g., `test_device_detector.py`)
- **Test class name**: `Test<ClassName>` (e.g., TestDeviceDetector)
- **One test file per class**: Each class gets its own dedicated test file
- Test each public method
- Test edge cases and error conditions
- Mock external dependencies (file system, subprocess calls)

Example file structure:
```
src/
├── device_detector.py       # DeviceDetector class
├── test_device_detector.py  # DeviceDetector tests
├── wipeit.py               # Main functions
├── test_wipeit.py          # Function tests
└── test_wipeit.py          # Legacy combined tests (to be split)
```

Example test file (`test_device_detector.py`):
```python
import unittest
from unittest.mock import patch, MagicMock
from device_detector import DeviceDetector

class TestDeviceDetector(unittest.TestCase):
    """Test DeviceDetector class."""

    def test_init(self):
        """Test initialization."""

    def test_get_size(self):
        """Test size detection."""

    @patch('subprocess.check_output')
    def test_detect_type_ssd(self, mock_subprocess):
        """Test SSD detection."""
```

### Test File Organization

- **Separate test files**: Each class should have its own test file
- **Test file naming**: `test_<module_name>.py` for classes, `test_<function_module>.py` for function modules
- **Test discovery**: All test files should be discoverable by unittest
- **Import organization**: Import the class/module being tested at the top
- **Test isolation**: Each test file should be independently runnable

### When to Use Classes vs Functions

Use a class when:
- You have multiple related operations on the same data
- You need to maintain state between operations
- You want to encapsulate complex logic with helper methods
- You need multiple instances with different configurations

Use functions when:
- Single, standalone operation
- No state to maintain
- Utility/helper operations
- Operating on multiple different objects

### File Organization

- **One file per class**: Each class should be in its own file
- **File naming**: Use snake_case for file names (e.g., `device_detector.py`)
- **Class naming**: Use PascalCase for class names (e.g., `DeviceDetector`)
- **Package structure**: Organize classes in logical packages under `src/`

Example structure:
```
src/
├── __init__.py
├── global_constants.py      # All application constants
├── device_detector.py       # DeviceDetector class
├── progress_manager.py      # ProgressManager class (future)
└── wipeit.py               # Main functions and CLI
```

### Constants and Global Variables

- **Constants file**: All application constants should be defined in `global_constants.py`
- **Naming convention**: Use ALL_CAPS with underscores for constant names
- **Organization**: Group related constants together with descriptive comments
- **Import usage**: Import constants from `global_constants` module

Example constants file:
```python
# Size multipliers
KILOBYTE = 1024
MEGABYTE = 1024 * 1024
GIGABYTE = 1024 * 1024 * 1024

# Default values
DEFAULT_CHUNK_SIZE = 100 * MEGABYTE
PROGRESS_FILE_EXPIRY_SECONDS = 24 * 3600

# Thresholds
LOW_SPEED_THRESHOLD_MBPS = 50
```

Usage in code:
```python
from global_constants import MEGABYTE, DEFAULT_CHUNK_SIZE

def parse_size(size_str):
    return int(size_str) * MEGABYTE
```

**Benefits:**
- Centralized constant management
- Easy to find and update values
- Prevents magic numbers throughout code
- Improves code readability and maintainability

### Backward Compatibility

When refactoring functions to classes:
- Keep original functions as thin wrappers
- Allows gradual migration
- Maintains existing tests
- Document deprecation path

Example:
```python
def get_device_info(device):
    """
    Get device information (DEPRECATED - use DeviceDetector).

    This function is maintained for backward compatibility.
    New code should use: DeviceDetector(device).display_info()
    """
    detector = DeviceDetector(device)
    return detector.display_info()
```
