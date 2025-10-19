#!/usr/bin/env python3
"""
wipeit - Secure device wiping utility
Overwrites block devices with random data for secure data destruction.
"""

import argparse
import json
import os
import subprocess
import sys
import time

from device_detector import DeviceDetector
from disk_pretest import DiskPretest
from global_constants import (
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


def parse_size(size_str) -> int:
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


def save_progress(device, written, total_size,
                  chunk_size, pretest_results=None, device_id=None,
                  algorithm=None):
    """
    Save wipe progress to file.

    Args:
        device: Device path (e.g., '/dev/sdb')
        written: Bytes written so far
        total_size: Total device size in bytes
        chunk_size: Chunk size used for wiping
        pretest_results: Optional pretest results
        device_id: Optional device unique identifiers (serial, model, etc.)
        algorithm: Optional algorithm name for resume consistency
    """
    from progress_file_version import ProgressFileVersion

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
        'device_id': device_id,
        'algorithm': algorithm
    }

    # Add version number using ProgressFileVersion
    progress_data = ProgressFileVersion.add_version_to_data(progress_data)

    try:
        with open(progress_file, 'w') as f:
            json.dump(progress_data, f, indent=2)
            f.flush()
            os.fsync(f.fileno())
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
    from progress_file_version import ProgressFileVersion

    progress_file = PROGRESS_FILE_NAME

    if not os.path.exists(progress_file):
        return None

    try:
        with open(progress_file, 'r') as f:
            progress_data = json.load(f)

        # Migrate progress data if needed
        progress_data, was_migrated, warning = \
            ProgressFileVersion.migrate_progress_data(progress_data)

        if warning:
            print(f"⚠️  {warning}")

        # Validate progress data
        is_valid, error = \
            ProgressFileVersion.validate_progress_data(progress_data)
        if not is_valid:
            print(f"⚠️  Progress file validation failed: {error}")
            return None

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
                    print("     - Run: sudo wipeit --resume")
                    print("       (auto-detects drive by serial number)")
                    print()
                    print("  3. To clear this progress file and start fresh:")
                    print(f"     rm {PROGRESS_FILE_NAME}")
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
                          f"{saved_id['size'] / GIGABYTE:.2f} GB")
                    print(f"Current size:  "
                          f"{current_id['size'] / GIGABYTE:.2f} GB")
                    print()
                    print("⚠️  This is a DIFFERENT drive or the drive has "
                          "been repartitioned!")
                    print()
                    print("WHAT TO DO:")
                    print("  1. Verify you have the correct drive connected")
                    print("  2. To start a fresh wipe on this drive:")
                    print(f"     sudo wipeit {device}")
                    print("  3. To clear the old progress file:")
                    print(f"     rm {PROGRESS_FILE_NAME}")
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


def clear_progress():
    """Clear progress file."""
    progress_file = PROGRESS_FILE_NAME
    try:
        if os.path.exists(progress_file):
            os.remove(progress_file)
    except Exception as e:
        print(f"Warning: Could not clear progress: {e}")


def find_device_by_serial_model():
    """
    Search all available drives for one matching the serial and model
    from the progress file.

    Returns:
        tuple: (device_path, device_id) if found, (None, None) otherwise
            - device_path: str like '/dev/sdb'
            - device_id: dict with 'serial', 'model', 'size' keys
    """
    # Load progress file to get saved device_id
    progress_data = find_resume_file()

    if not progress_data:
        return None, None

    if 'device_id' not in progress_data or not progress_data['device_id']:
        return None, None

    saved_id = progress_data['device_id']
    saved_serial = saved_id.get('serial')
    saved_model = saved_id.get('model')

    if not saved_serial:
        # Can't match without serial number
        return None, None

    # Get all block devices
    try:
        output = subprocess.check_output(['lsblk', '-dno', 'NAME,TYPE'])\
            .decode().splitlines()
        disks = ['/dev/' + line.split()[0]
                 for line in output
                 if len(line.split()) > 1 and line.split()[1] == 'disk']
    except Exception as e:
        print(f"Error listing devices: {e}")
        return None, None

    # Search for matching device
    for device in disks:
        try:
            detector = DeviceDetector(device)
            current_id = detector.get_unique_id()

            # Match by serial number (primary identifier)
            if (current_id.get('serial') and
                    current_id['serial'] == saved_serial):
                # Optionally verify model too for extra safety
                if saved_model and current_id.get('model'):
                    if current_id['model'] != saved_model:
                        print(f"⚠️  Warning: Serial matches but model "
                              f"differs on {device}")
                        print(f"   Expected: {saved_model}")
                        print(f"   Found: {current_id['model']}")
                        # Still return it - serial is the primary identifier

                return device, current_id
        except Exception:
            # Skip devices we can't read
            continue

    return None, None


def find_resume_file():
    """
    Find progress file if it exists.

    Returns:
        dict or None: Progress data if file exists and is valid, None otherwise
    """
    from progress_file_version import ProgressFileVersion

    progress_file = PROGRESS_FILE_NAME

    if os.path.exists(progress_file):
        try:
            with open(progress_file, 'r') as f:
                progress_data = json.load(f)

            # Migrate progress data if needed (silently for find)
            progress_data, _, _ = \
                ProgressFileVersion.migrate_progress_data(progress_data)

            return progress_data
        except Exception:
            pass

    return None


def display_resume_info():
    """
    Display available resume options.

    Returns:
        bool: True if progress file exists and was displayed, False otherwise
    """
    progress_data = find_resume_file()

    if not progress_data:
        return False

    print("=" * 50)
    print("RESUME OPTIONS")
    print("=" * 50)
    print("Found previous wipe session that can be resumed:")
    print()

    try:
        device = progress_data['device']
        written = progress_data['written']
        total_size = progress_data['total_size']
        progress_percent = progress_data['progress_percent']
        timestamp = progress_data['timestamp']

        print(f"• Device: {device}")
        print(f"  Progress: {progress_percent:.2f}% complete")
        written_gb = written / GIGABYTE
        total_gb = total_size / GIGABYTE
        print(f"  Written: {written_gb:.2f} GB / {total_gb:.2f} GB")
        print(f"  Started: {time.ctime(timestamp)}")
        print()
    except Exception as e:
        print(f"Error reading progress data: {e}")
        return False

    print("=" * 50)

    return True


def calculate_average_speed(total_bytes, elapsed_seconds):
    """
    Calculate average speed in MB/s.

    Args:
        total_bytes (int): Total bytes processed
        elapsed_seconds (float): Time elapsed in seconds

    Returns:
        float: Average speed in MB/s, or 0 if elapsed_seconds is 0
    """
    if elapsed_seconds > 0:
        return total_bytes / elapsed_seconds / MEGABYTE
    else:
        return 0.0


def create_wipe_strategy(algorithm, device, size, chunk_size, written,
                         pretest_results, progress_callback):
    """
    Factory function to create the appropriate wipe strategy.

    Args:
        algorithm (str): Algorithm name ('adaptive_chunk', 'small_chunk',
                         or 'standard')
        device (str): Device path
        size (int): Device size in bytes
        chunk_size (int): Chunk size in bytes
        written (int): Bytes already written
        pretest_results (dict or None): Pretest results
        progress_callback (callable): Progress callback function

    Returns:
        WipeStrategy: Instance of the appropriate strategy class
    """
    if algorithm == "adaptive_chunk":
        print("Using adaptive chunk sizing for optimal performance")
        return AdaptiveStrategy(
            device, size, chunk_size, written, pretest_results,
            progress_callback
        )
    elif algorithm == "small_chunk":
        chunk_mb = min(chunk_size, MAX_SMALL_CHUNK_SIZE) / MEGABYTE
        print(f"Using small chunk size: {chunk_mb:.0f} MB")
        return SmallChunkStrategy(
            device, size, chunk_size, written, pretest_results,
            progress_callback
        )
    else:
        return StandardStrategy(
            device, size, chunk_size, written, pretest_results,
            progress_callback
        )


def handle_hdd_pretest(device, chunk_size, existing_pretest_results, written,
                       size, device_id):
    """
    Handle HDD pretest: use existing results or run new pretest.

    Args:
        device (str): Device path
        chunk_size (int): Chunk size in bytes
        existing_pretest_results (dict or None): Previously saved pretest
                                                  results
        written (int): Bytes already written (for progress save)
        size (int): Total device size
        device_id (dict): Device identification info

    Returns:
        dict or None: Pretest results dictionary, or None if no pretest ran
    """
    if existing_pretest_results:
        print("Using previous pretest results")
        return existing_pretest_results

    print("HDD detected - performing pretest to optimize "
          "wiping algorithm...")
    pretest = DiskPretest(device, chunk_size)
    results = pretest.run_pretest()

    if results:
        pretest_results = results.to_dict()
        save_progress(device, written, size, chunk_size,
                      pretest_results, device_id)
        return pretest_results
    else:
        print("Pretest failed, using standard algorithm")
        return None


def handle_resume(device):
    """
    Handle resume logic: load progress and display resume information.

    Args:
        device (str): Device path

    Returns:
        tuple: (written, existing_pretest_results, saved_chunk_size,
                saved_algorithm) where:
            - written: bytes written so far (0 if no progress)
            - existing_pretest_results: dict of pretest results or None
            - saved_chunk_size: saved chunk size in bytes or None
            - saved_algorithm: saved algorithm name or None
    """
    progress_data = load_progress(device)

    if not progress_data:
        print("No previous progress found, starting from beginning")
        return 0, None, None, None

    written = progress_data['written']
    print(f"Resuming wipe from {written / GIGABYTE:.2f} GB "
          f"({progress_data['progress_percent']:.2f}% complete)")
    print(f"Previous session: {time.ctime(progress_data['timestamp'])}")

    existing_pretest_results = None
    if 'pretest_results' in progress_data:
        existing_pretest_results = progress_data['pretest_results']
        print(f"   Found previous pretest results from "
              f"{time.ctime(progress_data['timestamp'])}")

    saved_chunk_size = progress_data.get('chunk_size')
    if saved_chunk_size:
        print(f"ℹ️  Resuming with previous buffer size: "
              f"{saved_chunk_size / MEGABYTE:.0f} MB")

    saved_algorithm = progress_data.get('algorithm')
    if saved_algorithm:
        print(f"ℹ️  Resuming with {saved_algorithm} algorithm")

    return written, existing_pretest_results, saved_chunk_size, \
        saved_algorithm


def wipe_device(device, chunk_size=DEFAULT_CHUNK_SIZE, resume=False,
                skip_pretest=False, force_buffer=False):
    """
    Wipe device using appropriate strategy (WRAPPER).

    This function maintained for backward compatibility.
    New code should use WipeStrategy classes directly.

    Args:
        device: Path to block device
        chunk_size: Base chunk size for wiping
        resume: Whether to resume previous session
        skip_pretest: Whether to skip HDD pretest
        force_buffer: Whether user explicitly specified buffer size

    Raises:
        KeyboardInterrupt: If user interrupts the wipe
        Exception: On I/O or other errors
    """
    from wipe_strategy_factory import WipeStrategyFactory

    written = 0
    size = 0
    start_time = time.time()
    pretest_results = None
    device_id = None  # Initialize to None for exception handlers
    algorithm = None

    try:
        size = DeviceDetector.get_block_device_size(device)

        detector = DeviceDetector(device)
        disk_type, confidence, details = detector.detect_type()
        device_id = detector.get_unique_id()

        print(f"\nDetected disk type: {disk_type} "
              f"(confidence: {confidence})")
        if details:
            print(f"   Detection details: {', '.join(details)}")

        if resume:
            written, existing_pretest_results, saved_chunk_size, \
                saved_algorithm = handle_resume(device)

            if saved_algorithm:
                # Resume with saved algorithm - perfect consistency
                algorithm = saved_algorithm
                chunk_size = saved_chunk_size or chunk_size
                pretest_results = existing_pretest_results
                print("   (continuing with saved algorithm and buffer)")
            elif saved_chunk_size:
                # Old v1 progress file - has chunk_size but no algorithm
                chunk_size = saved_chunk_size
                force_buffer = True
                print("   (resuming with saved buffer size)")
        else:
            written = 0
            existing_pretest_results = None

        # Only determine algorithm if not already set by resume
        if not algorithm:
            if force_buffer:
                # User explicitly specified buffer - skip pretest
                print(f"Using user-specified buffer: "
                      f"{chunk_size / MEGABYTE:.0f} MB")
                algorithm = "buffer_override"
                pretest_results = None
            elif disk_type == "HDD" and not skip_pretest:
                pretest_results = handle_hdd_pretest(
                    device, chunk_size, existing_pretest_results,
                    written, size, device_id)

                if pretest_results:
                    algorithm = pretest_results.get(
                        'recommended_algorithm', 'standard')
                    print(f"Using {algorithm} algorithm based on pretest")
                else:
                    algorithm = "standard"
                    print(f"Using {algorithm} algorithm")
            else:
                algorithm = "standard"
                print(f"Using {algorithm} algorithm")

        def progress_callback(written_bytes, total_bytes, chunk_bytes):
            """Callback for saving progress from strategy."""
            save_progress(device, written_bytes, total_bytes, chunk_bytes,
                          pretest_results, device_id, algorithm)

        strategy = WipeStrategyFactory.create_strategy(
            algorithm=algorithm,
            device_path=device,
            total_size=size,
            chunk_size=chunk_size,
            start_position=written,
            pretest_results=pretest_results,
            progress_callback=progress_callback)

        strategy.wipe()
        written = strategy.written

        clear_progress()

        total_time = time.time() - start_time
        avg_speed = calculate_average_speed(size, total_time)

        print("\n" + "=" * 50)
        print("WIPE COMPLETED")
        print("=" * 50)
        print(f"• Device: {device}")
        print(f"• Size: {size / GIGABYTE:.2f} GB")
        print(f"• Time: {total_time:.2f} seconds")
        print(f"• Average speed: {avg_speed:.2f} MB/s")
        print("• Status: Successfully wiped")

    except KeyboardInterrupt:
        # Get actual progress from strategy if it was created
        if 'strategy' in locals():
            written = strategy.written
        print("\n\n⚠️  Wipe interrupted by user")
        print(f"• Progress saved: {written / GIGABYTE:.2f} GB written")
        print("• To resume: sudo wipeit --resume")
        print("  (will automatically detect the drive by serial number)")
        save_progress(device, written, size, chunk_size, pretest_results,
                      device_id, algorithm)
        sys.exit(1)
    except Exception as e:
        # Get actual progress from strategy if it was created
        if 'strategy' in locals():
            written = strategy.written
        print(f"\nError during wipe: {e}")
        save_progress(device, written, size, chunk_size, pretest_results,
                      device_id, algorithm)
        sys.exit(1)


def setup_argument_parser():
    """
    Set up and return the command-line argument parser.

    Returns:
        argparse.ArgumentParser: Configured argument parser
    """
    parser = argparse.ArgumentParser(
        description='Secure device wiping utility',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  wipeit /dev/sdb                    # Wipe device with default settings
  wipeit -b 1G /dev/sdb             # Use 1GB buffer size
  wipeit --resume                   # Resume previous wipe (auto-detects drive)
  wipeit --resume /dev/sdb          # Resume on specific device (optional)
  wipeit --skip-pretest /dev/sdb    # Skip HDD pretest
  wipeit --list                     # List all available devices

⚠️  WARNING: This tool will PERMANENTLY DESTROY ALL DATA on the target device!
        """
    )

    parser.add_argument(
        'device',
        nargs='?',
        help='Block device to wipe (e.g., /dev/sdb). Optional with --resume.')
    parser.add_argument(
        '-b', '--buffer-size', '--force-buffer-size',
        default='100M',
        help='Buffer size (default: 100M, range: 1M-1T). '
             'When specified, bypasses algorithm selection and uses '
             'this exact buffer size.')
    parser.add_argument('--resume', action='store_true',
                        help='Resume previous wipe session '
                             '(auto-detects drive by serial number)')
    parser.add_argument('--skip-pretest', action='store_true',
                        help='Skip HDD pretest (use standard algorithm)')
    parser.add_argument('--list', action='store_true',
                        help='List all available block devices')
    parser.add_argument(
        '-v',
        '--version',
        action='version',
        version='wipeit 1.6.1')

    return parser


def main():
    """Main function for CLI interface."""
    parser = setup_argument_parser()
    args = parser.parse_args()

    # Detect if user explicitly specified buffer size
    user_specified_buffer = ('-b' in sys.argv or
                             '--buffer-size' in sys.argv or
                             '--force-buffer-size' in sys.argv)

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

    # Handle --resume without device specification (auto-detect)
    if args.resume and not args.device:
        print("=" * 70)
        print("AUTO-DETECTING RESUME DRIVE")
        print("=" * 70)
        detected_device, detected_id = find_device_by_serial_model()

        if detected_device:
            print(f"✓ Found matching drive: {detected_device}")
            print(f"  Serial: {detected_id.get('serial', 'N/A')}")
            print(f"  Model: {detected_id.get('model', 'N/A')}")
            if detected_id.get('size'):
                print(f"  Size: {detected_id['size'] / GIGABYTE:.2f} GB")
            print()
            args.device = detected_device
        else:
            print("🚨 ERROR: Could not find matching drive")
            print()
            progress_data = find_resume_file()
            if progress_data and 'device_id' in progress_data:
                saved_id = progress_data['device_id']
                print("Looking for drive with:")
                if saved_id.get('serial'):
                    print(f"  Serial: {saved_id['serial']}")
                if saved_id.get('model'):
                    print(f"  Model: {saved_id['model']}")
                print()
            else:
                print("No valid progress file found or missing "
                      "device identification.")
                print()

            print("Available drives:")
            print("=" * 50)
            list_all_devices()
            print()
            print("POSSIBLE REASONS:")
            print("  1. The original drive is not connected")
            print("  2. The drive's serial number cannot be read")
            print("  3. The progress file is from a different drive")
            print()
            print("TO RESOLVE:")
            print("  1. Reconnect the original drive and try again")
            print("  2. Manually specify device: "
                  "sudo wipeit --resume /dev/sdX")
            print(f"  3. Start fresh by removing: "
                  f"rm {PROGRESS_FILE_NAME}")
            sys.exit(1)

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
            print("To continue the previous session:")
            print("  sudo wipeit --resume")
            print("  (will automatically detect the drive by serial number)")
            print()

    # Display configuration
    print("=" * DISPLAY_LINE_WIDTH)
    print("CONFIGURATION")
    print("=" * DISPLAY_LINE_WIDTH)
    print(f"• Using buffer size: {buffer_size / MEGABYTE:.0f} MB "
          f"({buffer_size / GIGABYTE:.2f} GB)")

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
            written_gb = progress_data['written'] / GIGABYTE
            total_gb = progress_data['total_size'] / GIGABYTE
            print("✓ Found previous session")
            print(f"• Progress: {percent:.2f}% complete")
            print(f"• Written: {written_gb:.2f} GB / {total_gb:.2f} GB")
            print(f"Resuming wipe from {percent:.2f}% complete")
    else:
        # Clear any existing progress
        clear_progress()

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
    wipe_device(args.device, buffer_size, args.resume, args.skip_pretest,
                user_specified_buffer)


if __name__ == '__main__':
    main()
