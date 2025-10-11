#!/usr/bin/env python3
import json
import time
import sys
sys.path.insert(0, 'src')
import wipeit

# Create a test progress file
test_data = {
    'device': '/dev/sdb',
    'written': 500 * 1024 * 1024 * 1024,  # 500GB
    'total_size': 1000 * 1024 * 1024 * 1024,  # 1TB
    'chunk_size': 100 * 1024 * 1024,
    'timestamp': time.time(),
    'progress_percent': 50.0
}

with open('wipeit_progress.json', 'w') as f:
    json.dump(test_data, f)

print("Created test progress file")
print("\n--- Testing display_resume_info() ---")
result = wipeit.display_resume_info()
print(f"\nFunction returned: {result}")

# Cleanup
import os
os.remove('wipeit_progress.json')
print("\nCleaned up test file")
