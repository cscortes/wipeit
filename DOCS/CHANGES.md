# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

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
- **Release Automation**: Tag-based PyPI publishing ready
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
  - Progress files stored in `wipeit_progress_[device].json` (current directory)
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

