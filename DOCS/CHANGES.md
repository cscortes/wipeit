# Changelog

**⚠️ WARNING: This tool is EXTREMELY DESTRUCTIVE and will PERMANENTLY DESTROY data! ⚠️**

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

**🚨 USE AT YOUR OWN RISK - ALL DATA WILL BE IRREVERSIBLY DESTROYED! 🚨**

## [Unreleased]

## [1.5.0] - 2025-10-19

### Added
- **Auto-Detect Resume Drive**: Major enhancement to `--resume` functionality
  - `--resume` no longer requires device specification
  - Automatically searches all drives and matches by serial number and model
  - Device path (e.g., `/dev/sdb`) can now change between sessions
  - New function `find_device_by_serial_model()` searches and matches drives
  - Maintains backwards compatibility: can still specify device manually
  - Shows clear feedback about which drive was detected
  - Provides helpful error messages when no matching drive is found

### Changed
- **Argument Parser**: Updated help text and examples
  - Device argument is now optional with `--resume`
  - Updated help: "Resume previous wipe session (auto-detects drive by serial number)"
  - Updated examples to show both `wipeit --resume` and `wipeit --resume /dev/sdb`

### Improved
- **User Messages**: Updated all `--resume` instructions throughout the codebase
  - KeyboardInterrupt message now shows auto-detection info
  - Device mismatch errors reference auto-detection
  - Resume prompts clarify no device specification needed

### Tests
- **Comprehensive Test Coverage**: Added 7 new tests in `TestAutoDetectResume` class
  - `test_find_device_by_serial_model_found()` - Successful auto-detection
  - `test_find_device_by_serial_model_not_found()` - No matching device
  - `test_find_device_by_serial_model_no_progress_file()` - Missing progress file
  - `test_find_device_by_serial_model_no_serial_in_progress()` - Missing serial
  - `test_setup_argument_parser_resume_without_device()` - Parser validation
  - `test_main_resume_without_device_auto_detects()` - Integration test
  - `test_main_resume_without_device_no_match()` - Error handling
  - All 174 tests passing with 97% code coverage

## [1.4.4] - 2025-10-13

### Fixed
- **CI/CD Integration Tests**: Fixed `test-ci.sh` to use updated function signatures
  - Updated `clear_progress(device)` → `clear_progress()` (no arguments)
  - Updated `find_resume_files()` → `find_resume_file()` (returns dict or None)

### Documentation
- **Complete Documentation Update**: All documentation files updated to reflect refactored code
  - `ARCH.md`: Updated function listings, removed obsolete functions, added new utility functions
  - `PROGRAMMING_STYLE_GUIDE.md`: Updated circular dependency example to use DeviceDetector
  - `TESTDESIGN.md`: Updated function names to match current implementation

## [1.4.3] - 2025-10-13

### Fixed
- **CRITICAL: Random Data Wiping**: Fixed bug where device was being overwritten with zeros instead of random data
  - Changed all wipe operations to use `os.urandom()` for cryptographically secure random data
  - Affects StandardStrategy, AdaptiveStrategy, and DiskPretest
  - Now properly meets security requirements for secure data destruction
  - Impact: Slightly slower due to random data generation, but significantly more secure

### Changed
- **Code Refactoring**: Improved code organization based on human review of AI-generated code
  - Moved `get_block_device_size()` from wipeit.py to DeviceDetector class as static method
  - Consolidated device size functionality using ioctl (BLKGETSIZE64) instead of subprocess
  - Removed circular import dependencies between modules
  - Cleaned up import organization (all imports at top of files)
  - Removed redundant wrapper functions and duplicate code
  - Removed unused `timestamp` parameter from PretestResults
  - Removed redundant `analysis` dictionary from PretestResults.to_dict()

### Added
- **Test Coverage**: Added comprehensive tests for utility functions
  - New TestUtilityFunctions class with 17 test methods
  - Tests for `calculate_average_speed()`, `create_wipe_strategy()`, `handle_resume()`, `handle_hdd_pretest()`, `setup_argument_parser()`
  - Removed redundant tests already covered in test_device_detector.py
  - All 167 tests pass

### Documentation
- **Programming Style Guide**: Added import organization guidelines
  - All imports must be at top of files
  - Exception only for circular dependencies with explanatory comment
  - Three-tier import ordering: stdlib, third-party, local

## [1.4.2] - 2025-10-12

### Added
- **GitHub Release Wheel Distribution**: Wheel and source distribution files now automatically attached to GitHub releases
  - Updated workflow to use `softprops/action-gh-release@v1`
  - Users can download `.whl` files directly from releases page
  - Installation: `pip install wipeit-*.whl`

### Changed
- **Installation Documentation**: Updated README with GitHub release wheel installation as recommended method
  - Option 1: Download wheel from releases (recommended)
  - Option 2: Install from source
- **Release Workflow**: Enhanced to attach distribution files as release assets
- **Architecture Documentation**: Completely updated ARCH.md to reflect current codebase
  - Documented Strategy pattern (WipeStrategy classes)
  - Added DiskPretest class documentation
  - Updated file structure with all current modules
  - Added comprehensive mermaid diagrams
  - Documented testing architecture (157 tests, 95% coverage)

### Removed
- **PyPI References**: Removed all PyPI installation documentation
  - Distribution is now exclusively via GitHub releases
  - No PyPI upload attempted
  - Removed PyPI upload step from CI/CD workflow

## [1.4.1] - 2025-10-11

### Fixed
- **Critical: Progress callbacks never called**: Fixed modulo alignment bug that prevented progress saves
  - Problem: `written % PROGRESS_SAVE_THRESHOLD == 0` fails when chunk sizes don't align (e.g., 1GB chunks vs 100MB threshold: `1073741824 % 104857600 = 62914560 ≠ 0`)
  - Solution: Added `written_since_last_save` tracking variable
  - Changed condition to `written_since_last_save >= PROGRESS_SAVE_THRESHOLD`
  - Ensures progress saves every 100MB regardless of chunk size
  - Affects StandardStrategy and AdaptiveStrategy
- **UnboundLocalError crash**: Fixed variable scope issue in exception handlers
  - Initialize `device_id = None` at start of `wipe_device()` function
  - Prevents crashes when exceptions occur before device_id is assigned
- **Test infrastructure improvements**: Fixed 4 test mocking issues
  - Added missing `DeviceDetector` mocks in integration tests
  - Fixed `test_keyboard_interrupt_saves_actual_progress` device attribute
  - Added `input()` mock to prevent test hanging
  - All 157 tests now pass reliably

### Changed
- Test reliability: All tests properly mocked and isolated
- Code quality: Fixed whitespace and line length linter errors

## [1.4.0] - 2025-10-11

### Fixed
- **Critical: Keyboard interrupt progress loss**: Fixed bug where pressing Ctrl+C saved 0 bytes instead of actual progress
  - Exception handler now retrieves `strategy.written` before saving
  - Added `if 'strategy' in locals()` check for safety
  - Applies to both KeyboardInterrupt and general exceptions
- **Progress file flush**: Added immediate disk flush (`os.fsync()`) to ensure progress survives crashes
  - Python buffer flush + OS kernel flush for guaranteed persistence
  - Critical for interrupt and crash safety
- **Progress save frequency**: Increased from every 1GB to every 100MB
  - 10x improvement in progress tracking accuracy
  - Maximum lag reduced from 1GB to 100MB
- **Device mismatch on resume**: Program now halts immediately (sys.exit(1)) with clear error message when device ID doesn't match
  - Shows expected vs current serial/model/size
  - Provides step-by-step recovery instructions
  - Prevents accidental wiping of wrong drive
- **Test failure**: Fixed `test_wipe_with_progress_callback` to calculate expected callbacks dynamically

### Added
- **Enhanced resume diagnostics**: Added debug output to investigate resume detection issues
  - Full exception traceback in load_progress()
  - Dedicated RESUME STATUS section showing found/not-found status
  - Enhanced device identity warnings
- **Device unique ID verification**: Resume operations now verify device identity using serial, model, and size
  - `DeviceDetector.get_unique_id()` method added
  - Verifies correct drive before resuming wipe
  - Prevents accidental data loss from device swaps
- **Comprehensive test coverage**: Added 8 new tests for keyboard interrupt and device verification
  - `test_keyboard_interrupt_saves_actual_progress`: Verifies interrupt saves actual progress
  - `test_resume_with_mismatched_device_halts`: Integration test for device mismatch
  - `test_save_progress_with_device_id`: Ensures device_id is saved
  - `test_load_progress_verifies_device_id`: Loads and verifies matching ID
  - `test_load_progress_rejects_mismatched_serial`: Halts on serial mismatch
  - `test_load_progress_rejects_mismatched_size`: Halts on size mismatch
  - `test_get_unique_id`: Gets device identifiers
  - `test_get_unique_id_missing_fields`: Handles missing identifiers

### Changed
- **⚠️ BREAKING**: Progress filename is now always `wipeit_progress.json` instead of `wipeit_progress_[device].json`
  - Simplifies progress tracking with single consistent filename
  - Note: Only one device can have active progress at a time
  - Old device-specific progress files will be ignored
- **Constant renamed**: `GB_MILESTONE_THRESHOLD` → `PROGRESS_SAVE_THRESHOLD` for semantic clarity
  - Old name was misleading (value is 100MB, not GB)
  - New name is unit-agnostic and semantically accurate
- **Progress percent calculation**: Now accurately calculated and saved during interrupts
- **Icon usage**: Removed most decorative icons, keeping only `⚠️` and `🚨` for critical warnings
  - Added strict icon usage guidelines to PROGRAMMING_STYLE_GUIDE.md
- **Test count**: Increased to 157 unit tests (up from 149)
- **Test coverage**: Maintained at 95%

### Technical
- **File I/O**: All progress saves now use `f.flush()` + `os.fsync()` for immediate disk persistence
- **Error handling**: Enhanced exception messages with full tracebacks for debugging
- **Safety improvements**: Multiple layers of verification prevent wrong-device wipes

## [1.3.1] - 2025-10-11

### Fixed
- **Estimated finish time display**: Restored feature that shows actual clock time (e.g., "3:15 PM") at 5% progress milestones (lost during WipeStrategy refactoring)
- **Resume milestone bug**: Fixed bug where milestones were repeated when resuming a wipe. Now correctly calculates last_milestone based on resume position (e.g., resuming at 47% starts at milestone 45, next shown is 50%)

### Added
- **Milestone test coverage**: Added 8 comprehensive test cases for estimated finish time feature:
  - `test_milestone_tracking`: Verifies milestones are tracked at 5% intervals
  - `test_milestone_not_shown_twice`: Ensures same milestone doesn't show twice
  - `test_milestone_increments_correctly`: Tests all 5% milestones (5%, 10%, 15%, etc.)
  - `test_estimated_finish_time_format`: Validates time format ("%I:%M %p")
  - `test_milestone_display_all_strategies`: Tests milestone display across StandardStrategy, SmallChunkStrategy, and AdaptiveStrategy
  - `test_milestone_uniqueness_all_strategies`: Verifies no duplicate milestones across all strategies
  - `test_milestone_initialization_on_resume`: Tests last_milestone calculation for various resume positions (0%, 12%, 47%, 5%, 99%)
  - `test_milestone_not_repeated_after_resume`: Verifies milestones aren't repeated when resuming from previous position

### Changed
- **Test count**: Increased to 145 unit tests (up from 137)
- **Test coverage**: test_wipe_strategy.py now has 833 lines (was 303)
- **Cross-strategy validation**: Milestone feature now verified on all three wiping strategies
- **Resume functionality**: Milestone tracking now properly resumes from last completed milestone

## [1.3.0] - 2025-10-11

### Added
- **WipeStrategy Class Architecture**: Major refactoring of wiping logic into object-oriented strategy pattern
  - **WipeStrategy abstract base class**: Common functionality for all wiping strategies
  - **StandardStrategy**: Fixed chunk size wiping for general use
  - **SmallChunkStrategy**: Optimized for slow drives with smaller chunks
  - **AdaptiveStrategy**: Dynamic chunk sizing based on disk position and speed
  - **Backward compatibility**: Original `wipe_device()` function maintained as wrapper
  - **New test suite**: `test_wipe_strategy.py` with comprehensive unit tests
- **DiskPretest Class**: Refactored HDD pretest functionality into reusable class
  - **DiskPretest class**: Encapsulated pretest logic with testable methods
  - **PretestResults dataclass**: Structured pretest outcome data
  - **Quiet mode support**: Non-interactive pretest execution
  - **Backward compatibility**: Original `perform_hdd_pretest()` function maintained as wrapper
  - **New test suite**: `test_disk_pretest.py` with comprehensive unit tests

### Changed
- **Code organization**: Better separation of concerns with class-based architecture
- **Test coverage**: Increased overall test coverage to 95% (from 82%)
- **Maintainability**: Easier to extend and modify wiping and pretest algorithms
- **Version bump**: Updated from 1.2.0 to 1.3.0 across all files

### Technical
- **137 unit tests** passing (up from 29)
- **Class-based design**: Follows Strategy Pattern for extensibility
- **Comprehensive mocking**: Isolated unit tests for all new classes
- **Style compliance**: All code adheres to 79-character line limit
- **Zero linting errors**: Clean code passing all style checks

## [1.2.0] - 2025-01-11

### Added
- **Comprehensive Codebase Reports**: New `make reports` target providing detailed project statistics
  - **File structure analysis**: Total files, Python files, documentation, configuration files
  - **Code metrics**: Lines of code, documentation lines, file sizes
  - **Code coverage analysis**: Detailed coverage reports with missing line information
  - **Security analysis**: Bandit security scan and Safety dependency vulnerability check
  - **Dependency analysis**: Runtime, development, and build system dependencies from pyproject.toml
  - **Complexity analysis**: Class and function counts with names (codebase vs test separation)
  - **Code style summary**: Longest lines detection and style compliance
  - **Virtual environment exclusion**: Properly excludes .venv and venv directories from analysis
- **Enhanced Makefile**: Improved help system with detailed target descriptions and usage examples
- **Professional terminology**: Updated reports to use "codebase" instead of "non-test" for clarity

### Changed
- **Version bump**: Updated from 1.1.0 to 1.2.0 across all files
- **Documentation updates**: Updated README, TESTDESIGN.md, and CHANGES.md with new version references
- **Code style improvements**: Enhanced Makefile formatting and organization

### Fixed
- **Bandit configuration**: Resolved .bandit file parsing issues for security scans
- **Report accuracy**: Fixed dependency parsing and class/function name extraction in reports
- **Virtual environment handling**: Properly excluded virtual environment code from codebase analysis

## [1.1.0] - 2025-01-27

### Added
- **🚨 CRITICAL SAFETY FEATURE: Mount Detection and Prevention**
  - **Automatic mount checking**: Detects if target device or partitions are mounted
  - **Immediate termination**: STOPS EXECUTION if mounted devices are detected
  - **Detailed mount information**: Shows exactly which partitions are mounted and where
  - **Clear unmount instructions**: Provides step-by-step commands to safely unmount devices
  - **Comprehensive safety warnings**: Explains risks of wiping mounted devices
  - **Prevents data corruption**: Protects against accidental loss of important data
- **Enhanced mount checking tests**: 6 new test cases covering all mount detection scenarios
- **Updated documentation**: Added comprehensive mount safety section to README

### Changed
- **Safety workflow**: Mount check now runs before any wiping operations
- **Error handling**: Improved mount status detection with better error handling
- **User experience**: Clear, actionable error messages when devices are mounted

### Fixed
- **Safety gap**: Previously only warned about mounted devices, now prevents execution
- **Test coverage**: Added comprehensive testing for mount checking functionality

## [1.0.0] - 2025-01-27

### Added
- **Major version milestone**: First stable release of wipeit
- **Comprehensive CI/CD pipeline**: Full GitHub Actions integration with testing, linting, and security scanning
- **Enhanced documentation**: Complete architecture documentation, CI/CD guide, and safety setup instructions
- **Local development tools**: Makefile with targets for testing, linting, security scanning, and pre-commit preparation

### Changed
- **CI/CD improvements**: Removed code formatting from GitHub Actions, focusing on testing and quality checks
- **Documentation updates**: Updated all documentation to reflect current CI/CD practices and tool usage
- **Release process**: Streamlined release checklist with version update reminders

### Fixed
- **Critical bug fixes**: Fixed float-to-integer conversion issues in adaptive chunking algorithm
- **Test coverage**: Expanded test suite with comprehensive coverage of HDD pretest and adaptive chunking
- **Version consistency**: Ensured all files maintain consistent version numbering

### Security
- **Security scanning**: Integrated bandit and safety security tools with proper configuration
- **Dependency management**: Updated dependency requirements and security scanning setup

## [0.4.0] - 2025-10-10

### Added
- **Enhanced output formatting with section headings and bullet points**:
  - Clear section headings with visual separators for all major sections
  - Professional bullet point formatting throughout the output
  - Improved visual hierarchy and readability
  - Better organization of device information, configuration, pretest, and progress sections

### Changed
- **Output format improvements**:
  - Replaced emoji icons with clean bullet points (•) for professional appearance
  - Added section headings: DEVICE INFORMATION, CONFIGURATION, HDD PRETEST, PRETEST ANALYSIS, WIPING PROCESS, WIPE COMPLETED, WIPE INTERRUPTED
  - Enhanced progress bar display with better visual indicators
  - Improved completion and interruption messages with clear formatting
  - Maintained all functionality while significantly improving user experience

### Fixed
- **Test compatibility**: Updated test assertions to match new section heading format
- **Code formatting**: Ensured all new formatting code complies with programming style guide

## [0.3.1] - 2025-10-10

### Added
- **Comprehensive test coverage for HDD pretest and adaptive chunk functionality**:
  - New `TestHDDPretest` class with 3 test cases covering pretest scenarios
  - New `TestWipeDeviceIntegration` class with 2 test cases for adaptive chunk algorithm
  - Total test count increased from 29 to 34 tests
  - **CRITICAL BUG TEST**: Explicit test for float-to-integer conversion in adaptive chunk sizing
- **Security scanning improvements**:
  - Migration to Safety CLI 3.x with `safety scan` command (replaces deprecated `safety check`)
  - New `make security` command for running bandit and safety security scans
  - Bandit configuration file (`bandit.yaml`) to suppress expected issues in system tools
  - Safety CLI setup documentation (`DOCS/SAFETY_SETUP.md`) with authentication guide

### Fixed
- **Critical bug**: Float-to-integer conversion error in adaptive chunk sizing
  - Fixed `TypeError: 'float' object cannot be interpreted as an integer` in `wipe_device()`
  - Added explicit `int()` casting for `current_chunk_size` calculations
  - Bug would have been caught by new comprehensive test coverage
- **Line length violations** in new test cases (79-character limit compliance)

### Changed
- Test coverage now includes all critical code paths for HDD pretest feature
- Enhanced test mocking for realistic HDD pretest simulation
- Improved error messages in test assertions

## [0.3.0] - 2025-01-16

### Added
- **Makefile with comprehensive targets**:
  - `make tests` - Run comprehensive test suite with style checks
  - `make lint` - Run flake8 style checks with 79-character line limit
  - `make pre-git-prep` - Prepare code for git commit by fixing style issues
  - `make info` - Display help information for all targets
- **GitHub Actions integration** - All workflows now use Makefile targets for consistency
- **Architecture documentation** (ARCH.md) with Mermaid function call graph
- **Programming style guide compliance** - All code follows 79-character line limit
- **Enhanced test coverage** - All 29 unit tests pass with 0 linting errors

### Changed
- **Code formatting** - All Python files now comply with programming style guide
- **CI/CD workflows** - Updated to use centralized Makefile targets
- **Documentation structure** - All .md files organized in DOCS/ directory

### Fixed
- **Line length violations** - All files now within 79-character limit
- **Import organization** - Cleaned up unused imports in test files
- **Test integrity** - Preserved all test functionality while fixing style issues

## [0.2.0] - 2025-01-16

### Added
- **Comprehensive testing infrastructure** with 29 unit tests
- **Test design documentation** (TESTDESIGN.md) with complete testing strategy
- **GitHub Actions CI/CD pipeline** with 4 workflows:
  - CI Pipeline for fast feedback
  - Comprehensive Tests with quality checks
  - Release Pipeline for automated publishing
  - Status Monitoring for health checks
- **Code quality tools**: linting, formatting, security scanning
- **Issue and PR templates** for better project management
- **Dependabot configuration** for automated dependency updates
- **CI/CD documentation** (DOCS/CI-CD.md)
- **Local CI testing script** (test-ci.sh)
- **Status badges** in README for CI/CD visibility
- **Estimated finish time display** at 5% progress milestones

### Changed
- Enhanced project documentation with development section
- Improved README with CI/CD badges and contributing guidelines
- Updated GitHub Actions workflows for better automation

### Technical
- **Test Coverage**: 82% overall coverage with comprehensive mocking
- **Multi-Python Support**: Tests on Python 3.8, 3.9, 3.10, 3.11, 3.12
- **Quality Gates**: Automated linting, formatting, and security checks
- **Release Automation**: Tag-based GitHub releases with automated testing and building
- **Progress Enhancement**: Estimated finish time displayed at 5% milestones (e.g., "Estimated Finish Time: 3:15 PM")

## [0.1.0] - 2025-10-01

### Added
- Initial release of wipeit
- Device listing functionality with detailed information
- Secure device wiping with random data overwriting
- Real-time progress display with speed and ETA
- Safety checks for mounted devices
- Root/sudo privilege verification
- Confirmation prompt before wiping
- Support for keyboard interrupt (Ctrl+C)
- Chunked writing for memory efficiency (100 MB default)
- **Configurable buffer size** with `-b/--buffer-size` option
  - Support for M, G, T suffixes (megabytes, gigabytes, terabytes)
  - Valid range: 1M to 1T
  - Default: 100M
  - Example: `wipeit -b 1G /dev/sdx`
- **Resume functionality** with `--resume` option
  - Automatic progress saving every 1GB or 10 chunks
  - Graceful interruption handling with Ctrl+C (immediate response)
  - Resume from exact interruption point
  - Progress file stored as `wipeit_progress.json` (current directory)
  - 24-hour expiry for progress files
  - Immediate write flushing and syncing for responsive interruption
  - Example: `wipeit --resume /dev/sdx`
- **Version information** with `-v/--version` option
  - Shows current version number
  - Example: `wipeit --version` outputs `wipeit 0.1.0`
- **Pending operations display** when running without arguments
  - Automatically detects and displays interrupted wipe operations
  - Shows progress percentage, written data, buffer size, and start time
  - Provides exact resume commands for each pending operation
  - Works without root privileges for checking pending operations

### Features
- Display device information: size, model, serial number
- Show partition layout and mount points
- Warn users about mounted devices
- Progress tracking with percentage, written GB, speed (MB/s), ETA, and buffer size
- Flexible buffer size configuration for performance tuning
- Size parser supports decimal values (e.g., `0.5G` for 512 MB)

### Security
- Mandatory root user check before execution
- Explicit confirmation required before wiping
- Mount status verification to prevent accidental data loss

### Performance
- Adjustable buffer size allows optimization for different device types
- Larger buffers can improve write speeds on fast devices
- Memory-efficient chunked writing prevents excessive RAM usage

### Documentation
- Comprehensive performance recommendations section
  - Expected write speeds for all device types
  - Time estimates by device size (16GB to 4TB)
  - Buffer size optimization guidelines
  - System requirements for optimal performance
  - I/O scheduler recommendations
  - 6 performance optimization tips
  - Troubleshooting guide for performance issues
  - Real-world performance comparison data
  - Multiple device wiping strategies
- Table of contents for easy navigation
- Device-specific buffer size examples

