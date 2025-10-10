#!/usr/bin/env python3
"""
wipeit - Secure device wiping utility
Overwrites block devices with random data for secure data destruction.
"""

__version__ = "0.4.0"

import argparse
import fcntl
import json
import os
import signal
import struct
import subprocess
import sys
import time


def get_device_info(device):
    try:
        size = subprocess.check_output(['blockdev', '--getsize64', device])\
            .decode().strip()
        cmd = ['udevadm', 'info', '--query=property', '--name', device]
        model = subprocess.check_output(cmd).decode()
        lines = model.splitlines()
        info = {line.split('=')[0]: line.split('=')[1]
                for line in lines if '=' in line}
        print("=" * 70)
        print("DEVICE INFORMATION")
        print("=" * 70)
        print(f"• Device: {device}")
        print(f"• Size: {int(size) / (1024**3):.2f} GB")
        if 'ID_MODEL' in info:
            print(f"• Model: {info['ID_MODEL']}")
        if 'ID_SERIAL_SHORT' in info:
            print(f"• Serial: {info['ID_SERIAL_SHORT']}")

        disk_type, confidence, details = detect_disk_type(device)
        print(f"• Type: {disk_type} (confidence: {confidence})")
        if details:
            print(f"• Detection details: {', '.join(details)}")

        cmd = ['lsblk', '-o', 'NAME,SIZE,TYPE,MOUNTPOINTS', device]
        partitions = subprocess.check_output(cmd).decode()
        print("• Device and partitions:")
        print(partitions)
        mount_output = subprocess.check_output(['mount']).decode()
        if device in mount_output:
            print(f"• Warning: {device} or its partitions appear to be "
                  f"mounted.")
        else:
            print(f"• {device} does not appear to be mounted.")
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

    if size_str[-1] in ['M', 'G', 'T']:
        try:
            value = float(size_str[:-1])
            suffix = size_str[-1]
        except ValueError:
            raise ValueError(f"Invalid size format: {size_str}")
    else:
        raise ValueError(f"Size must end with M, G, or T: {size_str}")

    multipliers = {
        'M': 1024 * 1024,
        'G': 1024 * 1024 * 1024,
        'T': 1024 * 1024 * 1024 * 1024
    }

    size_bytes = int(value * multipliers[suffix])

    min_size = 1024 * 1024
    max_size = 1024 * 1024 * 1024 * 1024

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


def detect_disk_type(device, debug=False):
    """
    Detect the type of storage device (HDD, SSD, NVMe).
    Returns a tuple: (disk_type, confidence_level, details)
    """
    try:
        device_name = os.path.basename(device)
        if debug:
            print(f"   Debug: Detecting disk type for {device}")
            print(f"   Debug: Device name: {device_name}")

        rotational_path = f"/sys/block/{device_name}/queue/rotational"
        if os.path.exists(rotational_path):
            with open(rotational_path, 'r') as f:
                is_rotational = f.read().strip() == '1'
            if debug:
                print(f"   Debug: Rotational attribute: {is_rotational}")
        else:
            is_rotational = None
            if debug:
                print(f"   Debug: Rotational path not found: "
                      f"{rotational_path}")

        is_nvme = device_name.startswith('nvme')
        is_mmc = device_name.startswith('mmc')

        try:
            cmd = ['udevadm', 'info', '--query=property', '--name', device]
            udev_output = subprocess.check_output(cmd).decode()
            udev_props = {}
            for line in udev_output.splitlines():
                if '=' in line:
                    key, value = line.split('=', 1)
                    udev_props[key] = value
        except Exception:
            udev_props = {}

        ssd_indicators = []
        if 'ID_ATA_ROTATION_RATE_RPM' in udev_props:
            rpm = udev_props['ID_ATA_ROTATION_RATE_RPM']
            if rpm == '0':
                ssd_indicators.append('zero_rpm')
            else:
                ssd_indicators.append(f'rpm_{rpm}')

        nvme_indicators = []
        if ('ID_BUS' in udev_props and
                udev_props['ID_BUS'] == 'nvme'):
            nvme_indicators.append('nvme_bus')

        disk_type = "UNKNOWN"
        confidence = "LOW"
        details = []

        if is_nvme or 'nvme_bus' in nvme_indicators:
            disk_type = "NVMe SSD"
            confidence = "HIGH"
            details.append("NVMe interface detected")
        elif is_mmc:
            disk_type = "eMMC/MMC"
            confidence = "HIGH"
            details.append("MMC interface detected")
        elif is_rotational is False:
            disk_type = "SSD"
            confidence = "HIGH"
            details.append("Non-rotational device")
        elif is_rotational is True:
            disk_type = "HDD"
            confidence = "HIGH"
            details.append("Rotational device")
        elif 'zero_rpm' in ssd_indicators:
            disk_type = "SSD"
            confidence = "MEDIUM"
            details.append("Zero RPM indicates SSD")
        elif any('rpm_' in indicator for indicator in ssd_indicators):
            disk_type = "HDD"
            confidence = "MEDIUM"
            details.append(f"Rotational speed detected: "
                           f"{ssd_indicators[0]}")
        else:
            model = udev_props.get('ID_MODEL', '').upper()
            if any(keyword in model for keyword in
                   ['SSD', 'SOLID STATE']):
                disk_type = "SSD"
                confidence = "MEDIUM"
                details.append("SSD mentioned in model name")
            elif any(keyword in model for keyword in
                     ['HDD', 'HARD DISK', 'HARDDRIVE']):
                disk_type = "HDD"
                confidence = "MEDIUM"
                details.append("HDD mentioned in model name")

        return disk_type, confidence, details

    except Exception as e:
        return "UNKNOWN", "LOW", [f"Detection failed: {str(e)}"]


def perform_hdd_pretest(device, chunk_size=100 * 1024 * 1024):
    """
    Perform pretest on HDD to measure write speeds at different positions.
    Returns dictionary with speed measurements and recommended algorithm.
    """
    print("=" * 70)
    print("HDD PRETEST")
    print("=" * 70)
    print("• Performing HDD pretest to optimize wiping algorithm...")
    print("  This will test write speeds at different disk positions.")
    print("  WARNING: This will write test data to the disk!")

    try:
        size = get_block_device_size(device)
        print(f"  • Disk size: {size / (1024**3):.2f} GB")
        print(f"  • Test chunk size: {chunk_size / (1024**2):.0f} MB")

        test_positions = [
            ("beginning", 0),
            ("middle", size // 2),
            ("end", size - chunk_size)
        ]

        print(f"  • Test positions: {len(test_positions)} locations")

        results = {}
        test_data = os.urandom(chunk_size)

        with open(device, 'wb') as f:
            for position_name, position in test_positions:
                print(f"  • Testing {position_name} of disk...")

                f.seek(position)

                start_time = time.time()
                f.write(test_data)
                f.flush()
                os.fsync(f.fileno())
                end_time = time.time()

                duration = end_time - start_time
                speed_mbps = (chunk_size / (1024 * 1024)) / duration

                results[position_name] = {
                    'position': position,
                    'speed_mbps': speed_mbps,
                    'duration': duration
                }

                print(f"    • {position_name.capitalize()}: "
                      f"{speed_mbps:.2f} MB/s")

        speeds = [results[pos]['speed_mbps'] for pos in results]
        avg_speed = sum(speeds) / len(speeds)
        speed_variance = max(speeds) - min(speeds)

        if speed_variance > avg_speed * 0.3:
            algorithm = "adaptive_chunk"
            reason = ("High speed variance detected - "
                      "adaptive chunk sizing recommended")
        elif avg_speed < 50:
            algorithm = "small_chunk"
            reason = ("Low average speed - "
                      "small chunks for better responsiveness")
        else:
            algorithm = "standard"
            reason = "Consistent speeds - standard algorithm optimal"

        results['analysis'] = {
            'average_speed': avg_speed,
            'speed_variance': speed_variance,
            'recommended_algorithm': algorithm,
            'reason': reason
        }

        print("\n" + "=" * 70)
        print("PRETEST ANALYSIS")
        print("=" * 70)
        print(f"• Average speed: {avg_speed:.2f} MB/s")
        print(f"• Speed variance: {speed_variance:.2f} MB/s")
        print(f"• Recommended algorithm: {algorithm}")
        print(f"• Reason: {reason}")

        return results

    except Exception as e:
        print(f"• Pretest failed: {e}")
        print("   Error details:", str(e))
        print("   Falling back to standard algorithm")
        return None


def get_progress_file(device):
    """Get the path to the progress file for a device."""
    device_name = os.path.basename(device)
    return f"wipeit_progress_{device_name}.json"


def save_progress(device, written, total_size, chunk_size,
                  pretest_results=None):
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

    if pretest_results:
        progress_data['pretest_results'] = pretest_results

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

            if time.time() - progress_data.get('timestamp', 0) <= 86400:
                resume_info.append(progress_data)
        except Exception:
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
        print(f"   Written: {written / (1024**3):.2f} GB / "
              f"{total_size / (1024**3):.2f} GB")
        print(f"   Buffer size: {chunk_size / (1024**2):.0f} MB")
        print(f"   Started: {time.ctime(timestamp)}")
        print(f"   Resume command: sudo ./wipeit.py --resume {device}")

    print("\n💡 To resume any operation, use: "
          "sudo ./wipeit.py --resume <device>")
    print("💡 To start fresh, the progress file will be overwritten")
    print("=" * 50)

    return True


def wipe_device(device, chunk_size=100 * 1024 * 1024, resume=False,
                skip_pretest=False):
    try:
        size = get_block_device_size(device)
        written = 0
        start_time = time.time()

        disk_type, confidence, details = detect_disk_type(device)
        pretest_results = None

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
                print("✅ Using previous pretest results for algorithm.")
                pretest_results = existing_pretest_results
                algo = pretest_results['analysis']['recommended_algorithm']
                print(f"   Previous algorithm: {algo}")
            else:
                print("\n🔄 HDD detected - pretest will be performed "
                      "to optimize wiping algorithm...")
                print("   This will test write speeds at different "
                      "disk positions.")
                print("   The pretest may take a few minutes "
                      "depending on disk size.")

                proceed = input("\nProceed with HDD pretest? (y/n): ")
                if proceed.lower() != 'y':
                    print("   Pretest skipped by user. "
                          "Using standard algorithm.")
                    pretest_results = None
                else:
                    print("\n🔄 Starting HDD pretest...")
                    pretest_results = perform_hdd_pretest(device, chunk_size)

            if pretest_results:
                algo = pretest_results['analysis']['recommended_algorithm']
                if not existing_pretest_results:
                    print(f"\n✅ Pretest complete. Using {algo} algorithm.")

                if algo == "small_chunk":
                    chunk_size = min(chunk_size, 50 * 1024 * 1024)
                    if not existing_pretest_results:
                        print(f"  Adjusted chunk size to "
                              f"{chunk_size / (1024**2):.0f} MB for "
                              f"better responsiveness")
                elif algo == "adaptive_chunk":
                    if not existing_pretest_results:
                        print("  Using adaptive chunk sizing based on "
                              "disk position")
            else:
                print("  Using standard algorithm due to pretest failure")
        elif disk_type == "HDD" and skip_pretest:
            print("✅ HDD detected - skipping pretest, using standard "
                  "algorithm")
        else:
            print(f"✅ {disk_type} detected - using standard algorithm")

        def signal_handler(signum, frame):
            print(f"\nWipe interrupted at {written / (1024**3):.2f} GB "
                  f"({written / size * 100:.2f}% complete)")
            save_progress(device, written, size, chunk_size, pretest_results)
            print("Progress saved. To resume, run:")
            print(f"  sudo ./wipeit.py --resume {device}")
            sys.exit(0)

        signal.signal(signal.SIGINT, signal_handler)

        print("\n" + "=" * 70)
        print("WIPING PROCESS")
        print("=" * 70)
        print("• Starting secure wipe with random data...")

        with open(device, 'wb') as f:
            if written > 0:
                f.seek(written)

            last_milestone = int(written / size * 100) // 5 * 5

            while written < size:
                remaining = size - written

                current_chunk_size = chunk_size
                if (pretest_results and
                        pretest_results['analysis'][
                            'recommended_algorithm'] == "adaptive_chunk"):
                    position_ratio = written / size
                    if position_ratio < 0.1:
                        current_chunk_size = int(min(chunk_size * 1.5,
                                                     remaining))
                    elif position_ratio > 0.9:
                        current_chunk_size = int(min(chunk_size * 0.7,
                                                     remaining))

                to_write = min(current_chunk_size, remaining)
                data = os.urandom(to_write)
                f.write(data)
                f.flush()
                os.fsync(f.fileno())
                written += to_write

                if written % (1024**3) == 0 or \
                   written % (chunk_size * 10) == 0:
                    save_progress(device, written, size, chunk_size,
                                  pretest_results)

                elapsed = time.time() - start_time
                speed = written / elapsed / (1024**2) if elapsed > 0 else 0
                eta = (size - written) / (written / elapsed) \
                    if elapsed > 0 and written > 0 else 0

                current_milestone = int(written / size * 100) // 5 * 5
                progress_percent = written / size * 100

                algorithm_info = ""
                if pretest_results:
                    algo = pretest_results['analysis'][
                        'recommended_algorithm']
                    if algo == "adaptive_chunk":
                        algorithm_info = " | Algorithm: Adaptive"
                    elif algo == "small_chunk":
                        algorithm_info = " | Algorithm: Small Chunk"

                # Create a visual progress bar
                bar_length = 40
                filled_length = int(bar_length * progress_percent / 100)
                bar = "█" * filled_length + "░" * (bar_length - filled_length)
                # Format the progress line with better visual structure
                progress_line = (
                    f"\r• [{bar}] {progress_percent:.1f}% "
                    f"│ {written / (1024**3):.2f} GB "
                    f"│ {speed:.1f} MB/s "
                    f"│ {eta / 60:.1f} min "
                    f"│ {current_chunk_size / (1024**2):.0f}M"
                    f"{algorithm_info}")

                if (current_milestone > last_milestone and
                        current_milestone >= 5):
                    estimated_finish = time.time() + eta
                    finish_time_str = time.strftime(
                        "%I:%M %p", time.localtime(estimated_finish))
                    progress_line += (
                        f" │ {finish_time_str}")
                    last_milestone = current_milestone

                print(progress_line, end="", flush=True)

        clear_progress(device)
        print("\n\n" + "=" * 70)
        print("WIPE COMPLETED")
        print("=" * 70)
        print("• Wipe completed successfully!")
        print(f"• Total written: {written / (1024**3):.2f} GB")
        print("• Device has been securely wiped with random data")

    except KeyboardInterrupt:
        print("\n\n" + "=" * 70)
        print("WIPE INTERRUPTED")
        print("=" * 70)
        print(f"• Wipe interrupted at {written / (1024**3):.2f} GB "
              f"({written / size * 100:.2f}% complete)")
        save_progress(device, written, size, chunk_size, pretest_results)
        print("• Progress saved. To resume, run:")
        print(f"  sudo ./wipeit.py --resume {device}")
    except Exception as e:
        print(f"Error wiping: {e}")
        if 'written' in locals():
            save_progress(device, written, size, chunk_size, pretest_results)


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

Disk type detection and HDD pretest:
  wipeit automatically detects disk type (HDD/SSD/NVMe) and performs
  pretests on HDDs to optimize wiping algorithms. Use --skip-pretest
  to bypass this feature and use standard algorithm.
        """)
    parser.add_argument("device", nargs="?",
                        help="The device to wipe, e.g., /dev/sdx")
    parser.add_argument("-b", "--buffer-size",
                        default="100M",
                        help="Write buffer size (e.g., 100M, 1G, 500M). "
                             "Range: 1M to 1T (default: 100M)")
    parser.add_argument("--resume", action="store_true",
                        help="Resume a previously interrupted wipe operation")
    parser.add_argument("--skip-pretest", action="store_true",
                        help="Skip HDD pretest and use standard algorithm")
    parser.add_argument("--debug", action="store_true",
                        help="Enable debug output for disk detection")
    parser.add_argument("-v", "--version", action="version",
                        version=f"wipeit {__version__}")
    args = parser.parse_args()

    if args.device is None:
        if display_resume_info():
            print("\n" + "=" * 50)
            print("📋 Available devices (requires sudo):")
            print("=" * 50)

        if os.geteuid() != 0:
            print("Error: This program must be run as root (sudo) "
                  "to list devices.")
            print("Use: sudo ./wipeit.py")
            sys.exit(1)

        list_all_devices()
    else:
        if os.geteuid() != 0:
            print("Error: This program must be run as root (sudo).")
            sys.exit(1)
        try:
            chunk_size = parse_size(args.buffer_size)
            print("=" * 70)
            print("CONFIGURATION")
            print("=" * 70)
            print(f"• Using buffer size: {chunk_size / (1024**2):.0f} MB "
                  f"({chunk_size / (1024**3):.2f} GB)")
        except ValueError as e:
            print(f"Error: {e}")
            sys.exit(1)

        get_device_info(args.device)

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
            wipe_device(args.device, chunk_size, args.resume,
                        args.skip_pretest)
        else:
            print("Aborted.")


if __name__ == "__main__":
    main()
