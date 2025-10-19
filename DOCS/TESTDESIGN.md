# Test Design Document - wipeit

**⚠️ WARNING: This tool is EXTREMELY DESTRUCTIVE and will PERMANENTLY DESTROY data! ⚠️**

## Overview

This document outlines the comprehensive testing strategy for the wipeit secure device wiping utility. It covers all features, test categories, and should be updated whenever new features are added.

**🚨 USE AT YOUR OWN RISK - ALL DATA WILL BE IRREVERSIBLY DESTROYED! 🚨**

## Table of Contents

- [Test Categories](#test-categories)
- [Feature Coverage](#feature-coverage)
- [Test Data Management](#test-data-management)
- [Mocking Strategy](#mocking-strategy)
- [Integration Testing](#integration-testing)
- [Performance Testing](#performance-testing)
- [Security Testing](#security-testing)
- [Test Maintenance](#test-maintenance)

## Test Categories

### 1. Unit Tests (`test_wipeit.py`)

#### 1.1 Core Function Tests
- **`TestParseSize`** - Buffer size parsing functionality
  - Valid size strings (1M, 100M, 1G, 0.5G, 1T)
  - Case insensitive parsing (1m, 1g, 1t)
  - Invalid size strings (500K, 2T, 0.5M, ABC, 100, 100MB)
  - Boundary values (1M minimum, 1T maximum)
  - Decimal values (0.5G, 2.5G)

#### 1.2 Progress File Management Tests
- **`TestProgressFileFunctions`** - Progress tracking functionality
  - `get_progress_file()` - File path generation
  - `save_progress()` - Progress data serialization
  - `load_progress()` - Progress data deserialization
  - `clear_progress()` - Progress file cleanup
  - File existence validation
  - JSON format validation
  - Device matching validation
  - Timestamp expiry validation (24-hour limit)

#### 1.3 Resume File Detection Tests
- **`TestResumeFileFunctions`** - Resume file scanning
  - `find_resume_file()` - Progress file detection
  - `display_resume_info()` - Resume information display
  - Multiple resume files handling
  - Expired file filtering
  - Corrupted file handling
  - Empty directory handling

#### 1.4 Device Information Tests
- **`TestDeviceInfoFunctions`** - Device querying functionality
  - `get_device_info()` - Single device information
  - `list_all_devices()` - Multiple device listing
  - Subprocess command mocking
  - Output format validation
  - Error handling for missing devices

#### 1.5 DeviceDetector Class Tests (New)
- **`TestDeviceDetector`** - Object-oriented device detection functionality
  - **Initialization**: Object creation and property setup
  - **Core Methods**: Size detection, property extraction, type detection, mount checking, partition info
  - **Private Methods**: Rotational checking, interface detection, RPM analysis, model name detection
  - **Display Methods**: Header, basic info, type info, partition info, mount status display
  - **Error Handling**: Comprehensive error scenarios for all methods
  - **Mocking Strategy**: Subprocess calls, file system operations, device properties
  - **Edge Cases**: Missing files, invalid data, subprocess failures

#### 1.6 Main Function Tests
- **`TestMainFunction`** - Command-line interface
  - Help option (`--help`)
  - Version option (`--version`, `-v`)
  - No arguments behavior
  - Device argument handling
  - Root privilege checking
  - Argument parsing validation

#### 1.6 HDD Pretest Tests
- **`TestHDDPretest`** - HDD pretest functionality (Added in 0.3.1)
  - `test_pretest_successful` - Verify HDD pretest runs and returns results
  - `test_pretest_adaptive_algorithm` - Test adaptive algorithm recommendation
  - `test_pretest_small_chunk_algorithm` - Test small chunk algorithm recommendation
  - Pretest output and analysis validation
  - Speed measurement and variance calculation

#### 1.7 Wipe Device Integration Tests
- **`TestWipeDeviceIntegration`** - Wipe device with pretest (Added in 0.3.1)
  - `test_wipe_device_with_adaptive_chunk` - **CRITICAL BUG TEST**: Validates float-to-int conversion
  - `test_adaptive_chunk_sizing_calculations` - Verifies adaptive chunk sizing produces integers
  - Integration of pretest results with wipe device function
  - Adaptive chunk algorithm correctness validation

#### 1.8 Integration Tests
- **`TestIntegration`** - End-to-end workflows
  - Complete progress save/load/clear workflow
  - Size parsing with various inputs
  - Cross-function interaction testing
  - Estimated finish time formatting and milestone tracking

### 2. Integration Tests

#### 2.1 Command-Line Interface Tests
```bash
# Test help functionality
./wipeit.py --help
./wipeit.py -h

# Test version functionality
./wipeit.py --version
./wipeit.py -v

# Test device listing (requires sudo)
sudo ./wipeit.py

# Test buffer size parsing
sudo ./wipeit.py -b 100M /dev/test
sudo ./wipeit.py -b 1G /dev/test
sudo ./wipeit.py -b 0.5G /dev/test

# Test resume functionality
sudo ./wipeit.py --resume /dev/test
```

#### 2.2 Progress File Workflow Tests
```bash
# Test progress file creation
python3 -c "from wipeit import save_progress; save_progress('/dev/test', 1024, 4096, 100)"

# Test progress file loading
python3 -c "from wipeit import load_progress; print(load_progress('/dev/test'))"

# Test progress file cleanup
python3 -c "from wipeit import clear_progress; clear_progress()"
```

### 3. Functional Tests

#### 3.1 Buffer Size Configuration Tests
- **Test Cases:**
  - Default buffer size (100M)
  - Minimum buffer size (1M)
  - Maximum buffer size (1T)
  - Decimal buffer sizes (0.5G, 2.5G)
  - Invalid buffer sizes (500K, 2T, 0.5M)

#### 3.2 Resume Functionality Tests
- **Test Cases:**
  - Create interrupted wipe scenario
  - Save progress at various points
  - Resume from different progress levels
  - Handle expired progress files
  - Handle corrupted progress files
  - Multiple device resume scenarios

#### 3.3 Progress Tracking Tests
- **Test Cases:**
  - Progress saving every 1GB
  - Progress saving every 10 chunks
  - Progress file format validation
  - Progress file location (current directory)
  - Progress cleanup on completion

#### 3.4 Safety Feature Tests
- **Test Cases:**
  - Root privilege verification
  - Mount detection and warnings
  - Confirmation prompts
  - Device information display
  - Mount status checking

### 4. Performance Tests

#### 4.1 Buffer Size Performance Tests
```python
# Test different buffer sizes with mock device
buffer_sizes = ['1M', '10M', '100M', '500M', '1G', '2G']
for size in buffer_sizes:
    # Measure write performance
    # Measure memory usage
    # Measure CPU usage
```

#### 4.2 Progress File I/O Tests
- **Test Cases:**
  - Progress file write performance
  - Progress file read performance
  - Large progress file handling
  - Concurrent progress file access

### 5. Security Tests

#### 5.1 Input Validation Tests
- **Test Cases:**
  - Malicious device paths
  - Invalid buffer size inputs
  - Path traversal attempts
  - Special character handling

#### 5.2 File System Security Tests
- **Test Cases:**
  - Progress file permissions
  - Progress file location security
  - Temporary file cleanup
  - File system access controls

### 6. Error Handling Tests

#### 6.1 Device Access Error Tests
- **Test Cases:**
  - Non-existent devices
  - Permission denied scenarios
  - Device busy scenarios
  - I/O error handling

#### 6.2 Progress File Error Tests
- **Test Cases:**
  - Corrupted JSON files
  - Missing progress files
  - Permission denied on progress files
  - Disk full scenarios

## Feature Coverage Matrix

| Feature | Unit Tests | Integration Tests | Functional Tests | Performance Tests | Security Tests |
|---------|------------|-------------------|------------------|-------------------|----------------|
| Buffer Size Parsing | ✅ | ✅ | ✅ | ❌ | ✅ |
| Progress File Management | ✅ | ✅ | ✅ | ✅ | ✅ |
| Resume Functionality | ✅ | ✅ | ✅ | ❌ | ✅ |
| Device Information | ✅ | ✅ | ✅ | ❌ | ✅ |
| Command-Line Interface | ✅ | ✅ | ✅ | ❌ | ✅ |
| Safety Features | ✅ | ✅ | ✅ | ❌ | ✅ |
| Write Flushing | ❌ | ✅ | ✅ | ✅ | ❌ |
| Pending Operations Display | ✅ | ✅ | ✅ | ❌ | ❌ |

## Test Data Management

### 1. Mock Data
- **Device Information:** Mock subprocess outputs for device queries
- **Progress Data:** Sample progress files with various states
- **File System:** Temporary files and directories for testing

### 2. Test Fixtures
```python
# Sample progress data
SAMPLE_PROGRESS_DATA = {
    'device': '/dev/sdb',
    'written': 1024 * 1024 * 1024,
    'total_size': 4 * 1024 * 1024 * 1024,
    'chunk_size': 100 * 1024 * 1024,
    'timestamp': time.time(),
    'progress_percent': 25.0
}

# Sample device information
SAMPLE_DEVICE_INFO = {
    'size': '1073741824',
    'model': 'Samsung_SSD',
    'serial': '12345',
    'partitions': 'NAME SIZE TYPE MOUNTPOINTS\nsdb 1G disk\n'
}
```

### 3. Test Environment Setup
- **Temporary Directories:** For progress file testing
- **Mock Devices:** For device information testing
- **Cleanup Procedures:** Automatic test cleanup

## Mocking Strategy

### 1. Subprocess Mocking
```python
@patch('subprocess.check_output')
def test_device_info(mock_check_output):
    mock_check_output.side_effect = [
        b'1073741824\n',  # blockdev --getsize64
        b'ID_MODEL=Samsung_SSD\n',  # udevadm info
        b'NAME SIZE TYPE MOUNTPOINTS\nsdb 1G disk\n',  # lsblk
        b'/dev/sda1 on /boot\n',  # mount
    ]
```

### 2. File System Mocking
```python
@patch('os.path.exists')
@patch('builtins.open', mock_open())
def test_progress_file_operations(mock_open, mock_exists):
    mock_exists.return_value = True
    # Test progress file operations
```

### 3. System Call Mocking
```python
@patch('os.geteuid')
def test_root_privilege_check(mock_geteuid):
    mock_geteuid.return_value = 0  # Root user
    # Test root privilege functionality
```

## Integration Testing

### 1. End-to-End Workflows
- **Complete Wipe Workflow:** Start → Interrupt → Resume → Complete
- **Progress Tracking Workflow:** Save → Load → Update → Clear
- **Command-Line Workflow:** Parse → Validate → Execute → Cleanup

### 2. Cross-Feature Integration
- **Buffer Size + Progress Tracking:** Different buffer sizes with progress saving
- **Resume + Device Info:** Resume with device information display
- **Safety + Progress:** Safety checks with progress tracking

## Performance Testing

### 1. Write Performance Tests
- **Buffer Size Impact:** Measure write speed with different buffer sizes
- **Progress Saving Impact:** Measure overhead of progress saving
- **Flush/Sync Impact:** Measure overhead of immediate flushing

### 2. Memory Usage Tests
- **Buffer Memory:** Monitor memory usage with different buffer sizes
- **Progress File Memory:** Monitor memory usage for progress operations
- **Long-Running Tests:** Memory leak detection

### 3. I/O Performance Tests
- **Progress File I/O:** Measure progress file read/write performance
- **Device I/O:** Measure device write performance (with mock devices)
- **Concurrent I/O:** Test multiple operations simultaneously

## Security Testing

### 1. Input Validation
- **Device Path Validation:** Prevent path traversal attacks
- **Buffer Size Validation:** Prevent buffer overflow attacks
- **Progress File Validation:** Prevent JSON injection attacks

### 2. File System Security
- **Progress File Permissions:** Ensure proper file permissions
- **Temporary File Security:** Secure temporary file handling
- **Directory Traversal:** Prevent unauthorized directory access

### 3. Privilege Escalation
- **Root Privilege Checks:** Ensure proper privilege validation
- **Device Access Control:** Prevent unauthorized device access
- **System Call Security:** Secure system call usage

## Test Maintenance

### 1. Adding New Features

When adding new features, update this document by:

1. **Adding New Test Categories:**
   ```markdown
   #### X.Y New Feature Tests
   - **`TestNewFeature`** - Description of new feature
     - Test case 1
     - Test case 2
     - Test case 3
   ```

2. **Updating Feature Coverage Matrix:**
   - Add new feature row
   - Mark appropriate test coverage columns

3. **Adding New Test Cases:**
   - Unit tests for core functionality
   - Integration tests for CLI interface
   - Functional tests for end-to-end workflows
   - Performance tests if applicable
   - Security tests if applicable

### 2. Test Case Templates

#### Unit Test Template
```python
class TestNewFeature(unittest.TestCase):
    """Test the new feature functionality."""

    def setUp(self):
        """Set up test environment."""
        pass

    def tearDown(self):
        """Clean up test environment."""
        pass

    def test_feature_basic_functionality(self):
        """Test basic feature functionality."""
        # Test implementation
        pass

    def test_feature_edge_cases(self):
        """Test feature edge cases."""
        # Test implementation
        pass

    def test_feature_error_handling(self):
        """Test feature error handling."""
        # Test implementation
        pass
```

#### Integration Test Template
```bash
# Test new feature via command line
./wipeit.py --new-feature-option value

# Test new feature with other features
./wipeit.py --existing-option --new-feature-option value
```

### 3. Test Documentation Updates

When adding tests, also update:

1. **README.md:** Add usage examples for new features
2. **DOCS/CHANGES.md:** Document new test coverage
3. **This document:** Add new test categories and coverage

### 4. Continuous Integration

#### Test Execution
```bash
# Run all tests
python3 test_wipeit.py

# Run specific test class
python3 -m unittest test_wipeit.TestParseSize

# Run with coverage
python3 -m coverage run test_wipeit.py
python3 -m coverage report
```

#### Test Quality Metrics
- **Code Coverage:** Aim for >90% coverage
- **Test Execution Time:** Keep under 30 seconds
- **Test Reliability:** 100% pass rate
- **Test Maintainability:** Clear, documented test cases

## Test Execution

### 1. Running Tests

```bash
# Run all tests
python3 test_wipeit.py

# Run with verbose output
python3 test_wipeit.py -v

# Run specific test class
python3 -m unittest test_wipeit.TestParseSize -v

# Run specific test method
python3 -m unittest test_wipeit.TestParseSize.test_valid_sizes -v
```

### 2. Test Coverage

```bash
# Install coverage tool
pip install coverage

# Run tests with coverage
coverage run test_wipeit.py

# Generate coverage report
coverage report

# Generate HTML coverage report
coverage html
```

### 3. Continuous Integration

```yaml
# Example GitHub Actions workflow
name: Tests
on: [push, pull_request]
jobs:
  test:
    runs-on: ubuntu-latest
    steps:
    - uses: actions/checkout@v2
    - name: Set up Python
      uses: actions/setup-python@v2
      with:
        python-version: 3.8
    - name: Install dependencies
      run: pip install coverage
    - name: Run tests
      run: python3 test_wipeit.py
    - name: Run coverage
      run: coverage run test_wipeit.py && coverage report
```

## Test Statistics

### Current Test Coverage (v1.6.0+)
- **Total Test Classes**: 13
- **Total Test Cases**: 188
- **Test Coverage Breakdown**:
  - `TestParseSize`: 5 tests
  - `TestProgressFileFunctions`: 7 tests
  - `TestResumeFileFunctions`: 5 tests
  - `TestUtilityFunctions`: 2 tests (Updated: now returns 4-tuple)
  - `TestDeviceInfoFunctions`: 2 tests
  - `TestMainFunction`: 4 tests
  - `TestIntegration`: 4 tests
  - `TestHDDPretest`: 3 tests (Added in 0.3.1)
  - `TestWipeDeviceIntegration`: 2 tests (Added in 0.3.1)
  - `TestMountChecking`: 6 tests (Added in 1.1.0)
  - `TestDeviceDetector`: 35 tests (Added in 1.1.0+)
  - `TestAutoDetectResume`: 7 tests (Added in 1.5.0)
  - **`TestProgressFileVersion`: 10 tests** (Added in 1.6.0)
  - **`TestWipeStrategyFactory`: 7 tests** (Added in 1.6.0)

### DeviceDetector Test Coverage
The new `TestDeviceDetector` class provides comprehensive coverage of the object-oriented device detection functionality:

#### **Initialization Tests**
- `test_init()` - Verify proper object initialization

#### **Core Method Tests**
- `test_get_size()` - Device size detection with success/error cases
- `test_get_device_properties()` - udev property extraction with success/error cases
- `test_detect_type()` - Complete device type detection workflow
- `test_is_mounted()` - Mount status checking (not mounted, device mounted, partitions mounted, error cases)
- `test_get_partitions()` - Partition information retrieval with success/error cases
- `test_display_info()` - Complete information display workflow

#### **Private Method Tests**
- `test_check_rotational_ssd()` - SSD rotational check (returns False)
- `test_check_rotational_hdd()` - HDD rotational check (returns True)
- `test_check_rotational_not_found()` - Missing sysfs file handling
- `test_check_nvme_interface_true/false()` - NVMe interface detection
- `test_check_mmc_interface_true/false()` - MMC interface detection
- `test_analyze_rpm_indicators_*()` - RPM indicator analysis (zero RPM, with RPM, NVMe bus)
- `test_detect_from_model_name_*()` - Model name-based detection (SSD, HDD, unknown)
- `test_determine_type_*()` - Type determination logic (NVMe, MMC, SSD, HDD, various indicators)

#### **Display Method Tests**
- `test_display_header()` - Information header display
- `test_display_basic_info()` - Basic device information display
- `test_display_type_info()` - Device type information display
- `test_display_partition_info()` - Partition information display
- `test_display_mount_status_*()` - Mount status display (mounted/not mounted)

#### **Error Handling Tests**
- `test_get_size_error()` - Size detection error handling
- `test_get_device_properties_error()` - Property extraction error handling
- `test_detect_type_error()` - Type detection error handling
- `test_is_mounted_error()` - Mount check error handling
- `test_get_partitions_error()` - Partition info error handling
- `test_display_info_error()` - Display error handling

### Code Coverage Goals
- **Target**: 90%+ code coverage
- **Critical Paths**: 100% coverage for HDD pretest, adaptive chunk algorithms, and DeviceDetector class
- **Current Status**: All 75 tests passing with 0 linting errors

## Conclusion

This test design document provides comprehensive coverage for all wipeit features. It should be updated whenever new features are added to ensure complete test coverage and maintainability.

### Recent Updates (v1.2.0+)
- Added comprehensive test coverage for HDD pretest functionality
- Added critical bug test for float-to-integer conversion in adaptive chunk sizing
- Increased test count from 34 to 40 tests
### TestAutoDetectResume Test Coverage (v1.5.0)
The new `TestAutoDetectResume` class provides comprehensive coverage of the auto-detection resume functionality:

#### **Core Function Tests**
- `test_find_device_by_serial_model_found()` - Successful device auto-detection by serial and model
- `test_find_device_by_serial_model_not_found()` - No matching device scenario
- `test_find_device_by_serial_model_no_progress_file()` - Missing progress file handling
- `test_find_device_by_serial_model_no_serial_in_progress()` - Progress file without serial number

#### **Integration Tests**
- `test_setup_argument_parser_resume_without_device()` - Argument parser validation
- `test_main_resume_without_device_auto_detects()` - Full integration with main()
- `test_main_resume_without_device_no_match()` - Error handling when no match found

### Recent Additions
- **Added auto-detect resume test coverage (7 new tests)** (v1.5.0)
- **Increased total test count from 75 to 82 tests** (v1.5.0)
- Added comprehensive mount checking test coverage (6 new tests)
- **Added comprehensive DeviceDetector class test coverage (35 new tests)**
- **Increased total test count from 40 to 75 tests**
- **Added object-oriented testing patterns and class method coverage**
- All tests comply with 79-character line length limit

### Key Principles:
1. **Comprehensive Coverage:** Test all features and edge cases
2. **Maintainable Tests:** Clear, documented, and easy to update
3. **Reliable Tests:** Consistent, deterministic test results
4. **Performance Awareness:** Monitor test execution time and resource usage
5. **Security Focus:** Test security-critical functionality thoroughly

### Maintenance Checklist:
- [ ] Update test categories when adding features
- [ ] Update feature coverage matrix
- [ ] Add new test cases for new functionality
- [ ] Update documentation (README, CHANGES)
- [ ] Verify test coverage remains >90%
- [ ] Ensure all tests pass consistently
- [ ] Review and update this document quarterly
