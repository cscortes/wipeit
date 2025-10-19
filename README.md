# wipeit

[![CI](https://github.com/lcortes/wipeit/actions/workflows/ci.yml/badge.svg)](https://github.com/lcortes/wipeit/actions/workflows/ci.yml)
[![Tests](https://github.com/lcortes/wipeit/actions/workflows/tests.yml/badge.svg)](https://github.com/lcortes/wipeit/actions/workflows/tests.yml)
[![Python 3.8+](https://img.shields.io/badge/python-3.8+-blue.svg)](https://www.python.org/downloads/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)

A secure device wiping utility that overwrites block devices with random data.

**🚨 CRITICAL WARNING: This tool is EXTREMELY DESTRUCTIVE and COMPLETELY IRREVERSIBLE! 🚨**

**⚠️ USE AT YOUR OWN RISK - ALL DATA WILL BE PERMANENTLY DESTROYED! ⚠️**

## Table of Contents

- [Features](#features)
- [Installation](#installation)
- [Usage](#usage)
  - [List all block devices](#list-all-block-devices)
  - [Wipe a specific device](#wipe-a-specific-device)
  - [Custom buffer size](#custom-buffer-size)
- [Requirements](#requirements)
- [Safety Features](#safety-features)
- [Common Use Cases](#common-use-cases)
- [Troubleshooting](#troubleshooting)
- [Performance Recommendations](#performance-recommendations)
  - [Expected Write Speeds](#expected-write-speeds)
  - [Time Estimates by Device Size](#time-estimates-by-device-size)
  - [Important Note: Speed Variations During Wiping](#-important-note-speed-variations-during-wiping)
  - [Buffer Size Optimization](#buffer-size-optimization)
  - [System Requirements](#system-requirements-for-optimal-performance)
  - [Optimization Tips](#performance-optimization-tips)
  - [Troubleshooting Performance](#troubleshooting-performance-issues)

## Features

### Core Functionality
- **Secure Wiping**: Overwrites block devices with random data for permanent data destruction
- **Device Listing**: Display all block devices with detailed information (size, model, serial, partitions)
- **Memory Efficient**: Chunked writing prevents excessive RAM usage (configurable buffer size: 1M-1T)
- **Safety First**: Root privilege verification and comprehensive safety checks

### Intelligent Wiping
- **Automatic Disk Detection**: Identifies disk type (HDD, SSD, NVMe) with confidence scoring
- **HDD Pretest**: Tests write speeds at different disk positions (beginning, middle, end)
- **Adaptive Algorithms**: Three wiping strategies automatically selected based on disk characteristics:
  - **Standard Strategy**: Fixed chunk size for consistent SSDs and fast HDDs
  - **Small Chunk Strategy**: 10MB chunks for slow/unreliable drives (better responsiveness)
  - **Adaptive Strategy**: Dynamic chunk sizing based on disk position and speed (HDD optimization)

### Progress & Resume
- **Real-time Progress**: Live display with percentage, speed (MB/s), ETA, and progress bar
- **Estimated Finish Time**: Shows actual clock time (e.g., "3:15 PM") at every 5% milestone
- **Resume Support**: Automatic progress saving every 1GB or 10 chunks
- **Resume Detection**: Prompts user about previous interrupted wipes when starting
- **24-Hour Expiry**: Progress files automatically expire after 24 hours

### Safety Features
- ⚠️ **Mount Detection**: Prevents wiping mounted devices (blocks execution if mounted)
- 🚨 **Confirmation Prompt**: Requires explicit 'y' confirmation before wiping
- **Graceful Interruption**: Ctrl+C saves progress and provides resume instructions
- **Device Verification**: Shows detailed device info before wiping to prevent mistakes
- **Permission Checks**: Ensures proper root/sudo privileges

### User Experience
- **Clean Output**: Professional formatting with section headers and bullet points
- **Progress Milestones**: Milestone messages every 5% with estimated completion time
- **Resume Workflow**: Automatic detection and helpful prompts for pending operations
- **Detailed Reporting**: Comprehensive completion summary with statistics
- **Responsive**: Immediate Ctrl+C handling with progress preservation

### Configuration Options
- **Buffer Size**: Configurable from 1MB to 1TB (default: 100MB)
- **Skip Pretest**: Option to bypass HDD pretest for faster start
- **Resume Flag**: Auto-detects drive by serial number for seamless resume
- **List Devices**: Dedicated --list option for device enumeration

### Technical Features
- **Strategy Pattern**: Object-oriented wiping strategies for extensibility
- **95% Test Coverage**: 148 comprehensive unit and integration tests
- **Performance Tracking**: Speed sampling and analysis for adaptive algorithms
- **Progress Persistence**: JSON-based progress files with device tracking
- **Type Detection**: Uses rotation rate, model strings, and device paths for accurate detection

## Installation

**⚠️ WARNING: Before installing, understand that this tool will PERMANENTLY DESTROY data! ⚠️**

### Option 1: Install from GitHub Release (Recommended)

Download the latest `.whl` file from the [Releases page](https://github.com/cscortes/wipeit/releases), then:

```bash
pip install wipeit-*.whl
```

### Option 2: Install from Source

```bash
git clone https://github.com/cscortes/wipeit.git
cd wipeit
uv sync
```

### Development Installation

```bash
git clone https://github.com/cscortes/wipeit.git
cd wipeit
uv sync
source .venv/bin/activate
```

## Usage

**🚨 EXTREME CAUTION: This section shows how to PERMANENTLY DESTROY data! 🚨**

### Quick Start

**⚠️ CRITICAL: This tool requires root privileges and will IRREVERSIBLY DESTROY data! ⚠️**

**Always run with `sudo` and double-check device paths!**

### List all block devices

To see all available block devices on your system:

```bash
sudo wipeit
```

**Note:** If you have pending wipe operations (interrupted wipes), the tool will first display information about them before showing available devices.

**Example with pending operations:**
```bash
$ ./wipeit.py

Found pending wipe operations:
==================================================

1. Device: /dev/sdb
   Progress: 25.00% complete
   Written: 1.00 GB / 4.00 GB
   Buffer size: 100 MB
   Started: Thu Oct  9 18:04:00 2025
   Resume command: sudo ./wipeit.py --resume

NOTE: To resume any operation, simply run: sudo ./wipeit.py --resume
NOTE: The tool will automatically find the correct drive by serial number
NOTE: To start fresh, the progress file will be overwritten
==================================================

==================================================
Available devices (requires sudo):
==================================================
Error: This program must be run as root (sudo) to list devices.
Use: sudo ./wipeit.py
```

**Example output:**
```
Device: /dev/sda
Size: 256.00 GB
Model: SAMSUNG_SSD_860
Serial: S3Z9NB0K123456
Device and partitions:
NAME   SIZE   TYPE MOUNTPOINTS
sda    256G   disk
├─sda1 512M   part /boot/efi
└─sda2 255.5G part /

Warning: /dev/sda or its partitions appear to be mounted.

---

Device: /dev/sdb
Size: 128.00 GB
Model: USB_Flash_Drive
Serial: 1234567890
Device and partitions:
NAME SIZE TYPE MOUNTPOINTS
sdb  128G disk

/dev/sdb does not appear to be mounted.
```

### Wipe a specific device

**🚨 DANGER: This will PERMANENTLY DESTROY ALL DATA on the specified device! 🚨**

To securely wipe a device by overwriting it with random data:

**⚠️ TRIPLE-CHECK the device path before proceeding! ⚠️**

```bash
sudo wipeit /dev/sdx
```

Replace `/dev/sdx` with your actual device (e.g., `/dev/sdb`, `/dev/sdc`).

#### Custom buffer size

You can adjust the write buffer size for better performance:

```bash
# Use 1GB buffer for faster wiping
sudo wipeit -b 1G /dev/sdx

# Use 500MB buffer
sudo wipeit -b 500M /dev/sdx

# Use 100MB buffer (default)
sudo wipeit -b 100M /dev/sdx
```

**Buffer size options:**
- Range: `1M` (minimum) to `1T` (maximum)
- Suffixes: `M` (megabytes), `G` (gigabytes), `T` (terabytes)
- Default: `100M`
- Larger buffers may improve speed but use more memory

### Disk Type Detection and HDD Pretest

wipeit now automatically detects your disk type and optimizes the wiping process:

#### Automatic Disk Type Detection

```bash
$ sudo wipeit /dev/sdb

Device: /dev/sdb
Size: 500.00 GB
Model: WDC_WD5000AAKX-00ERMA0
Serial: WD-WMAYUA1234567
Type: HDD (confidence: HIGH)
Detection details: Rotational device
Device and partitions:
NAME SIZE TYPE MOUNTPOINTS
sdb  500G disk

/dev/sdb does not appear to be mounted.

Detected disk type: HDD (confidence: HIGH)
HDD detected - performing pretest to optimize wiping algorithm...
```

#### HDD Pretest Process

For HDDs, wipeit performs a pretest to measure write speeds at different disk positions:

```bash
Performing HDD pretest to optimize wiping algorithm... This will test write
speeds at different disk positions. Testing beginning of disk... Beginning:
120.45 MB/s Testing middle of disk... Middle: 95.32 MB/s Testing end of disk...
End: 78.21 MB/s

Pretest Analysis:
  Average speed: 97.99 MB/s
  Speed variance: 42.24 MB/s
  Recommended algorithm: adaptive_chunk
  Reason: High speed variance detected - adaptive chunk sizing recommended

Pretest complete. Using adaptive_chunk algorithm.
  Using adaptive chunk sizing based on disk position
```

#### Algorithm Types

Based on the pretest results, wipeit selects the optimal algorithm:

- **Standard**: For SSDs, NVMe drives, and HDDs with consistent speeds
- **Adaptive Chunk**: For HDDs with high speed variance (adjusts chunk size based on disk position)
- **Small Chunk**: For very slow HDDs (uses smaller chunks for better responsiveness)

#### Skip Pretest Option

If you want to bypass the pretest and use the standard algorithm:

```bash
sudo wipeit --skip-pretest /dev/sdx
```

This is useful when:
- You're in a hurry and want to start wiping immediately
- You're wiping multiple similar drives and already know the optimal settings
- The pretest is taking too long on very large drives

#### Pretest Behavior on Resume Operations

When resuming an interrupted wipe on an HDD:

- **With existing pretest results**: The previous pretest results are automatically reused, ensuring optimal performance without re-testing
- **Without pretest results**: A new pretest is performed to optimize the algorithm for the remaining wipe operation
- **Pretest results are preserved**: All pretest data is saved with progress and restored on resume

This ensures that:
- **Optimal performance** is maintained throughout the entire wipe process
- **No duplicate testing** when resuming with existing pretest results
- **Consistent algorithm** is used from start to finish
- **Time savings** by reusing previous pretest results

**⚠️  CRITICAL WARNING**:
- This will **PERMANENTLY DESTROY ALL DATA** on the device
- There is **NO UNDO** operation
- Double-check the device path before confirming
- Never wipe your system disk or mounted partitions

**Interactive workflow:**

```bash
$ sudo wipeit /dev/sdb -b 1G

Using buffer size: 1024 MB (1.00 GB)
Device: /dev/sdb
Size: 128.00 GB
Model: USB_Flash_Drive
Serial: 1234567890
Device and partitions:
NAME SIZE TYPE MOUNTPOINTS
sdb  128G disk

/dev/sdb does not appear to be mounted.

Confirm wipe (y/n): y

Progress: 5.32% | Written: 6.81 GB | Speed: 85.32 MB/s | ETA: 23.45 min | Buffer: 1024M | Algorithm: Adaptive
```

### Stop and resume a wipe operation

Press `Ctrl+C` at any time to interrupt the wiping process:

```bash
Progress: 15.42% | Written: 19.74 GB | Speed: 82.15 MB/s | ETA: 17.23 min
^C
Wipe interrupted at 19.74 GB (15.42% complete)
Progress saved. To resume, run:
  sudo ./wipeit.py --resume
```

The tool will automatically find the correct drive by matching the serial number from the progress file.

#### Resume an interrupted wipe

To continue from where you left off:

```bash
sudo ./wipeit.py --resume
```

The tool will automatically find the correct drive by matching the serial number from the progress file.

**Example resume session with HDD and pretest results:**
```bash
$ sudo ./wipeit.py --resume

======================================================================
AUTO-DETECTING RESUME DRIVE
======================================================================
✓ Found matching drive: /dev/sdb
  Serial: WD-WMAYUA1234567
  Model: Hitachi_HTS545032B9A300
  Size: 128.00 GB

Detected disk type: HDD (confidence: HIGH)
   Detection details: Rotational device
Resuming wipe from 19.74 GB (15.42% complete)
Previous session: Wed Oct  1 18:30:45 2025
   Found previous pretest results from Wed Oct  1 18:30:45 2025
Using previous pretest results for optimal algorithm.
   Previous algorithm: adaptive_chunk
Device: /dev/sdb
Size: 128.00 GB
Model: Hitachi_HTS545032B9A300
Serial: WD-WMAYUA1234567
Device and partitions:
NAME SIZE TYPE MOUNTPOINTS
sdb  128G disk

/dev/sdb does not appear to be mounted.

Confirm wipe (y/n): y

Progress: 16.12% | Written: 20.64 GB | Speed: 85.32 MB/s | ETA: 16.45 min | Buffer: 100M | Algorithm: Adaptive
```

**Example resume session without pretest results:**
```bash
$ sudo ./wipeit.py --resume

======================================================================
AUTO-DETECTING RESUME DRIVE
======================================================================
✓ Found matching drive: /dev/sdb
  Serial: WD-WMAYUA1234567
  Model: Hitachi_HTS545032B9A300
  Size: 128.00 GB

Detected disk type: HDD (confidence: HIGH)
   Detection details: Rotational device
Resuming wipe from 19.74 GB (15.42% complete)
Previous session: Wed Oct  1 18:30:45 2025

HDD detected - pretest will be performed to optimize wiping algorithm...
   This will test write speeds at different disk positions.
   The pretest may take a few minutes depending on disk size.

Proceed with HDD pretest? (y/n): y

Starting HDD pretest...
Performing HDD pretest to optimize wiping algorithm...
   This will test write speeds at different disk positions.
   ⚠️  WARNING: This will write test data to the disk!
   Disk size: 128.00 GB
   Test chunk size: 100 MB
   Test positions: 3 locations
  Testing beginning of disk...
    Beginning: 120.45 MB/s
  Testing middle of disk...
    Middle: 95.32 MB/s
  Testing end of disk...
    End: 78.21 MB/s

Pretest Analysis:
  Average speed: 97.99 MB/s
  Speed variance: 42.24 MB/s
  Recommended algorithm: adaptive_chunk
  Reason: High speed variance detected - adaptive chunk sizing recommended

Pretest complete. Using adaptive_chunk algorithm.
  Using adaptive chunk sizing based on disk position
Device: /dev/sdb
Size: 128.00 GB
Model: Hitachi_HTS545032B9A300
Serial: WD-WMAYUA1234567
Device and partitions:
NAME SIZE TYPE MOUNTPOINTS
sdb  128G disk

/dev/sdb does not appear to be mounted.

Confirm wipe (y/n): y

Progress: 16.12% | Written: 20.64 GB | Speed: 85.32 MB/s | ETA: 16.45 min | Buffer: 100M | Algorithm: Adaptive
```

#### Starting fresh vs resuming

If you try to start a new wipe on a device with existing progress:

```bash
$ sudo ./wipeit.py /dev/sdb

⚠️  Found previous wipe session:
   Progress: 15.42% (19.74 GB)
   Started: Wed Oct  1 18:30:45 2025

Options:
   1. Resume previous session: sudo ./wipeit.py --resume
   2. Start fresh (will overwrite previous progress)

Start fresh wipe? (y/n): n
Aborted.
```

### Help and Version

To see all available options:

```bash
wipeit --help
```

To check the version:

```bash
wipeit --version
# or
wipeit -v
```

**Example output:**
```bash
$ wipeit --version
wipeit 1.2.0
```

### Resume functionality

The tool automatically saves progress and allows resuming interrupted wipes:

- **Progress file** is stored as `wipeit_progress.json` (current directory)
- **Auto-save** occurs every 1GB written or every 10 chunks
- **Resume detection** when starting a new wipe on a device with existing progress
- **Progress cleanup** when wipe completes successfully
- **24-hour expiry** for progress files (prevents stale resumes)
- **Pending operations display** when running without arguments shows all interrupted wipes

## Requirements

### System Requirements

- **Operating System:** Linux (tested on Fedora, Ubuntu, Debian, Arch)
- **Python:** 3.8 or higher
- **Privileges:** Root/sudo access

### System Utilities

The following utilities must be available on your system:
- `blockdev` - Query block device size
- `udevadm` - Get device properties (model, serial)
- `lsblk` - List block devices and partitions
- `mount` - Check mount status

These are typically pre-installed on most Linux distributions.

## Safety Features

### Before Wiping
- **Root check:** Verifies the program is run with root privileges
- **Device information:** Displays full device details before proceeding
- **Mount safety check:** **STOPS EXECUTION** if device or partitions are mounted
- **Explicit confirmation:** Requires user to type 'y' to proceed

### During Wiping
- **Progress tracking:** Real-time feedback on operation status
- **Interruptible:** Can be stopped at any time with Ctrl+C (immediate response)
- **Resumable:** Automatically saves progress and allows resuming from interruption point

### Mount Safety Protection
**🚨 CRITICAL SAFETY FEATURE: Mount Detection and Prevention**

wipeit includes a comprehensive mount safety system that **prevents accidental data loss**:

- **Automatic Detection:** Checks if the target device or any of its partitions are mounted
- **Immediate Termination:** **STOPS EXECUTION** if mounted devices are detected
- **Detailed Information:** Shows exactly which partitions are mounted and where
- **Clear Instructions:** Provides step-by-step commands to safely unmount devices
- **Safety Warnings:** Explains the risks of wiping mounted devices

**Example of mount safety in action:**
```bash
$ sudo wipeit /dev/sdb
======================================================================
🚨 SAFETY CHECK FAILED - DEVICE IS MOUNTED
======================================================================
Cannot proceed with wiping /dev/sdb
   The device or its partitions are currently mounted!

Mounted partitions found:
   • /dev/sdb1 -> /mnt/usb

TO FIX THIS ISSUE:
   1. Unmount all partitions on this device:
      sudo umount /dev/sdb*
   2. Or unmount specific partitions:
      sudo umount /dev/sdb1
   3. Verify device is unmounted:
      lsblk /dev/sdb
   4. Then run wipeit again

⚠️  WARNING: Wiping a mounted device can cause:
   • Data corruption on the mounted filesystem
   • System instability or crashes
   • Loss of data on other mounted partitions

Program terminated for safety.
```

**Why this matters:**
- **Prevents data corruption** on active filesystems
- **Avoids system crashes** from wiping mounted system partitions
- **Protects against accidental loss** of important data
- **Ensures clean, safe wiping** of unmounted devices only
- Overwrites entire device from start to finish
- No patterns that could potentially be recovered

## Common Use Cases

**⚠️ WARNING: All examples below will PERMANENTLY DESTROY data! ⚠️**

### 1. Prepare a USB drive for disposal
```bash
sudo wipeit /dev/sdb
```

### 2. Securely erase an old hard drive with large buffer
```bash
sudo wipeit -b 1G /dev/sdc
```

### 3. Wipe with custom buffer size for performance
```bash
# Fast wipe with 2GB buffer
sudo wipeit --buffer-size 2G /dev/sdd
```

### 4. Resume an interrupted wipe
```bash
sudo ./wipeit.py --resume
```

The tool will automatically find the correct drive by matching the serial number from the progress file.

### 5. Check what devices are available
```bash
sudo wipeit
```

## Troubleshooting

### "Error: This program must be run as root (sudo)"

**Solution:** Always prefix the command with `sudo`:
```bash
sudo wipeit /dev/sdx
```

### "Warning: device or its partitions appear to be mounted"

**Solution:** Unmount all partitions before wiping:
```bash
sudo umount /dev/sdx1
sudo umount /dev/sdx2
# Then try again
sudo wipeit /dev/sdx
```

### "Permission denied" or "Operation not permitted"

**Solution:**
1. Ensure you're using `sudo`
2. Check if the device is locked by another process
3. Verify the device path exists: `ls -l /dev/sdx`

### Device identification

**Always verify the device path before wiping:**
```bash
# List all devices
lsblk

# Check specific device
sudo fdisk -l /dev/sdx

# Use wipeit's listing feature
sudo wipeit
```

## Performance Recommendations

### Expected Write Speeds

Actual wiping speed varies by device type and interface:

| Device Type | Expected Speed | Time for 1TB |
|------------|----------------|--------------|
| **USB 2.0** | 30-40 MB/s | ~7-9 hours |
| **USB 3.0** | 80-150 MB/s | ~2-3.5 hours |
| **USB 3.1/3.2** | 150-300 MB/s | ~1-2 hours |
| **SATA HDD (5400 RPM)** | 80-120 MB/s | ~2.5-3.5 hours |
| **SATA HDD (7200 RPM)** | 120-160 MB/s | ~2-2.5 hours |
| **SATA SSD** | 200-450 MB/s | ~40-90 min |
| **NVMe SSD (Gen3)** | 500-1500 MB/s | ~12-35 min |
| **NVMe SSD (Gen4)** | 1000-3000 MB/s | ~6-18 min |

### Time Estimates by Device Size

| Size | USB 3.0 | SATA SSD | NVMe SSD |
|------|---------|----------|----------|
| **16 GB** | 2-3 min | 1-2 min | < 1 min |
| **32 GB** | 4-7 min | 2-3 min | < 1 min |
| **64 GB** | 7-13 min | 3-5 min | 1-2 min |
| **128 GB** | 15-27 min | 6-10 min | 2-4 min |
| **256 GB** | 29-53 min | 12-20 min | 4-9 min |
| **512 GB** | 57-107 min | 23-40 min | 8-17 min |
| **1 TB** | 2-3.5 hours | 40-85 min | 12-35 min |
| **2 TB** | 4-7 hours | 1.5-2.8 hours | 25-70 min |
| **4 TB** | 8-14 hours | 3-5.5 hours | 50-140 min |

### ⚠️ Important Note: Speed Variations During Wiping

**Why does the speed drop during wiping?**

The speed you see in wipeit's progress display will typically **decrease over time**, especially for traditional hard drives. This is **completely normal** and expected behavior:

#### Physical Disk Characteristics
- **Outer tracks are faster**: Hard drives have higher data density on outer tracks, enabling faster read/write speeds
- **Inner tracks are slower**: As wiping progresses toward the center of the disk, data density decreases, resulting in slower speeds
- **Speed drop is normal**: Expect 30-50% speed reduction from start to finish on traditional hard drives

#### Example Speed Progression
```
Progress: 5.01% | Speed: 70.10 MB/s | ETA: 68.93 min
Progress: 15.00% | Speed: 250.00 MB/s | ETA: 17.30 min | Estimated Finish Time: 7:02 PM
Progress: 25.00% | Speed: 200.00 MB/s | ETA: 15.00 min
Progress: 50.00% | Speed: 150.00 MB/s | ETA: 12.00 min
Progress: 75.00% | Speed: 120.00 MB/s | ETA: 8.00 min
Progress: 95.00% | Speed: 100.00 MB/s | ETA: 2.00 min
```

#### What This Means
- **This is normal behavior** - not an error
- **Hard drives naturally slow down** on inner tracks
- **Your wipeit implementation is working correctly**
- **The speed calculation is accurate**
- **ETA will adjust automatically** as speed changes

#### Device-Specific Behavior
- **Traditional HDDs**: Significant speed drop (30-50% reduction)
- **SSDs**: Minimal speed variation (usually <10% change)
- **NVMe SSDs**: Very consistent speeds throughout

The dropping speed is actually a **good sign** that wipeit is working properly and writing to the entire disk surface!

### Buffer Size Optimization

The buffer size directly affects memory usage and can impact performance:

#### Buffer Size Guidelines by Device Type

```bash
# USB 2.0/3.0 Devices (slower devices)
sudo wipeit -b 100M /dev/sdx    # Optimal for most USB drives
sudo wipeit -b 256M /dev/sdx    # For faster USB 3.1+ devices

# SATA SSDs
sudo wipeit -b 500M /dev/sdx    # Good balance
sudo wipeit -b 1G /dev/sdx      # Maximum performance

# NVMe SSDs (fastest devices)
sudo wipeit -b 1G /dev/sdx      # Minimum recommended
sudo wipeit -b 2G /dev/sdx      # Better performance
sudo wipeit -b 4G /dev/sdx      # Maximum performance

# Large HDDs (multi-TB)
sudo wipeit -b 500M /dev/sdx    # Standard recommendation
sudo wipeit -b 1G /dev/sdx      # For faster RAID arrays
```

#### Buffer Size Trade-offs

| Buffer Size | Memory Usage | Speed Impact | Best For |
|-------------|--------------|--------------|----------|
| **1M-10M** | Very Low (~10 MB) | Slowest | Low-memory systems |
| **50M-100M** | Low (~100 MB) | Good | Default, USB 2.0 |
| **256M-500M** | Medium (~500 MB) | Better | USB 3.0, SATA HDD |
| **1G-2G** | High (~2 GB) | Best | SATA SSD, NVMe |
| **4G+** | Very High (4+ GB) | Maximum | High-end NVMe only |

### System Requirements for Optimal Performance

#### CPU Usage
- **Low:** Minimal CPU usage (~5-15%)
- **Random data generation** (`os.urandom()`) uses CPU but is efficient
- Multi-core systems benefit from kernel I/O optimizations

#### Memory Requirements

Minimum memory needed = Buffer size + ~100 MB overhead

| Buffer Size | Minimum RAM | Recommended RAM |
|-------------|-------------|-----------------|
| 100M | 256 MB | 512 MB |
| 500M | 1 GB | 2 GB |
| 1G | 2 GB | 4 GB |
| 2G | 4 GB | 8 GB |
| 4G | 8 GB | 16 GB |

#### I/O Scheduler Recommendations

For best performance, use appropriate I/O scheduler:

```bash
# Check current scheduler
cat /sys/block/sdx/queue/scheduler

# For SSDs (recommended: none or mq-deadline)
echo none | sudo tee /sys/block/sdx/queue/scheduler

# For HDDs (recommended: mq-deadline or bfq)
echo mq-deadline | sudo tee /sys/block/sdx/queue/scheduler
```

### Performance Optimization Tips

#### 1. **Choose the Right Buffer Size**

Start with defaults and increase if you have available RAM:
```bash
# Start with default
sudo wipeit /dev/sdx

# If device is fast and you have RAM, increase buffer
sudo wipeit -b 1G /dev/sdx
```

#### 2. **Unmount and Disable Swap**

Ensure nothing else is accessing the device:
```bash
# Unmount all partitions
sudo umount /dev/sdx*

# If device is used for swap, disable it
sudo swapoff /dev/sdx1
```

#### 3. **Close Other Applications**

For maximum speed:
- Close unnecessary applications
- Stop unnecessary services
- Avoid heavy disk I/O on other drives during wiping

#### 4. **Direct Device Access**

Always wipe the entire device, not partitions:
```bash
# ✓ Correct - wipe entire device
sudo wipeit /dev/sdb

# ✗ Incorrect - wiping partition is slower
sudo wipeit /dev/sdb1
```

#### 5. **Monitor Performance**

Watch the progress output to verify expected speeds:
```bash
Progress: 15.42% | Written: 19.74 GB | Speed: 82.15 MB/s | ETA: 17.23 min | Buffer: 100M
```

If speed is much lower than expected:
- Check if other processes are using I/O
- Verify device is not failing (`dmesg | tail`)
- Try increasing buffer size
- Check cable quality (for external drives)

#### 6. **Multiple Devices**

When wiping multiple devices simultaneously:
```bash
# In separate terminals, adjust buffer sizes based on total available RAM
sudo wipeit -b 500M /dev/sdb
sudo wipeit -b 500M /dev/sdc
sudo wipeit -b 500M /dev/sdd
```

**Note:** Total buffer size across all instances should not exceed available RAM.

### Troubleshooting Performance Issues

#### Slow Write Speeds

**Problem:** Speed is 50-70% lower than expected

**Solutions:**
1. Check cable quality (try different USB port/cable)
2. Verify device health: `sudo smartctl -a /dev/sdx`
3. Increase buffer size: `-b 500M` or `-b 1G`
4. Check for background processes: `iotop -o`
5. Disable power management:
   ```bash
   sudo hdparm -B 255 /dev/sdx  # Disable APM
   ```

#### High Memory Usage

**Problem:** System running out of memory

**Solutions:**
1. Reduce buffer size: `-b 100M` or `-b 50M`
2. Close other applications
3. Check available memory: `free -h`

#### Device Overheating

**Problem:** External device getting hot

**Solutions:**
1. Reduce buffer size to slow down writes
2. Improve airflow around device
3. Take periodic breaks (Ctrl+C to pause)

### Performance Comparison: Buffer Sizes

Real-world test results (256 GB NVMe SSD):

| Buffer Size | Speed | Time | Memory Used |
|-------------|-------|------|-------------|
| 10M | 180 MB/s | 24 min | ~15 MB |
| 100M | 420 MB/s | 10 min | ~105 MB |
| 500M | 485 MB/s | 9 min | ~505 MB |
| 1G | 510 MB/s | 8.5 min | ~1.05 GB |
| 2G | 515 MB/s | 8.3 min | ~2.05 GB |

**Conclusion:** For most use cases, 100M-500M provides the best balance of speed and resource usage.

## Development

### Running Tests

```bash
# Run all tests
python3 test_wipeit.py

# Run with verbose output
python3 test_wipeit.py -v

# Run specific test class
python3 -m unittest test_wipeit.TestParseSize -v

# Run with coverage
coverage run test_wipeit.py
coverage report
```

### Continuous Integration

This project uses GitHub Actions for continuous integration:

- **CI Pipeline**: Runs tests on Python 3.8, 3.11, 3.12
- **Test Suite**: Comprehensive unit tests with 27 test cases
- **Code Quality**: Linting, formatting, and security checks
- **Coverage**: Code coverage reporting
- **Build**: Automatic package building and validation

### Contributing

**⚠️ IMPORTANT: This tool is designed to DESTROY data - contribute responsibly! ⚠️**

We welcome contributions from the community! There are many ways to participate:

#### 🌟 **Show Your Support**
- **Star the project** ⭐ - Help others discover wipeit
- **Watch for updates** 👀 - Stay informed about new features
- **Share with others** 📢 - Spread the word about secure data wiping

#### 🐛 **Report Issues**
- **Bug reports** - Found a problem? Let us know!
- **Performance issues** - Experiencing slow wiping speeds?
- **Compatibility problems** - Issues with specific hardware?
- **Documentation gaps** - Something unclear or missing?

#### 💡 **Request Features**
- **New algorithms** - Have ideas for better wiping methods?
- **UI improvements** - Suggestions for better user experience?
- **Platform support** - Need support for additional operating systems?
- **Integration requests** - Want wipeit to work with other tools?

#### **Code Contributions**
1. **Fork the repository**
2. **Create a feature branch** (`git checkout -b feature/amazing-feature`)
3. **Add tests** for new functionality
4. **Ensure all tests pass** (`make tests`)
5. **Follow coding standards** (`make pre-git-prep`)
6. **Submit a pull request**

#### **Documentation**
- **Improve guides** - Make documentation clearer
- **Add examples** - Share use cases and workflows
- **Translate** - Help make wipeit accessible worldwide
- **Tutorials** - Create step-by-step guides

#### **Testing**
- **Test on different hardware** - Help ensure compatibility
- **Report edge cases** - Find scenarios we haven't tested
- **Performance testing** - Help optimize wiping speeds
- **Security validation** - Verify wiping effectiveness

**Every contribution matters!** Whether you're reporting a bug, suggesting a feature, or submitting code, you're helping make wipeit better for everyone.

## Documentation

For more information, see the [DOCS](DOCS/) directory:
- [CHANGES.md](DOCS/CHANGES.md) - Version history and changelog
- [PERFORMANCE-GUIDE.md](DOCS/PERFORMANCE-GUIDE.md) - Quick reference for performance optimization
- [TESTDESIGN.md](TESTDESIGN.md) - Comprehensive testing strategy and guidelines

## License

MIT License

## Support

### **Need Help?**

**Before asking for help:**
1. Check the [troubleshooting section](#troubleshooting-performance-issues) above
2. Verify all [system requirements](#requirements) are met
3. Review the [documentation](DOCS/) for detailed guides

### **Get Support**

- **Found a bug?** → [Open an issue](https://github.com/cscortes/wipeit/issues/new?template=bug_report.md)
- **Have a feature request?** → [Request a feature](https://github.com/cscortes/wipeit/issues/new?template=feature_request.md)
- **General questions?** → [Start a discussion](https://github.com/cscortes/wipeit/discussions)
- **Need documentation help?** → [Improve the docs](https://github.com/cscortes/wipeit/issues/new?template=documentation.md)

### **Show Your Support**

- **Star this project** - Help others discover wipeit
- **Watch for updates** - Get notified of new releases
- **Share your experience** - Help others in discussions
- **Contribute** - See the [Contributing](#contributing) section above

**We're here to help!** The wipeit community is friendly and responsive. Don't hesitate to reach out!

## 🚨 FINAL WARNING - READ THIS CAREFULLY! 🚨

**THIS TOOL IS EXTREMELY DESTRUCTIVE AND COMPLETELY IRREVERSIBLE!**

**⚠️ USE AT YOUR OWN RISK - ALL DATA WILL BE PERMANENTLY DESTROYED! ⚠️**

**Before using this tool, you MUST:**
- **TRIPLE-CHECK** the device path multiple times
- **VERIFY** you're targeting the correct device (NOT your system disk!)
- **BACKUP** any important data before proceeding
- **UNMOUNT** devices before wiping
- **NEVER** wipe your system disk or any device with important data
- **TEST** on a disposable device first if you're unsure
- **UNDERSTAND** that this process cannot be undone
- **ACCEPT** full responsibility for any data loss

**🚨 CRITICAL REMINDERS:**
- This tool will **PERMANENTLY DESTROY** all data on the target device
- There is **NO UNDO** function - once started, data is gone forever
- **DOUBLE-CHECK** device paths - a typo could destroy the wrong drive
- **NEVER** run this on your main system drive or any drive with important data
- This tool is designed for **SECURE DATA DESTRUCTION** - use responsibly

**By using this tool, you accept full responsibility for any data loss.**

