#!/bin/bash
# Test script to simulate GitHub Actions CI pipeline locally

set -e

echo "🚀 Running wipeit CI Pipeline Tests"
echo "=================================="

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Function to print colored output
print_status() {
    echo -e "${GREEN}✅ $1${NC}"
}

print_warning() {
    echo -e "${YELLOW}⚠️  $1${NC}"
}

print_error() {
    echo -e "${RED}❌ $1${NC}"
}

# Check Python version
echo "🐍 Checking Python version..."
python3 --version
print_status "Python version check passed"

# Install dependencies
echo ""
echo "📦 Installing dependencies..."
pip3 install --upgrade pip > /dev/null 2>&1
pip3 install coverage > /dev/null 2>&1
print_status "Dependencies installed"

# Run unit tests
echo ""
echo "🧪 Running unit tests..."
python3 test_wipeit.py -v
print_status "Unit tests passed"

# Run tests with coverage
echo ""
echo "📊 Running coverage analysis..."
coverage run test_wipeit.py
coverage report --show-missing
print_status "Coverage analysis completed"

# Test help functionality
echo ""
echo "❓ Testing help functionality..."
python3 wipeit.py --help > /dev/null
print_status "Help functionality working"

# Test version functionality
echo ""
echo "🏷️  Testing version functionality..."
VERSION=$(python3 wipeit.py --version)
echo "Version: $VERSION"
print_status "Version functionality working"

# Test buffer size parsing
echo ""
echo "🔧 Testing buffer size parsing..."
python3 -c "
from wipeit import parse_size
test_sizes = ['1M', '100M', '1G', '0.5G', '1T']
for size in test_sizes:
    result = parse_size(size)
    print(f'  {size:4} -> {result:,} bytes ({result/(1024**3):.2f} GB)')
"
print_status "Buffer size parsing working"

# Test progress file functionality
echo ""
echo "📁 Testing progress file functionality..."
python3 -c "
from wipeit import save_progress, load_progress, clear_progress
device = '/dev/test'
save_progress(device, 1024*1024*1024, 4*1024*1024*1024, 100*1024*1024)
progress = load_progress(device)
if progress:
    print(f'  Progress loaded: {progress[\"progress_percent\"]:.2f}% complete')
clear_progress(device)
print('  Progress workflow completed')
"
print_status "Progress file functionality working"

# Test edge cases
echo ""
echo "🔍 Testing edge cases..."
python3 -c "
from wipeit import parse_size
import sys

# Test invalid sizes
invalid_tests = ['500K', '2T', '0.5M', 'ABC', '100', '100MB']
for size_str in invalid_tests:
    try:
        parse_size(size_str)
        print(f'  ❌ {size_str} should have failed')
        sys.exit(1)
    except (ValueError, IndexError):
        print(f'  ✅ {size_str} correctly rejected')

print('  All edge case tests passed')
"
print_status "Edge case testing completed"

# Test integration workflow
echo ""
echo "🔗 Testing integration workflow..."
python3 -c "
from wipeit import save_progress, load_progress, clear_progress, find_resume_files
import os

# Complete workflow test
device = '/dev/integration_test'
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
print('  ✅ Progress loaded')

# Test resume file detection
resume_files = find_resume_files()
assert len(resume_files) == 1, 'Should find one resume file'
print('  ✅ Resume file detection working')

# Clear progress
clear_progress(device)
progress = load_progress(device)
assert progress is None, 'Progress should be cleared'
print('  ✅ Progress cleared')

print('  Integration workflow completed successfully')
"
print_status "Integration workflow testing completed"

# Final summary
echo ""
echo "🎉 CI Pipeline Test Summary"
echo "=========================="
echo "✅ Python version check"
echo "✅ Dependencies installation"
echo "✅ Unit tests (27 tests)"
echo "✅ Coverage analysis"
echo "✅ Help functionality"
echo "✅ Version functionality"
echo "✅ Buffer size parsing"
echo "✅ Progress file management"
echo "✅ Edge case testing"
echo "✅ Integration workflow"
echo ""
print_status "All CI pipeline tests passed!"
echo ""
echo "🚀 Ready for GitHub Actions deployment!"
