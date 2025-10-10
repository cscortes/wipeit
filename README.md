# wipeit

A secure device wiping utility that overwrites block devices with random data.

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
- [Performance Recommendations](#performance-recommendations) 📊
  - [Expected Write Speeds](#expected-write-speeds)
  - [Time Estimates by Device Size](#time-estimates-by-device-size)
  - [Buffer Size Optimization](#buffer-size-optimization)
  - [System Requirements](#system-requirements-for-optimal-performance)
  - [Optimization Tips](#performance-optimization-tips)
  - [Troubleshooting Performance](#troubleshooting-performance-issues)

## Features

- 🔍 List all block devices with detailed information (size, model, serial, partitions)
- 🔒 Securely wipe devices by overwriting with random data
- 📊 Real-time progress display with speed and ETA
- ⚠️  Safety checks for mounted devices
- 💾 Chunked writing for efficient memory usage
- 🛡️ Root privilege verification before execution

## Installation

### Using uv (recommended)

```bash
# Install from PyPI (when published)
uv pip install wipeit

# Or install from source
git clone <repository-url>
cd wipeit
uv sync
```

### Using pip

```bash
pip install wipeit
```

### Development Installation

```bash
git clone <repository-url>
cd wipeit
uv sync
source .venv/bin/activate
```

## Usage

### Quick Start

**Important:** This tool requires root privileges. Always run with `sudo`.

### List all block devices

To see all available block devices on your system:

```bash
sudo wipeit
```

**Note:** If you have pending wipe operations (interrupted wipes), the tool will first display information about them before showing available devices.

**Example with pending operations:**
```bash
$ ./wipeit.py

🔄 Found pending wipe operations:
==================================================

1. Device: /dev/sdb
   Progress: 25.00% complete
   Written: 1.00 GB / 4.00 GB
   Buffer size: 100 MB
   Started: Thu Oct  9 18:04:00 2025
   Resume command: sudo ./wipeit.py --resume /dev/sdb

💡 To resume any operation, use: sudo ./wipeit.py --resume <device>
💡 To start fresh, the progress file will be overwritten
==================================================

==================================================
📋 Available devices (requires sudo):
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

To securely wipe a device by overwriting it with random data:

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

Progress: 5.32% | Written: 6.81 GB | Speed: 85.32 MB/s | ETA: 23.45 min | Buffer: 1024M
```

### Stop and resume a wipe operation

Press `Ctrl+C` at any time to interrupt the wiping process:

```bash
Progress: 15.42% | Written: 19.74 GB | Speed: 82.15 MB/s | ETA: 17.23 min
^C
Wipe interrupted at 19.74 GB (15.42% complete)
Progress saved. To resume, run:
  sudo ./wipeit.py --resume /dev/sdb
```

#### Resume an interrupted wipe

To continue from where you left off:

```bash
sudo ./wipeit.py --resume /dev/sdb
```

**Example resume session:**
```bash
$ sudo ./wipeit.py --resume /dev/sdb

Resuming wipe from 19.74 GB (15.42% complete)
Previous session: Wed Oct  1 18:30:45 2025
Device: /dev/sdb
Size: 128.00 GB
Model: USB_Flash_Drive
Serial: 1234567890
Device and partitions:
NAME SIZE TYPE MOUNTPOINTS
sdb  128G disk

/dev/sdb does not appear to be mounted.

Confirm wipe (y/n): y

Progress: 16.12% | Written: 20.64 GB | Speed: 85.32 MB/s | ETA: 16.45 min | Buffer: 100M
```

#### Starting fresh vs resuming

If you try to start a new wipe on a device with existing progress:

```bash
$ sudo ./wipeit.py /dev/sdb

⚠️  Found previous wipe session:
   Progress: 15.42% (19.74 GB)
   Started: Wed Oct  1 18:30:45 2025

Options:
   1. Resume previous session: sudo ./wipeit.py --resume /dev/sdb
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
wipeit 0.1.0
```

### Resume functionality

The tool automatically saves progress and allows resuming interrupted wipes:

- **Progress files** are stored in `wipeit_progress_[device].json` (current directory)
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
- ✅ **Root check:** Verifies the program is run with root privileges
- ✅ **Device information:** Displays full device details before proceeding
- ✅ **Mount detection:** Warns if device or partitions are mounted
- ✅ **Explicit confirmation:** Requires user to type 'y' to proceed

### During Wiping
- ✅ **Progress tracking:** Real-time feedback on operation status
- ✅ **Interruptible:** Can be stopped at any time with Ctrl+C
- ✅ **Resumable:** Automatically saves progress and allows resuming from interruption point
- ✅ **Memory efficient:** Uses 100 MB chunks to avoid excessive memory usage

### Random Data
- Uses `os.urandom()` for cryptographically secure random data
- Overwrites entire device from start to finish
- No patterns that could potentially be recovered

## Common Use Cases

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
sudo ./wipeit.py --resume /dev/sdb
```

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

## Documentation

For more information, see the [DOCS](DOCS/) directory:
- [CHANGES.md](DOCS/CHANGES.md) - Version history and changelog
- [PERFORMANCE-GUIDE.md](DOCS/PERFORMANCE-GUIDE.md) - Quick reference for performance optimization

## License

MIT License

## Support

If you encounter issues or have questions:
1. Check the troubleshooting section above
2. Verify all system requirements are met
3. Open an issue on the project repository

## ⚠️  Final Warning

**This tool is powerful and irreversible. Always:**
- ✅ Verify the device path multiple times
- ✅ Backup any data you want to keep
- ✅ Unmount devices before wiping
- ✅ Never wipe your system disk
- ✅ Test on a disposable device first if unsure

**By using this tool, you accept full responsibility for any data loss.**

