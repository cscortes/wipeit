#!/usr/bin/env python3
"""
wipeit - Secure device wiping utility
Overwrites block devices with random data for secure data destruction.
"""

import argparse
import fcntl
import json
import os
import struct
import subprocess
import sys
import time

from device_detector import DeviceDetector
from global_constants import (
    DEFAULT_CHUNK_SIZE,
    DISPLAY_LINE_WIDTH,
    GB_MILESTONE_THRESHOLD,
    GIGABYTE,
    HIGH_VARIANCE_THRESHOLD_MBPS,
    LOW_SPEED_THRESHOLD_MBPS,
    MAX_SIZE_BYTES,
    MAX_SMALL_CHUNK_SIZE,
    MEGABYTE,
    MIN_SIZE_BYTES,
    PROGRESS_FILE_EXPIRY_SECONDS,
    TERABYTE,
)


def list_all_devices():
    try:
        output = subprocess.check_output(['lsblk', '-dno', 'NAME,TYPE'])\
            .decode().splitlines()
        disks = ['/dev/' + line.split()[0]
                 for line in output
                 if len(line.split()) > 1 and line.split()[1] == 'disk']
        for device in disks:
            detector = DeviceDetector(device)
            detector.display_info()
            print("\n---\n")
    except Exception as e:
        print(f"Error listing devices: {e}")


def parse_size(size_str):
    """Parse size string with M, G, T suffix (e.g., '100M', '1G', '500M')."""
    size_str = size_str.upper().strip()

    if size_str[-1] in ['M', 'G', 'T']:
        try:
            value = float(size_str[:-1])
            suffix = size_str[-1]
        except ValueError:
            raise ValueError(f"Invalid size format: {size_str}")
    else:
        raise ValueError(f"Size must end with M, G, or T: {size_str}")

    multipliers = {
        'M': MEGABYTE,
        'G': GIGABYTE,
        'T': TERABYTE
    }

    size_bytes = int(value * multipliers[suffix])

    if size_bytes < MIN_SIZE_BYTES:
        raise ValueError("Buffer size must be at least 1M")
    if size_bytes > MAX_SIZE_BYTES:
        raise ValueError("Buffer size must not exceed 1T")

    return size_bytes


def get_block_device_size(device):
    with open(device, 'rb') as fd:
        buf = bytearray(8)
        fcntl.ioctl(fd.fileno(), 0x80081272, buf)  # BLKGETSIZE64
        return struct.unpack('Q', buf)[0]


def perform_hdd_pretest(device, chunk_size=DEFAULT_CHUNK_SIZE):
    """
    Perform pretest on HDD to measure write speeds at different positions.

    This helps determine the optimal wiping algorithm for the device.

    Args:
        device: Path to block device
        chunk_size: Size of test chunks in bytes

    Returns:
        dict: Pretest results with speed measurements and recommendations
    """
    try:
        size = get_block_device_size(device)
        print("=" * 50)
        print("HDD PRETEST")
        print("=" * 50)
        print("• Performing HDD pretest to optimize wiping algorithm...")
        print("  This will test write speeds at different disk positions.")
        print("  WARNING: This will write test data to the disk!")
        print(f"• Disk size: {size / (1024**3):.2f} GB")
        print(f"• Test chunk size: {chunk_size / (1024**2):.0f} MB")

        # Test positions: beginning, middle, end
        test_positions = [
            (0, "beginning"),
            (size // 2, "middle"),
            (size - chunk_size, "end")
        ]

        print(f"• Test positions: {len(test_positions)} locations")

        speeds = []
        for position, name in test_positions:
            print(f"• Testing {name} of disk...")
            start_time = time.time()

            # Write test data
            with open(device, 'wb') as f:
                f.seek(position)
                f.write(b'\x00' * chunk_size)
                f.flush()
                os.fsync(f.fileno())

            end_time = time.time()
            duration = end_time - start_time
            speed = chunk_size / duration / MEGABYTE  # MB/s
            speeds.append(speed)

            print(f"    • {name.capitalize()}: {speed:.2f} MB/s")

        # Analyze results
        avg_speed = sum(speeds) / len(speeds)
        speed_variance = max(speeds) - min(speeds)

        print("\n" + "=" * 50)
        print("PRETEST ANALYSIS")
        print("=" * 50)
        print(f"• Average speed: {avg_speed:.2f} MB/s")
        print(f"• Speed variance: {speed_variance:.2f} MB/s")

        # Determine recommended algorithm
        if speed_variance > HIGH_VARIANCE_THRESHOLD_MBPS:  # High variance
            algorithm = "adaptive_chunk"
            reason = ("High speed variance detected - "
                      "adaptive chunk sizing recommended")
        elif avg_speed < LOW_SPEED_THRESHOLD_MBPS:  # Low average speed
            algorithm = "small_chunk"
            reason = ("Low average speed - "
                      "small chunks for better responsiveness")
        else:
            algorithm = "standard"
            reason = "Consistent performance - standard algorithm recommended"

        print(f"• Recommended algorithm: {algorithm}")
        print(f"• Reason: {reason}")

        return {
            'speeds': speeds,
            'average_speed': avg_speed,
            'speed_variance': speed_variance,
            'analysis': {
                'recommended_algorithm': algorithm,
                'reason': reason
            },
            'recommended_algorithm': algorithm,
            'reason': reason
        }

    except Exception as e:
        print(f"Pretest failed: {e}")
        return None


def get_progress_file(device):
    """Get the path to the progress file for a device."""
    device_name = os.path.basename(device)
    return f"wipeit_progress_{device_name}.json"


def save_progress(device, written, total_size,
                  chunk_size, pretest_results=None):
    """Save wipe progress to file."""
    progress_file = get_progress_file(device)
    progress_percent = (written / total_size) * 100 if total_size > 0 else 0
    progress_data = {
        'device': device,
        'written': written,
        'total_size': total_size,
        'progress_percent': progress_percent,
        'chunk_size': chunk_size,
        'timestamp': time.time(),
        'pretest_results': pretest_results
    }

    try:
        with open(progress_file, 'w') as f:
            json.dump(progress_data, f, indent=2)
    except Exception as e:
        print(f"Warning: Could not save progress: {e}")


def load_progress(device):
    """Load saved progress from file."""
    progress_file = get_progress_file(device)

    if not os.path.exists(progress_file):
        return None

    try:
        with open(progress_file, 'r') as f:
            progress_data = json.load(f)

        # Check if progress is still valid (24 hours)
        if (time.time() - progress_data['timestamp'] >
                PROGRESS_FILE_EXPIRY_SECONDS):
            print("Progress file is older than 24 hours, ignoring.")
            return None

        # Verify device matches
        if progress_data['device'] != device:
            print("Progress file is for a different device, ignoring.")
            return None

        return progress_data
    except Exception as e:
        print(f"Warning: Could not load progress: {e}")
        return None


def clear_progress(device):
    """Clear progress file."""
    progress_file = get_progress_file(device)
    try:
        if os.path.exists(progress_file):
            os.remove(progress_file)
    except Exception as e:
        print(f"Warning: Could not clear progress: {e}")


def find_resume_files():
    """Find all progress files."""
    progress_files = []
    try:
        for filename in os.listdir('.'):
            if filename.startswith(
                    'wipeit_progress_') and filename.endswith('.json'):
                try:
                    with open(filename, 'r') as f:
                        progress_data = json.load(f)
                    # Check if progress is still valid (24 hours)
                    if (time.time() - progress_data['timestamp'] <=
                            PROGRESS_FILE_EXPIRY_SECONDS):
                        progress_files.append(progress_data)
                except Exception:
                    pass
    except Exception:
        pass
    return progress_files


def display_resume_info():
    """Display available resume options."""
    progress_files = find_resume_files()

    if not progress_files:
        return False

    print("=" * 50)
    print("RESUME OPTIONS")
    print("=" * 50)
    print("Found previous wipe sessions that can be resumed:")
    print()

    for progress_data in progress_files:
        try:
            device = progress_data['device']
            written = progress_data['written']
            total_size = progress_data['total_size']
            progress_percent = progress_data['progress_percent']
            timestamp = progress_data['timestamp']

            print(f"• Device: {device}")
            print(f"  Progress: {progress_percent:.2f}% complete")
            written_gb = written / (1024**3)
            total_gb = total_size / (1024**3)
            print(f"  Written: {written_gb:.2f} GB / {total_gb:.2f} GB")
            print(f"  Started: {time.ctime(timestamp)}")
            print()
        except Exception as e:
            print(f"Error reading progress data: {e}")

    print("=" * 50)

    return True


def wipe_device(device, chunk_size=DEFAULT_CHUNK_SIZE, resume=False,
                skip_pretest=False):
    written = 0  # Initialize written at function start
    size = 0
    start_time = time.time()
    pretest_results = None

    try:
        size = get_block_device_size(device)
        start_time = time.time()

        detector = DeviceDetector(device)
        disk_type, confidence, details = detector.detect_type()

        print(f"\n💾 Detected disk type: {disk_type} "
              f"(confidence: {confidence})")
        if details:
            print(f"   Detection details: {', '.join(details)}")

        progress_data = None
        existing_pretest_results = None
        if resume:
            progress_data = load_progress(device)
            if progress_data:
                written = progress_data['written']
                print(f"Resuming wipe from {written / (1024**3):.2f} GB "
                      f"({progress_data['progress_percent']:.2f}% complete)")
                print(f"Previous session:"
                      f" {time.ctime(progress_data['timestamp'])}")

                if 'pretest_results' in progress_data:
                    existing_pretest_results = progress_data['pretest_results']
                    print(f"   Found previous pretest results from "
                          f"{time.ctime(progress_data['timestamp'])}")
            else:
                print("No previous progress found, starting from beginning")

        if disk_type == "HDD" and not skip_pretest:
            if existing_pretest_results:
                pretest_results = existing_pretest_results
                print("🔄 Using previous pretest results")
            else:
                print("🔄 HDD detected - performing pretest to optimize "
                      "wiping algorithm...")
                pretest_results = perform_hdd_pretest(device, chunk_size)
                if pretest_results:
                    save_progress(device, written, size, chunk_size,
                                  pretest_results)
                else:
                    print("Pretest failed, using standard algorithm")

        # Determine algorithm based on pretest results
        if pretest_results:
            algorithm = pretest_results.get(
                'recommended_algorithm', 'standard')
            print(f"🎯 Using {algorithm} algorithm based on pretest")
        else:
            algorithm = "standard"
            print(f"🎯 Using {algorithm} algorithm")

        # Adaptive chunk sizing for HDDs
        if algorithm == "adaptive_chunk" and disk_type == "HDD":
            print("🔄 Using adaptive chunk sizing for optimal performance")
            current_chunk_size = chunk_size
            speed_samples = []

            while written < size:
                # Calculate position-based chunk size
                position_ratio = written / size
                if position_ratio < 0.1:  # Beginning - fast
                    current_chunk_size = int(chunk_size * 2)
                elif position_ratio > 0.9:  # End - slow
                    current_chunk_size = int(chunk_size * 0.5)
                else:  # Middle - adaptive
                    if len(speed_samples) > 0:
                        avg_speed = sum(
                            speed_samples[-5:]) / len(speed_samples[-5:])
                        if avg_speed < 50:  # Slow
                            current_chunk_size = int(chunk_size * 0.5)
                        elif avg_speed > 200:  # Fast
                            current_chunk_size = int(chunk_size * 1.5)
                        else:
                            current_chunk_size = chunk_size
                    else:
                        current_chunk_size = chunk_size

                # Ensure chunk size is within bounds
                current_chunk_size = max(
                    MEGABYTE, min(current_chunk_size, size - written))

                # Write chunk
                chunk_start_time = time.time()
                with open(device, 'wb') as f:
                    f.seek(written)
                    f.write(b'\x00' * current_chunk_size)
                    f.flush()
                    os.fsync(f.fileno())

                chunk_end_time = time.time()
                chunk_duration = chunk_end_time - chunk_start_time
                chunk_speed = current_chunk_size / \
                    chunk_duration / MEGABYTE
                speed_samples.append(chunk_speed)

                written += current_chunk_size

                # Progress display
                progress_percent = (written / size) * 100
                elapsed_time = time.time() - start_time
                if written > 0:
                    eta = (size - written) / (written / elapsed_time)
                    hours = int(eta // 3600)
                    minutes = int((eta % 3600) // 60)
                    seconds = int(eta % 60)
                    eta_str = f"{hours:02d}:{minutes:02d}:{seconds:02d}"
                else:
                    eta_str = "??:??:??"

                # Visual progress bar
                bar_length = 50
                filled_length = int(bar_length * written // size)
                bar = '█' * filled_length + '░' * (bar_length - filled_length)

                print(f"\r• Progress: {progress_percent:.1f}% |{bar}| "
                      f"{written / (1024**3):.1f}GB/"
                      f"{size / (1024**3):.1f}GB ETA: {eta_str} "
                      f"Speed: {chunk_speed:.1f}MB/s", end='', flush=True)

                # Save progress every 1GB
                if written % GB_MILESTONE_THRESHOLD == 0:
                    save_progress(device, written, size, chunk_size,
                                  pretest_results)

        else:  # Standard or small chunk algorithm
            if algorithm == "small_chunk":
                chunk_size = min(chunk_size, MAX_SMALL_CHUNK_SIZE)  # Max 10MB
                chunk_mb = chunk_size / MEGABYTE
                print(f"🔄 Using small chunk size: {chunk_mb:.0f} MB")

            while written < size:
                current_chunk_size = min(chunk_size, size - written)

                with open(device, 'wb') as f:
                    f.seek(written)
                    f.write(b'\x00' * current_chunk_size)
                    f.flush()
                    os.fsync(f.fileno())

                written += current_chunk_size

                # Progress display
                progress_percent = (written / size) * 100
                elapsed_time = time.time() - start_time
                if written > 0:
                    eta = (size - written) / (written / elapsed_time)
                    hours = int(eta // 3600)
                    minutes = int((eta % 3600) // 60)
                    seconds = int(eta % 60)
                    eta_str = f"{hours:02d}:{minutes:02d}:{seconds:02d}"
                else:
                    eta_str = "??:??:??"

                # Visual progress bar
                bar_length = 50
                filled_length = int(bar_length * written // size)
                bar = '█' * filled_length + '░' * (bar_length - filled_length)

                print(f"\r• Progress: {progress_percent:.1f}% |{bar}| "
                      f"{written / (1024**3):.1f}GB/"
                      f"{size / (1024**3):.1f}GB ETA: {eta_str}",
                      end='', flush=True)

                # Save progress every 1GB
                if written % GB_MILESTONE_THRESHOLD == 0:
                    save_progress(device, written, size, chunk_size,
                                  pretest_results)

        print()  # New line after progress bar
        clear_progress(device)

        total_time = time.time() - start_time
        avg_speed = size / total_time / MEGABYTE

        print("\n" + "=" * 50)
        print("WIPE COMPLETED")
        print("=" * 50)
        print(f"• Device: {device}")
        print(f"• Size: {size / (1024**3):.2f} GB")
        print(f"• Time: {total_time:.2f} seconds")
        print(f"• Average speed: {avg_speed:.2f} MB/s")
        print("• Status: ✅ Successfully wiped")

    except KeyboardInterrupt:
        print("\n\n⚠️  Wipe interrupted by user")
        print(f"• Progress saved: {written / (1024**3):.2f} GB written")
        print("• To resume: run wipeit with --resume flag")
        save_progress(device, written, size, chunk_size, pretest_results)
        sys.exit(1)
    except Exception as e:
        print(f"\n❌ Error during wipe: {e}")
        save_progress(device, written, size, chunk_size, pretest_results)
        sys.exit(1)


def main():
    """Main function for CLI interface."""
    parser = argparse.ArgumentParser(
        description='Secure device wiping utility',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  wipeit /dev/sdb                    # Wipe device with default settings
  wipeit -b 1G /dev/sdb             # Use 1GB buffer size
  wipeit --resume /dev/sdb          # Resume previous wipe
  wipeit --skip-pretest /dev/sdb    # Skip HDD pretest
  wipeit --list                     # List all available devices

⚠️  WARNING: This tool will PERMANENTLY DESTROY ALL DATA on the target device!
        """
    )

    parser.add_argument(
        'device',
        nargs='?',
        help='Block device to wipe (e.g., /dev/sdb)')
    parser.add_argument('-b', '--buffer-size', default='100M',
                        help='Buffer size (default: 100M, range: 1M-1T)')
    parser.add_argument('--resume', action='store_true',
                        help='Resume previous wipe session')
    parser.add_argument('--skip-pretest', action='store_true',
                        help='Skip HDD pretest (use standard algorithm)')
    parser.add_argument('--list', action='store_true',
                        help='List all available block devices')
    parser.add_argument(
        '-v',
        '--version',
        action='version',
        version='wipeit 1.2.0')

    args = parser.parse_args()

    # Check if running as root
    if os.geteuid() != 0:
        print("Error: This program must be run as root (sudo)")
        print("Use: sudo wipeit")
        sys.exit(1)

    # Handle --list option
    if args.list:
        print("📋 Available devices (requires sudo):")
        print("=" * 50)
        list_all_devices()
        return

    # Handle no arguments - show resume info and list devices
    if not args.device:
        # Display resume information if available
        display_resume_info()
        print("📋 Available devices (requires sudo):")
        print("=" * 50)
        list_all_devices()
        return

    # Check if device exists
    if not os.path.exists(args.device):
        print(f"Error: Device {args.device} does not exist")
        sys.exit(1)

    # Parse buffer size
    try:
        buffer_size = parse_size(args.buffer_size)
    except ValueError as e:
        print(f"Error: {e}")
        sys.exit(1)

    # Display resume information if available
    if not args.resume:
        if display_resume_info():
            print("Use --resume flag to continue a previous session")
            print()

    # Display configuration
    print("=" * DISPLAY_LINE_WIDTH)
    print("CONFIGURATION")
    print("=" * DISPLAY_LINE_WIDTH)
    print(f"• Using buffer size: {buffer_size / (1024**2):.0f} MB "
          f"({buffer_size / (1024**3):.2f} GB)")

    # Get device information
    detector = DeviceDetector(args.device)
    detector.display_info()

    # Safety check: Ensure device is not mounted
    is_mounted, mount_info = detector.is_mounted()
    if is_mounted:
        print("\n" + "=" * 70)
        print("🚨 SAFETY CHECK FAILED - DEVICE IS MOUNTED")
        print("=" * DISPLAY_LINE_WIDTH)
        print(f"❌ Cannot proceed with wiping {args.device}")
        print("   The device or its partitions are currently mounted!")
        print()
        if mount_info:
            print("📌 Mounted partitions found:")
            for mount in mount_info:
                print(f"   • {mount}")
            print()
        print("🔧 TO FIX THIS ISSUE:")
        print("   1. Unmount all partitions on this device:")
        print(f"      sudo umount /dev/{args.device.split('/')[-1]}*")
        print("   2. Or unmount specific partitions:")
        for mount in mount_info:
            partition = mount.split(' -> ')[0]
            print(f"      sudo umount {partition}")
        print("   3. Verify device is unmounted:")
        print(f"      lsblk {args.device}")
        print("   4. Then run wipeit again")
        print()
        print("⚠️  WARNING: Wiping a mounted device can cause:")
        print("   • Data corruption on the mounted filesystem")
        print("   • System instability or crashes")
        print("   • Loss of data on other mounted partitions")
        print()
        print("🛑 Program terminated for safety.")
        sys.exit(1)

    # Load progress if resuming
    if args.resume:
        progress_data = load_progress(args.device)
        if not progress_data:
            print("No previous progress found for this device")
            print("Starting fresh wipe...")
        else:
            percent = progress_data['progress_percent']
            print(f"Resuming wipe from {percent:.2f}% complete")
    else:
        # Clear any existing progress
        clear_progress(args.device)

    # Final confirmation
    print("\n" + "=" * 70)
    print("⚠️  FINAL WARNING ⚠️")
    print("=" * DISPLAY_LINE_WIDTH)
    print(f"🚨 This will PERMANENTLY DESTROY ALL DATA on {args.device}")
    print("🚨 This action CANNOT be undone!")
    print("🚨 Make sure you have selected the correct device!")
    print()
    print("Type 'y' to proceed with wiping, or anything else to abort:")

    try:
        response = input().strip().lower()
        if response != 'y':
            print("Wipe cancelled by user")
            sys.exit(0)
    except KeyboardInterrupt:
        print("\nWipe cancelled by user")
        sys.exit(0)

    # Start wiping
    print("\n🚀 Starting secure wipe...")
    wipe_device(args.device, buffer_size, args.resume, args.skip_pretest)


if __name__ == '__main__':
    main()
