# Performance Quick Reference Guide

**⚠️ WARNING: This tool is EXTREMELY DESTRUCTIVE and will PERMANENTLY DESTROY data! ⚠️**

## Buffer Size Cheat Sheet

**🚨 USE AT YOUR OWN RISK - ALL DATA WILL BE IRREVERSIBLY DESTROYED! 🚨**

### By Device Type

| Device | Buffer Size | Command |
|--------|-------------|---------|
| **USB 2.0 Drive** | 100M | `sudo wipeit -b 100M /dev/sdx` |
| **USB 3.0 Drive** | 256M | `sudo wipeit -b 256M /dev/sdx` |
| **SATA HDD** | 500M | `sudo wipeit -b 500M /dev/sdx` |
| **SATA SSD** | 1G | `sudo wipeit -b 1G /dev/sdx` |
| **NVMe SSD** | 2G | `sudo wipeit -b 2G /dev/sdx` |

### By Available RAM

| Your RAM | Maximum Buffer | Safe Buffer |
|----------|----------------|-------------|
| 512 MB | 100M | 50M |
| 1 GB | 500M | 256M |
| 2 GB | 1G | 500M |
| 4 GB | 2G | 1G |
| 8+ GB | 4G | 2G |

## Expected Wipe Times

### USB 3.0 Drives
- 16 GB → 2-3 minutes
- 64 GB → 7-13 minutes
- 128 GB → 15-27 minutes
- 512 GB → 1-2 hours
- 1 TB → 2-3.5 hours

### SATA SSDs
- 256 GB → 12-20 minutes
- 512 GB → 23-40 minutes
- 1 TB → 40-85 minutes
- 2 TB → 1.5-2.8 hours

### NVMe SSDs
- 256 GB → 4-9 minutes
- 512 GB → 8-17 minutes
- 1 TB → 12-35 minutes
- 2 TB → 25-70 minutes

## Pre-Wipe Checklist

```bash
# 1. Identify the correct device
lsblk
sudo wipeit  # List all devices

# 2. Unmount all partitions
sudo umount /dev/sdx*

# 3. Check available RAM
free -h

# 4. Verify device is not busy
lsof /dev/sdx

# 5. Start wipe with appropriate buffer
sudo wipeit -b [SIZE] /dev/sdx
```

## Optimization Commands

### Check Current I/O Scheduler
```bash
cat /sys/block/sdx/queue/scheduler
```

### Set Optimal Scheduler
```bash
# For SSDs
echo none | sudo tee /sys/block/sdx/queue/scheduler

# For HDDs
echo mq-deadline | sudo tee /sys/block/sdx/queue/scheduler
```

### Disable Power Management (if slow)
```bash
sudo hdparm -B 255 /dev/sdx
```

### Monitor Active I/O
```bash
# Install if needed
sudo dnf install iotop  # Fedora
sudo apt install iotop  # Ubuntu

# Monitor
sudo iotop -o
```

## Common Issues & Solutions

### Issue: Speed slower than expected

**Quick fixes:**
```bash
# 1. Increase buffer size
sudo wipeit -b 1G /dev/sdx

# 2. Check for other I/O activity
sudo iotop -o

# 3. Try different USB port (for external drives)

# 4. Verify cable quality
```

### Issue: System running out of memory

**Quick fixes:**
```bash
# 1. Reduce buffer size
sudo wipeit -b 50M /dev/sdx

# 2. Close other applications

# 3. Check memory usage
free -h
```

### Issue: Device overheating

**Quick fixes:**
```bash
# 1. Reduce buffer size to slow down writes
sudo wipeit -b 100M /dev/sdx

# 2. Pause and resume
# Press Ctrl+C to pause
# Wait for device to cool
# Restart with same command
```

## Multiple Devices Strategy

When wiping multiple devices simultaneously, divide your RAM:

```bash
# Example: 8GB RAM, 3 devices = ~2GB per device (leaving 2GB for system)

# Terminal 1
sudo wipeit -b 500M /dev/sdb

# Terminal 2
sudo wipeit -b 500M /dev/sdc

# Terminal 3
sudo wipeit -b 500M /dev/sdd
```

## Monitoring Progress

Watch for these indicators in the progress output:

```
Progress: 15.42% | Written: 19.74 GB | Speed: 82.15 MB/s | ETA: 17.23 min | Buffer: 100M
```

**What to check:**
- **Speed:** Should match expected speed for your device type
- **ETA:** Should be reasonable based on device size
- **Progress:** Should increase steadily

**Red flags:**
- Speed drops significantly (check cable/USB port)
- Progress stalls (check `dmesg` for errors)
- Speed < 10 MB/s on modern devices (device may be failing)

## Emergency Stops

You can safely interrupt at any time:

```bash
# Press Ctrl+C to stop
^C
Wipe interrupted.
```

**Note:** Interrupting is safe but:
- Device will be partially wiped
- You'll need to start over for complete wipe
- Already-wiped data is not recoverable

## Performance Testing

To find optimal buffer size for your device:

```bash
# Test with small area (if you have test data)
sudo wipeit -b 100M /dev/sdx  # Note the speed
# Ctrl+C after 1-2 minutes

sudo wipeit -b 500M /dev/sdx  # Note the speed
# Ctrl+C after 1-2 minutes

sudo wipeit -b 1G /dev/sdx    # Note the speed
# Ctrl+C after 1-2 minutes

# Use the buffer size with best speed/memory trade-off
```

## Best Practices Summary

1. ✅ Always verify device path before wiping
2. ✅ Unmount all partitions first
3. ✅ Choose buffer size based on device type and available RAM
4. ✅ Monitor progress for expected speeds
5. ✅ Close unnecessary applications during wipe
6. ✅ Use quality cables for external drives
7. ✅ Allow adequate cooling for devices
8. ✅ Keep total buffer sizes < 50% of RAM for multiple devices

## Quick Syntax Reference

```bash
# Basic wipe (default 100M buffer)
sudo wipeit /dev/sdx

# Custom buffer
sudo wipeit -b [SIZE][M|G|T] /dev/sdx

# List devices only
sudo wipeit

# Help
wipeit --help

# Examples
sudo wipeit -b 500M /dev/sdb    # 500 megabytes
sudo wipeit -b 1G /dev/sdc      # 1 gigabyte
sudo wipeit -b 2G /dev/sdd      # 2 gigabytes
sudo wipeit -b 0.5G /dev/sde    # 512 megabytes (decimal)
```

## Support

For more detailed information, see the main [README.md](../README.md).

For version history and changes, see [CHANGES.md](CHANGES.md).


