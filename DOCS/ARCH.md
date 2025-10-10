# Architecture Documentation

**⚠️ WARNING: This tool is EXTREMELY DESTRUCTIVE and will PERMANENTLY DESTROY data! ⚠️**

## Function Structure and Call Relationships

This document provides an overview of the wipeit codebase architecture, showing the function structure and call relationships.

**🚨 USE AT YOUR OWN RISK - ALL DATA WILL BE IRREVERSIBLY DESTROYED! 🚨**

### Function Call Graph

```mermaid
graph TD
    %% Entry Point
    main["main()<br/>Entry point - CLI argument parsing"]

    %% Device Information Functions
    get_device_info["get_device_info(device)<br/>Display device information"]
    list_all_devices["list_all_devices()<br/>List all available devices"]
    get_block_device_size["get_block_device_size(device)<br/>Get device size in bytes"]

    %% Disk Type Detection
    detect_disk_type["detect_disk_type(device, debug=False)<br/>Detect HDD/SSD/NVMe/eMMC"]
    perform_hdd_pretest["perform_hdd_pretest(device, chunk_size)<br/>Test HDD write speeds at different positions"]

    %% Progress Management
    get_progress_file["get_progress_file(device)<br/>Get progress file path"]
    save_progress["save_progress(device, written, total_size, chunk_size, pretest_results)<br/>Save wipe progress to file"]
    load_progress["load_progress(device)<br/>Load saved progress from file"]
    clear_progress["clear_progress(device)<br/>Clear progress file"]
    find_resume_files["find_resume_files()<br/>Find all progress files"]
    display_resume_info["display_resume_info()<br/>Display available resume options"]

    %% Core Wiping Function
    wipe_device["wipe_device(device, chunk_size, resume, skip_pretest)<br/>Main wiping function"]

    %% Utility Functions
    parse_size["parse_size(size_str)<br/>Parse size strings (e.g., '100M', '1G')"]

    %% Main function calls
    main --> display_resume_info
    main --> list_all_devices
    main --> parse_size
    main --> get_device_info
    main --> load_progress
    main --> clear_progress
    main --> wipe_device

    %% get_device_info calls
    get_device_info --> get_block_device_size
    get_device_info --> detect_disk_type

    %% wipe_device calls
    wipe_device --> get_block_device_size
    wipe_device --> detect_disk_type
    wipe_device --> load_progress
    wipe_device --> perform_hdd_pretest
    wipe_device --> save_progress

    %% Progress management calls
    save_progress --> get_progress_file
    load_progress --> get_progress_file
    clear_progress --> get_progress_file
    display_resume_info --> find_resume_files
    find_resume_files --> get_progress_file

    %% Styling
    classDef entryPoint fill:#e1f5fe,stroke:#01579b,stroke-width:3px
    classDef coreFunction fill:#f3e5f5,stroke:#4a148c,stroke-width:2px
    classDef utilityFunction fill:#e8f5e8,stroke:#1b5e20,stroke-width:2px
    classDef progressFunction fill:#fff3e0,stroke:#e65100,stroke-width:2px

    class main entryPoint
    class wipe_device,get_device_info,detect_disk_type,perform_hdd_pretest coreFunction
    class parse_size,get_block_device_size utilityFunction
    class save_progress,load_progress,clear_progress,get_progress_file,find_resume_files,display_resume_info progressFunction
```

### Function Categories

#### **Entry Point**
- `main()` - CLI argument parsing and orchestration

#### **Core Functions**
- `wipe_device()` - Main wiping logic with disk type detection and algorithm selection
- `get_device_info()` - Display comprehensive device information
- `detect_disk_type()` - Identify storage device type (HDD/SSD/NVMe/eMMC)
- `perform_hdd_pretest()` - Test HDD write speeds to optimize algorithm selection

#### **Progress Management**
- `save_progress()` - Save wipe progress and pretest results
- `load_progress()` - Load saved progress for resume operations
- `clear_progress()` - Remove progress files
- `get_progress_file()` - Generate progress file paths
- `find_resume_files()` - Discover available resume files
- `display_resume_info()` - Show resume options to user

#### **Utility Functions**
- `parse_size()` - Convert size strings to bytes
- `get_block_device_size()` - Get device size using system calls
- `list_all_devices()` - List available block devices

### Key Design Patterns

1. **Progressive Enhancement**: The system starts with basic wiping and adds intelligent features (disk detection, pretesting) for optimal performance.

2. **Resume Capability**: Progress is saved at regular intervals, allowing interrupted wipes to be resumed.

3. **Adaptive Algorithms**: HDD pretesting enables selection of optimal wiping strategies based on actual device performance.

4. **Separation of Concerns**: Device information, progress management, and core wiping logic are cleanly separated into distinct function groups.
