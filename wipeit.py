#!/usr/bin/env python3
"""
wipeit - Secure device wiping utility
Overwrites block devices with random data for secure data destruction.
"""

__version__ = "0.1.0"

import subprocess
import sys
import os
import fcntl
import struct
import time
import argparse
import json
import signal


def get_device_info(device):
    try:
        # Get size
        size = subprocess.check_output(['blockdev', '--getsize64', device])\
            .decode().strip()
        # Get model and serial
        cmd = ['udevadm', 'info', '--query=property', '--name', device]
        model = subprocess.check_output(cmd).decode()
        lines = model.splitlines()
        info = {line.split('=')[0]: line.split('=')[1]
                for line in lines if '=' in line}
        print(f"Device: {device}")
        print(f"Size: {int(size) / (1024**3):.2f} GB")
        if 'ID_MODEL' in info:
            print(f"Model: {info['ID_MODEL']}")
        if 'ID_SERIAL_SHORT' in info:
            print(f"Serial: {info['ID_SERIAL_SHORT']}")
        # Get partitions and mount points
        cmd = ['lsblk', '-o', 'NAME,SIZE,TYPE,MOUNTPOINTS', device]
        partitions = subprocess.check_output(cmd).decode()
        print("Device and partitions:\n" + partitions)
        # Check if mounted
        mount_output = subprocess.check_output(['mount']).decode()
        if device in mount_output:
            print(f"Warning: {device} or its partitions appear to be mounted.")
        else:
            print(f"{device} does not appear to be mounted.")
    except Exception as e:
        print(f"Error getting info: {e}")


def list_all_devices():
    try:
        output = subprocess.check_output(['lsblk', '-dno', 'NAME,TYPE'])\
            .decode().splitlines()
        disks = ['/dev/' + line.split()[0]
                 for line in output
                 if len(line.split()) > 1 and line.split()[1] == 'disk']
        for device in disks:
            get_device_info(device)
            print("\n---\n")
    except Exception as e:
        print(f"Error listing devices: {e}")


def parse_size(size_str):
    """Parse size string with M, G, T suffix (e.g., '100M', '1G', '500M')."""
    size_str = size_str.upper().strip()

    # Extract number and suffix
    if size_str[-1] in ['M', 'G', 'T']:
        try:
            value = float(size_str[:-1])
            suffix = size_str[-1]
        except ValueError:
            raise ValueError(f"Invalid size format: {size_str}")
    else:
        raise ValueError(f"Size must end with M, G, or T: {size_str}")

    # Convert to bytes
    multipliers = {
        'M': 1024 * 1024,
        'G': 1024 * 1024 * 1024,
        'T': 1024 * 1024 * 1024 * 1024
    }

    size_bytes = int(value * multipliers[suffix])

    # Validate range (1M to 1T)
    min_size = 1024 * 1024  # 1M
    max_size = 1024 * 1024 * 1024 * 1024  # 1T

    if size_bytes < min_size:
        raise ValueError("Buffer size must be at least 1M")
    if size_bytes > max_size:
        raise ValueError("Buffer size must not exceed 1T")

    return size_bytes


def get_block_device_size(device):
    with open(device, 'rb') as fd:
        buf = bytearray(8)
        fcntl.ioctl(fd.fileno(), 0x80081272, buf)  # BLKGETSIZE64
        return struct.unpack('Q', buf)[0]


def get_progress_file(device):
    """Get the path to the progress file for a device."""
    device_name = os.path.basename(device)
    return f"wipeit_progress_{device_name}.json"


def save_progress(device, written, total_size, chunk_size):
    """Save current progress to a file."""
    progress_file = get_progress_file(device)
    progress_data = {
        'device': device,
        'written': written,
        'total_size': total_size,
        'chunk_size': chunk_size,
        'timestamp': time.time(),
        'progress_percent': (written / total_size) * 100
    }
    try:
        with open(progress_file, 'w') as f:
            json.dump(progress_data, f, indent=2)
    except Exception as e:
        print(f"Warning: Could not save progress: {e}")


def load_progress(device):
    """Load progress from file if it exists."""
    progress_file = get_progress_file(device)
    if not os.path.exists(progress_file):
        return None

    try:
        with open(progress_file, 'r') as f:
            progress_data = json.load(f)

        # Verify the device matches
        if progress_data.get('device') != device:
            return None

        # Check if progress file is recent (within 24 hours)
        if time.time() - progress_data.get('timestamp', 0) > 86400:
            return None

        return progress_data
    except Exception:
        return None


def clear_progress(device):
    """Remove the progress file."""
    progress_file = get_progress_file(device)
    try:
        if os.path.exists(progress_file):
            os.remove(progress_file)
    except Exception:
        pass


def find_resume_files():
    """Find all progress files in the current directory."""
    import glob
    progress_files = glob.glob("wipeit_progress_*.json")
    resume_info = []

    for progress_file in progress_files:
        try:
            with open(progress_file, 'r') as f:
                progress_data = json.load(f)

            # Check if progress file is recent (within 24 hours)
            if time.time() - progress_data.get('timestamp', 0) <= 86400:
                resume_info.append(progress_data)
        except Exception:
            # Skip corrupted or invalid progress files
            continue

    return resume_info


def display_resume_info():
    """Display information about available resume files."""
    resume_files = find_resume_files()

    if not resume_files:
        return False

    print("🔄 Found pending wipe operations:")
    print("=" * 50)

    for i, progress_data in enumerate(resume_files, 1):
        device = progress_data['device']
        written = progress_data['written']
        total_size = progress_data['total_size']
        progress_percent = progress_data['progress_percent']
        timestamp = progress_data['timestamp']
        chunk_size = progress_data['chunk_size']

        print(f"\n{i}. Device: {device}")
        print(f"   Progress: {progress_percent:.2f}% complete")
        print(f"   Written: {written / (1024**3):.2f} GB / {total_size / (1024**3):.2f} GB")
        print(f"   Buffer size: {chunk_size / (1024**2):.0f} MB")
        print(f"   Started: {time.ctime(timestamp)}")
        print(f"   Resume command: sudo ./wipeit.py --resume {device}")

    print(f"\n💡 To resume any operation, use: sudo ./wipeit.py --resume <device>")
    print(f"💡 To start fresh, the progress file will be overwritten")
    print("=" * 50)

    return True


def wipe_device(device, chunk_size=100 * 1024 * 1024, resume=False):
    try:
        size = get_block_device_size(device)
        written = 0
        start_time = time.time()

        # Check for existing progress
        if resume:
            progress_data = load_progress(device)
            if progress_data:
                written = progress_data['written']
                print(f"Resuming wipe from {written / (1024**3):.2f} GB "
                      f"({progress_data['progress_percent']:.2f}% complete)")
                print(f"Previous session:"
                      f" {time.ctime(progress_data['timestamp'])}")
            else:
                print("No previous progress found, starting from beginning")

        # Set up signal handler for graceful interruption
        def signal_handler(signum, frame):
            print(f"\nWipe interrupted at {written / (1024**3):.2f} GB "
                  f"({written / size * 100:.2f}% complete)")
            save_progress(device, written, size, chunk_size)
            print("Progress saved. To resume, run:")
            print(f"  sudo ./wipeit.py --resume {device}")
            sys.exit(0)

        signal.signal(signal.SIGINT, signal_handler)

        with open(device, 'wb') as f:
            # Seek to the resume position
            if written > 0:
                f.seek(written)

            while written < size:
                remaining = size - written
                to_write = min(chunk_size, remaining)
                data = os.urandom(to_write)
                f.write(data)
                written += to_write

                # Save progress every 1GB or every 10 chunks,
                # whichever is smaller
                if written % (1024**3) == 0 or \
                   written % (chunk_size * 10) == 0:
                    save_progress(device, written, size, chunk_size)

                elapsed = time.time() - start_time
                speed = written / elapsed / (1024**2) if elapsed > 0 else 0
                eta = (size - written) / (written / elapsed) \
                    if elapsed > 0 and written > 0 else 0
                print(f"Progress: {written / size * 100:.2f}% "
                      f"| Written: {written / (1024**3):.2f} GB | "
                      f"Speed: {speed:.2f} MB/s | "
                      f"ETA: {eta / 60:.2f} min | "
                      f"Buffer: {chunk_size / (1024**2):.0f}M")

        # Wipe completed successfully
        clear_progress(device)
        print("\n✅ Wipe completed successfully!")
        print(f"Total written: {written / (1024**3):.2f} GB")

    except KeyboardInterrupt:
        print(f"\nWipe interrupted at {written / (1024**3):.2f} GB "
              f"({written / size * 100:.2f}% complete)")
        save_progress(device, written, size, chunk_size)
        print("Progress saved. To resume, run:")
        print(f"  sudo ./wipeit.py --resume {device}")
    except Exception as e:
        print(f"Error wiping: {e}")
        # Save progress even on error
        if 'written' in locals():
            save_progress(device, written, size, chunk_size)


def main():
    parser = argparse.ArgumentParser(
        description="Wipe device script",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Buffer size examples:
  100M  - 100 megabytes (default)
  1G    - 1 gigabyte
  500M  - 500 megabytes
  1T    - 1 terabyte (max)

Range: 1M to 1T
        """)
    parser.add_argument("device", nargs="?",
                        help="The device to wipe, e.g., /dev/sdx")
    parser.add_argument("-b", "--buffer-size",
                        default="100M",
                        help="Write buffer size (e.g., 100M, 1G, 500M). "
                             "Range: 1M to 1T (default: 100M)")
    parser.add_argument("--resume", action="store_true",
                        help="Resume a previously interrupted wipe operation")
    parser.add_argument("-v", "--version", action="version",
                        version=f"wipeit {__version__}")
    args = parser.parse_args()

    if args.device is None:
        # Check for resume files first (works without root)
        if display_resume_info():
            print("\n" + "=" * 50)
            print("📋 Available devices (requires sudo):")
            print("=" * 50)

        # Check if running as root (after parsing args so --help works)
        if os.geteuid() != 0:
            print("Error: This program must be run as root (sudo) to list devices.")
            print("Use: sudo ./wipeit.py")
            sys.exit(1)

        list_all_devices()
    else:
        # Check if running as root (after parsing args so --help works)
        if os.geteuid() != 0:
            print("Error: This program must be run as root (sudo).")
            sys.exit(1)
        # Parse buffer size
        try:
            chunk_size = parse_size(args.buffer_size)
            print(f"Using buffer size: {chunk_size / (1024**2):.0f} MB "
                  f"({chunk_size / (1024**3):.2f} GB)")
        except ValueError as e:
            print(f"Error: {e}")
            sys.exit(1)

        get_device_info(args.device)

        # Check for existing progress if not resuming
        if not args.resume:
            progress_data = load_progress(args.device)
            if progress_data:
                print("\n⚠️  Found previous wipe session:")
                print(f"   Progress: {progress_data['progress_percent']:.2f}% "
                      f"({progress_data['written'] / (1024**3):.2f} GB)")
                print(f"   Started: {time.ctime(progress_data['timestamp'])}")
                print("\nOptions:")
                print("   1. Resume previous session:"
                      f" sudo ./wipeit.py --resume {args.device}")
                print("   2. Start fresh (will overwrite previous progress)")
                choice = input("\nStart fresh wipe? (y/n): ")
                if choice.lower() != 'y':
                    print("Aborted.")
                    return
                else:
                    clear_progress(args.device)
                    print("Previous progress cleared.")

        confirm = input("Confirm wipe (y/n): ")
        if confirm.lower() == 'y':
            wipe_device(args.device, chunk_size, args.resume)
        else:
            print("Aborted.")


if __name__ == "__main__":
    main()
