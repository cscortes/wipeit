#!/bin/bash
# Test script to validate GitHub Actions workflow tests locally
# Run this before pushing to catch workflow failures early

set -e  # Exit on any error

echo "🚀 Testing GitHub Actions Workflows Locally"
echo "==========================================="
echo ""

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

print_success() {
    echo -e "${GREEN}✅ $1${NC}"
}

print_error() {
    echo -e "${RED}❌ $1${NC}"
}

print_info() {
    echo -e "${YELLOW}ℹ️  $1${NC}"
}

# Track failures
FAILED=0

# Test 1: Help functionality
echo "📝 Test 1: Help functionality"
if python src/wipeit.py --help > /dev/null 2>&1; then
    print_success "Help functionality working"
else
    print_error "Help functionality failed"
    FAILED=1
fi
echo ""

# Test 2: Version functionality
echo "📝 Test 2: Version functionality"
if python src/wipeit.py --version > /dev/null 2>&1; then
    print_success "Version functionality working"
else
    print_error "Version functionality failed"
    FAILED=1
fi
echo ""

# Test 3: Buffer size parsing
echo "📝 Test 3: Buffer size parsing"
cd src
python -c "
from wipeit import parse_size
test_sizes = ['1M', '100M', '1G', '0.5G', '1T']
for size in test_sizes:
    result = parse_size(size)
    print(f'  {size} -> {result:,} bytes')
" 2>&1
if [ $? -eq 0 ]; then
    print_success "Buffer size parsing working"
else
    print_error "Buffer size parsing failed"
    FAILED=1
fi
cd ..
echo ""

# Test 4: Buffer size parsing edge cases
echo "📝 Test 4: Buffer size parsing edge cases"
cd src
python -c "
from wipeit import parse_size
import sys

# Test valid sizes
valid_tests = [
    ('1M', 1024*1024),
    ('100M', 100*1024*1024),
    ('1G', 1024*1024*1024),
    ('0.5G', int(0.5*1024*1024*1024)),
    ('1T', 1024*1024*1024*1024)
]

for size_str, expected in valid_tests:
    result = parse_size(size_str)
    assert result == expected, f'Failed: {size_str} -> {result} != {expected}'
    print(f'  ✅ {size_str} -> {result:,} bytes')

# Test invalid sizes
invalid_tests = ['500K', '2T', '0.5M', 'ABC', '100', '100MB']
for size_str in invalid_tests:
    try:
        parse_size(size_str)
        print(f'  ❌ {size_str} should have failed')
        sys.exit(1)
    except (ValueError, IndexError):
        print(f'  ✅ {size_str} correctly rejected')

print('All buffer size tests passed!')
" 2>&1
TEST_RESULT=$?
cd ..
if [ $TEST_RESULT -eq 0 ]; then
    print_success "Buffer size edge cases working"
else
    print_error "Buffer size edge cases failed"
    FAILED=1
fi
echo ""

# Test 5: Progress file functionality (ci.yml)
echo "📝 Test 5: Progress file functionality (ci.yml)"
cd src
python -c "
from wipeit import save_progress, load_progress, clear_progress
device = '/dev/test'
save_progress(device, 1024*1024*1024, 4*1024*1024*1024, 100*1024*1024)
progress = load_progress(device)
if progress:
    print(f'  Progress loaded: {progress[\"progress_percent\"]:.2f}% complete')
clear_progress()
print('  Progress workflow test completed')
" 2>&1
if [ $? -eq 0 ]; then
    print_success "Progress file functionality (ci.yml) working"
else
    print_error "Progress file functionality (ci.yml) failed"
    FAILED=1
fi
cd ..
echo ""

# Test 6: Progress file workflow (status.yml)
echo "📝 Test 6: Progress file workflow (status.yml)"
cd src
python -c "
from wipeit import save_progress, load_progress, clear_progress, find_resume_file, display_resume_info
import os

# Test complete workflow
device = '/dev/test'
written = 1024 * 1024 * 1024
total_size = 4 * 1024 * 1024 * 1024
chunk_size = 100 * 1024 * 1024

# Save progress
save_progress(device, written, total_size, chunk_size)
print('  ✅ Progress saved')

# Load progress
progress = load_progress(device)
assert progress is not None, 'Progress should be loadable'
assert progress['device'] == device, 'Device should match'
assert progress['written'] == written, 'Written bytes should match'
print('  ✅ Progress loaded')

# Test resume file detection
resume_file = find_resume_file()
assert resume_file is not None, 'Should find one resume file'
print('  ✅ Resume file detection working')

# Test display (capture output)
import io
import sys
old_stdout = sys.stdout
sys.stdout = io.StringIO()
display_resume_info()
output = sys.stdout.getvalue()
sys.stdout = old_stdout
assert 'Found previous wipe session' in output, 'Should display resume info'
print('  ✅ Resume info display working')

# Clear progress
clear_progress()
progress = load_progress(device)
assert progress is None, 'Progress should be cleared'
print('  ✅ Progress cleared')

print('All progress file tests passed!')
" 2>&1
TEST_RESULT=$?
cd ..
if [ $TEST_RESULT -eq 0 ]; then
    print_success "Progress file workflow (status.yml) working"
else
    print_error "Progress file workflow (status.yml) failed"
    FAILED=1
fi
echo ""

# Summary
echo "==========================================="
if [ $FAILED -eq 0 ]; then
    print_success "All GitHub Actions workflow tests passed!"
    echo ""
    echo "✅ Safe to push to GitHub"
    exit 0
else
    print_error "Some GitHub Actions workflow tests failed!"
    echo ""
    echo "❌ Fix issues before pushing to GitHub"
    exit 1
fi

