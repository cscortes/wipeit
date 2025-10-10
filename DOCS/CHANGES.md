# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

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
  - Graceful interruption handling with Ctrl+C
  - Resume from exact interruption point
  - Progress files stored in `wipeit_progress_[device].json` (current directory)
  - 24-hour expiry for progress files
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

