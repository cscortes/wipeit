# Makefile for wipeit - Secure device wiping utility
#
# This Makefile provides targets for building, testing, and maintaining
# the wipeit project according to the programming style guide.

.PHONY: info tests lint pre-git-prep security help

# Default target - show help information
info: help

# Show help information with target descriptions
help:
	@echo "wipeit Makefile - Available targets:"
	@echo ""
	@echo "  info (default)  - Display this help information with target descriptions"
	@echo "                   Shows all available make targets and their purposes"
	@echo ""
	@echo "  tests          - Run comprehensive test suite including:"
	@echo "                   - All unit tests (python3 -m unittest)"
	@echo "                   - Code style checks (flake8 with 79-char line limit)"
	@echo "                   - Ensures no line length violations to pass"
	@echo "                   - Validates programming style guide compliance"
	@echo ""
	@echo "  lint           - Run only flake8 style checks with 79-character line limit"
	@echo "                   - Quick way to check code style without running tests"
	@echo "                   - Fails if any line length violations are found"
	@echo ""
	@echo "  pre-git-prep   - Prepare code for git commit by fixing style issues"
	@echo "                   - Runs autopep8 to fix line length and formatting issues"
	@echo "                   - Future: may include additional pre-commit tasks"
	@echo "                   - Use before committing to ensure clean code"
	@echo ""
	@echo "  security       - Run security scans with bandit and safety"
	@echo "                   - Bandit: Scans for common security issues in code"
	@echo "                   - Safety: Checks for known vulnerabilities in dependencies"
	@echo "                   - Ensures code security best practices"
	@echo ""
	@echo "Usage examples:"
	@echo "  make           # Show this help"
	@echo "  make info      # Show this help"
	@echo "  make tests     # Run all tests and style checks"
	@echo "  make lint      # Run only style checks"
	@echo "  make security  # Run security scans"
	@echo "  make pre-git-prep  # Fix code style before committing"

# Run comprehensive test suite including flake8 style checks
tests:
	@echo "Running comprehensive test suite..."
	@echo ""
	@echo "=== Running Unit Tests with Coverage ==="
	@python3 -m coverage run test_wipeit.py
	@python3 -m coverage report --show-missing
	@echo ""
	@echo "=== Running Import Sorting Check (isort) ==="
	@echo "Checking import order..."
	@python3 -m isort --check-only --diff wipeit.py test_wipeit.py
	@echo ""
	@echo "=== Running Style Checks (flake8) ==="
	@echo "Checking wipeit.py..."
	@python3 -m flake8 wipeit.py --max-line-length=79 --count
	@echo "Checking test_wipeit.py..."
	@python3 -m flake8 test_wipeit.py --max-line-length=79 --count
	@echo ""
	@echo "=== Test Summary ==="
	@echo "All tests completed successfully!"
	@echo "Import sorting checks passed."
	@echo "Style checks passed - no line length violations found."
	@echo ""
	@echo "✅ Test suite passed - code is ready for production"

# Run only flake8 style checks
lint:
	@echo "Running flake8 style checks..."
	@echo ""
	@echo "=== Checking wipeit.py ==="
	@python3 -m flake8 wipeit.py --max-line-length=79 --count
	@echo "=== Checking test_wipeit.py ==="
	@python3 -m flake8 test_wipeit.py --max-line-length=79 --count
	@echo ""
	@echo "✅ Style checks passed - no line length violations found"

# Prepare code for git commit by fixing style issues
pre-git-prep:
	@echo "Preparing code for git commit..."
	@echo ""
	@echo "=== Running autopep8 to fix line length issues ==="
	@echo "Fixing wipeit.py..."
	@python3 -m autopep8 --max-line-length=79 --in-place wipeit.py
	@echo "Fixing test_wipeit.py..."
	@python3 -m autopep8 --max-line-length=79 --in-place test_wipeit.py
	@echo ""
	@echo "=== Verifying fixes with flake8 ==="
	@echo "Checking wipeit.py..."
	@python3 -m flake8 wipeit.py --max-line-length=79 --count
	@echo "Checking test_wipeit.py..."
	@python3 -m flake8 test_wipeit.py --max-line-length=79 --count
	@echo ""
	@echo "✅ Code prepared for git commit - all style issues fixed"
	@echo "💡 Future: This target may include additional pre-commit tasks"

# Run security scans with bandit and safety
security:
	@echo "Running security scans..."
	@echo ""
	@echo "=== Running Bandit Security Scan ==="
	@echo "Scanning for high/medium severity security issues..."
	@python3 -m bandit -r . -c bandit.yaml -f txt -ll || echo "⚠️  Bandit found issues (see output above)"
	@echo ""
	@echo "=== Running Safety Dependency Check ==="
	@echo "Checking for known security vulnerabilities in dependencies..."
	@python3 -m safety scan || echo "⚠️  Safety found issues (see output above)"
	@echo ""
	@echo "✅ Security scans completed"
	@echo "💡 Note: Low severity issues in system tools are expected"
