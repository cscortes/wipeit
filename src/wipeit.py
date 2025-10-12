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
from disk_pretest import DiskPretest
from global_constants import (
    BLKGETSIZE64,
    DEFAULT_CHUNK_SIZE,
    DISPLAY_LINE_WIDTH,
    GIGABYTE,
    MAX_SIZE_BYTES,
    MAX_SMALL_CHUNK_SIZE,
    MEGABYTE,
    MIN_SIZE_BYTES,
    PROGRESS_FILE_NAME,
    TERABYTE,
)
from wipe_strategy import (
    AdaptiveStrategy,
    SmallChunkStrategy,
    StandardStrategy,
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
    """Get the size of a block device in bytes using BLKGETSIZE64 ioctl."""
    with open(device, 'rb') as fd:
        buf = bytearray(8)
        fcntl.ioctl(fd.fileno(), BLKGETSIZE64, buf)
        return struct.unpack('Q', buf)[0]


def save_progress(device, written, total_size,
                  chunk_size, pretest_results=None, device_id=None):
    """
    Save wipe progress to file.

    Args:
        device: Device path (e.g., '/dev/sdb')
        written: Bytes written so far
        total_size: Total device size in bytes
        chunk_size: Chunk size used for wiping
        pretest_results: Optional pretest results
        device_id: Optional device unique identifiers (serial, model, etc.)
    """
    progress_file = PROGRESS_FILE_NAME
    progress_percent = (written / total_size) * 100 if total_size > 0 else 0
    progress_data = {
        'device': device,
        'written': written,
        'total_size': total_size,
        'progress_percent': progress_percent,
        'chunk_size': chunk_size,
        'timestamp': time.time(),
        'pretest_results': pretest_results,
        'device_id': device_id
    }

    try:
        with open(progress_file, 'w') as f:
            json.dump(progress_data, f, indent=2)
            f.flush()  # Flush Python buffer
            os.fsync(f.fileno())  # Flush OS buffer to disk immediately
    except Exception as e:
        print(f"Warning: Could not save progress: {e}")


def load_progress(device):
    """
    Load saved progress from file and verify device identity.

    Args:
        device: Device path (e.g., '/dev/sdb')

    Returns:
        dict: Progress data if valid, None otherwise
    """
    progress_file = PROGRESS_FILE_NAME

    if not os.path.exists(progress_file):
        return None

    try:
        with open(progress_file, 'r') as f:
            progress_data = json.load(f)

        # Verify device identity if available
        if 'device_id' in progress_data and progress_data['device_id']:
            try:
                detector = DeviceDetector(device)
                current_id = detector.get_unique_id()
                saved_id = progress_data['device_id']

                # Check serial number (most unique identifier)
                if (saved_id.get('serial') and current_id.get('serial') and
                        saved_id['serial'] != current_id['serial']):
                    print("\n" + "=" * 70)
                    print("🚨 DEVICE MISMATCH ERROR")
                    print("=" * 70)
                    print("Cannot resume: Device serial number does not "
                          "match!")
                    print()
                    print(f"Expected serial: {saved_id['serial']}")
                    print(f"Current serial:  {current_id['serial']}")
                    print()
                    if saved_id.get('model'):
                        print(f"Expected model: {saved_id['model']}")
                    if current_id.get('model'):
                        print(f"Current model:  {current_id['model']}")
                    print()
                    print("⚠️  This is a DIFFERENT physical drive!")
                    print()
                    print("WHAT TO DO:")
                    print("  1. If this is the correct drive, the progress "
                          "file is from")
                    print("     a different device. Start a fresh wipe:")
                    print(f"     sudo wipeit {device}")
                    print()
                    print("  2. If you want to resume the ORIGINAL drive:")
                    print("     - Reconnect the original drive")
                    print("     - Verify it appears as the same device path")
                    print("     - Run: sudo wipeit --resume <device>")
                    print()
                    print("  3. To clear this progress file and start fresh:")
                    print("     rm wipeit_progress.json")
                    print("=" * 70)
                    sys.exit(1)

                # Check size as secondary verification
                if (saved_id.get('size') and current_id.get('size') and
                        saved_id['size'] != current_id['size']):
                    print("\n" + "=" * 70)
                    print("🚨 DEVICE MISMATCH ERROR")
                    print("=" * 70)
                    print("Cannot resume: Device size does not match!")
                    print()
                    print(f"Expected size: "
                          f"{saved_id['size'] / (1024**3):.2f} GB")
                    print(f"Current size:  "
                          f"{current_id['size'] / (1024**3):.2f} GB")
                    print()
                    print("⚠️  This is a DIFFERENT drive or the drive has "
                          "been repartitioned!")
                    print()
                    print("WHAT TO DO:")
                    print("  1. Verify you have the correct drive connected")
                    print("  2. To start a fresh wipe on this drive:")
                    print(f"     sudo wipeit {device}")
                    print("  3. To clear the old progress file:")
                    print("     rm wipeit_progress.json")
                    print("=" * 70)
                    sys.exit(1)

            except Exception as e:
                print(f"⚠️  Warning: Could not verify device identity: {e}")
                print("   Continuing anyway (backwards compatibility)")
                # Continue anyway - backwards compatibility

        return progress_data
    except Exception as e:
        print(f"🚨 Error loading progress file: {e}")
        import traceback
        traceback.print_exc()
        return None


def clear_progress(device):
    """Clear progress file."""
    progress_file = PROGRESS_FILE_NAME
    try:
        if os.path.exists(progress_file):
            os.remove(progress_file)
    except Exception as e:
        print(f"Warning: Could not clear progress: {e}")


def find_resume_files():
    """Find progress file if it exists."""
    progress_files = []
    progress_file = 'wipeit_progress.json'

    if os.path.exists(progress_file):
        try:
            with open(progress_file, 'r') as f:
                progress_data = json.load(f)
            progress_files.append(progress_data)
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
    """
    Wipe device using appropriate strategy (WRAPPER).

    This function maintained for backward compatibility.
    New code should use WipeStrategy classes directly.

    Args:
        device: Path to block device
        chunk_size: Base chunk size for wiping
        resume: Whether to resume previous session
        skip_pretest: Whether to skip HDD pretest

    Raises:
        KeyboardInterrupt: If user interrupts the wipe
        Exception: On I/O or other errors
    """
    written = 0
    size = 0
    start_time = time.time()
    pretest_results = None
    device_id = None  # Initialize to None for exception handlers

    try:
        size = get_block_device_size(device)

        detector = DeviceDetector(device)
        disk_type, confidence, details = detector.detect_type()
        device_id = detector.get_unique_id()

        print(f"\nDetected disk type: {disk_type} "
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
                print("Using previous pretest results")
            else:
                print("HDD detected - performing pretest to optimize "
                      "wiping algorithm...")
                pretest = DiskPretest(device, chunk_size)
                results = pretest.run_pretest()
                if results:
                    pretest_results = results.to_dict()
                    save_progress(device, written, size, chunk_size,
                                  pretest_results, device_id)
                else:
                    print("Pretest failed, using standard algorithm")

        if pretest_results:
            algorithm = pretest_results.get(
                'recommended_algorithm', 'standard')
            print(f"Using {algorithm} algorithm based on pretest")
        else:
            algorithm = "standard"
            print(f"Using {algorithm} algorithm")

        def progress_callback(written_bytes, total_bytes, chunk_bytes):
            """Callback for saving progress from strategy."""
            save_progress(device, written_bytes, total_bytes, chunk_bytes,
                          pretest_results, device_id)

        if algorithm == "adaptive_chunk":
            print("Using adaptive chunk sizing for optimal performance")
            strategy = AdaptiveStrategy(
                device, size, chunk_size, written, pretest_results,
                progress_callback
            )
        elif algorithm == "small_chunk":
            chunk_mb = min(chunk_size, MAX_SMALL_CHUNK_SIZE) / MEGABYTE
            print(f"Using small chunk size: {chunk_mb:.0f} MB")
            strategy = SmallChunkStrategy(
                device, size, chunk_size, written, pretest_results,
                progress_callback
            )
        else:
            strategy = StandardStrategy(
                device, size, chunk_size, written, pretest_results,
                progress_callback
            )

        strategy.wipe()
        written = strategy.written

        clear_progress(device)

        total_time = time.time() - start_time
        if total_time > 0:
            avg_speed = size / total_time / MEGABYTE
        else:
            avg_speed = 0

        print("\n" + "=" * 50)
        print("WIPE COMPLETED")
        print("=" * 50)
        print(f"• Device: {device}")
        print(f"• Size: {size / (1024**3):.2f} GB")
        print(f"• Time: {total_time:.2f} seconds")
        print(f"• Average speed: {avg_speed:.2f} MB/s")
        print("• Status: Successfully wiped")

    except KeyboardInterrupt:
        # Get actual progress from strategy if it was created
        if 'strategy' in locals():
            written = strategy.written
        print("\n\n⚠️  Wipe interrupted by user")
        print(f"• Progress saved: {written / (1024**3):.2f} GB written")
        print("• To resume: run wipeit with --resume flag")
        save_progress(device, written, size, chunk_size, pretest_results,
                      device_id)
        sys.exit(1)
    except Exception as e:
        # Get actual progress from strategy if it was created
        if 'strategy' in locals():
            written = strategy.written
        print(f"\nError during wipe: {e}")
        save_progress(device, written, size, chunk_size, pretest_results,
                      device_id)
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
        version='wipeit 1.4.2')

    args = parser.parse_args()

    # Check if running as root
    if os.geteuid() != 0:
        print("Error: This program must be run as root (sudo)")
        print("Use: sudo wipeit")
        sys.exit(1)

    # Handle --list option
    if args.list:
        print("Available devices (requires sudo):")
        print("=" * 50)
        list_all_devices()
        return

    # Handle no arguments - show resume info and list devices
    if not args.device:
        # Display resume information if available
        display_resume_info()
        print("Available devices (requires sudo):")
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
        print(f"Cannot proceed with wiping {args.device}")
        print("   The device or its partitions are currently mounted!")
        print()
        if mount_info:
            print("Mounted partitions found:")
            for mount in mount_info:
                print(f"   • {mount}")
            print()
        print("TO FIX THIS ISSUE:")
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
        print("Program terminated for safety.")
        sys.exit(1)

    # Load progress if resuming
    if args.resume:
        print("\n" + "=" * 70)
        print("RESUME STATUS")
        print("=" * 70)
        progress_data = load_progress(args.device)
        if not progress_data:
            print("🚨 No previous progress found for this device")
            print("Starting fresh wipe...")
        else:
            percent = progress_data['progress_percent']
            written_gb = progress_data['written'] / (1024**3)
            total_gb = progress_data['total_size'] / (1024**3)
            print("✓ Found previous session")
            print(f"• Progress: {percent:.2f}% complete")
            print(f"• Written: {written_gb:.2f} GB / {total_gb:.2f} GB")
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
