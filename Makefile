# Makefile for wipeit - Secure device wiping utility
#
# This Makefile provides targets for building, testing, and maintaining
# the wipeit project according to the programming style guide.

.PHONY: info tests lint pre-git-prep security reports build help

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
	@echo "  reports        - Generate comprehensive codebase statistics and reports"
	@echo "                   - Code coverage analysis with detailed metrics"
	@echo "                   - Security analysis (bandit + safety)"
	@echo "                   - Code metrics (lines of code, files, complexity)"
	@echo "                   - Import analysis and dependency information"
	@echo "                   - Performance and quality metrics"
	@echo ""
	@echo "  clean_files    - Clean invisible characters from all relevant files"
	@echo "                   - Removes problematic invisible characters from code/docs"
	@echo "                   - Processes Python, Markdown, YAML, JSON, and other text files"
	@echo "                   - Creates backup files (.bak) for safety"
	@echo "                   - Use to clean AI-generated content artifacts"
	@echo ""
	@echo "  build          - Build distribution packages (wheel and source tarball)"
	@echo "                   - Cleans previous builds in dist/ directory"
	@echo "                   - Creates wheel (.whl) for pip installation"
	@echo "                   - Creates source distribution (.tar.gz)"
	@echo "                   - Displays created packages with sizes"
	@echo ""
	@echo "Usage examples:"
	@echo "  make           # Show this help"
	@echo "  make info      # Show this help"
	@echo "  make tests     # Run all tests and style checks"
	@echo "  make lint      # Run only style checks"
	@echo "  make security  # Run security scans"
	@echo "  make reports   # Generate comprehensive codebase reports"
	@echo "  make clean_files  # Clean invisible characters from files"
	@echo "  make pre-git-prep  # Fix code style before committing"
	@echo "  make build     # Build distribution packages for pip installation"

# Run comprehensive test suite including flake8 style checks
tests:
	@echo "Running comprehensive test suite..."
	@echo ""
	@echo "=== Running Unit Tests with Coverage ==="
	@cd src && python3 -m coverage run -m unittest discover -s . -p "test_*.py"
	@cd src && python3 -m coverage report --show-missing
	@echo ""
	@echo "=== Running Import Sorting Check (isort) ==="
	@echo "Checking import order..."
	@python3 -m isort --check-only --diff src/wipeit.py src/device_detector.py src/test_wipeit.py src/test_device_detector.py
	@echo ""
	@echo "=== Running Style Checks (flake8) ==="
	@echo "Checking src/wipeit.py..."
	@python3 -m flake8 src/wipeit.py --max-line-length=79 --count
	@echo "Checking src/device_detector.py..."
	@python3 -m flake8 src/device_detector.py --max-line-length=79 --count
	@echo "Checking src/test_wipeit.py..."
	@python3 -m flake8 src/test_wipeit.py --max-line-length=79 --count
	@echo "Checking src/test_device_detector.py..."
	@python3 -m flake8 src/test_device_detector.py --max-line-length=79 --count
	@echo "Checking src/test_device_detector.py..."
	@python3 -m flake8 src/test_device_detector.py --max-line-length=79 --count
	@echo ""
	@echo "=== Test Summary ==="
	@echo "All tests completed successfully!"
	@echo "Import sorting checks passed."
	@echo "Style checks passed - no line length violations found."
	@echo ""
	@echo "Test suite passed - code is ready for production"

# Run only flake8 style checks
lint:
	@echo "Running flake8 style checks..."
	@echo ""
	@echo "=== Checking src/wipeit.py ==="
	@python3 -m flake8 src/wipeit.py --max-line-length=79 --count
	@echo "=== Checking src/device_detector.py ==="
	@python3 -m flake8 src/device_detector.py --max-line-length=79 --count
	@echo "=== Checking src/test_wipeit.py ==="
	@python3 -m flake8 src/test_wipeit.py --max-line-length=79 --count
	@echo "=== Checking src/test_device_detector.py ==="
	@python3 -m flake8 src/test_device_detector.py --max-line-length=79 --count
	@echo ""
	@echo "Style checks passed - no line length violations found"

# Prepare code for git commit by fixing style issues
pre-git-prep:
	@echo "Preparing code for git commit..."
	@echo ""
	@echo "=== Running autopep8 to fix line length issues ==="
	@echo "Fixing src/wipeit.py..."
	@python3 -m autopep8 --max-line-length=79 --in-place src/wipeit.py
	@echo "Fixing src/device_detector.py..."
	@python3 -m autopep8 --max-line-length=79 --in-place src/device_detector.py
	@echo "Fixing src/test_wipeit.py..."
	@python3 -m autopep8 --max-line-length=79 --in-place src/test_wipeit.py
	@echo "Fixing src/test_device_detector.py..."
	@python3 -m autopep8 --max-line-length=79 --in-place src/test_device_detector.py
	@echo ""
	@echo "=== Verifying fixes with flake8 ==="
	@echo "Checking src/wipeit.py..."
	@python3 -m flake8 src/wipeit.py --max-line-length=79 --count
	@echo "Checking src/device_detector.py..."
	@python3 -m flake8 src/device_detector.py --max-line-length=79 --count
	@echo "Checking src/test_wipeit.py..."
	@python3 -m flake8 src/test_wipeit.py --max-line-length=79 --count
	@echo "Checking src/test_device_detector.py..."
	@python3 -m flake8 src/test_device_detector.py --max-line-length=79 --count
	@echo ""
	@echo "Code prepared for git commit - all style issues fixed"
	@echo "Note: This target may include additional pre-commit tasks in the future"

# Run security scans with bandit and safety
security:
	@echo "Running security scans..."
	@echo ""
	@echo "=== Running Bandit Security Scan ==="
	@echo "Scanning for high/medium severity security issues..."
	@python3 -m bandit -r src/ --ini .bandit -f txt -ll || echo "⚠️  Bandit found issues (see output above)"
	@echo ""
	@echo "=== Running Safety Dependency Check ==="
	@echo "Checking for known security vulnerabilities in dependencies..."
	@python3 -m safety scan || echo "⚠️  Safety found issues (see output above)"
	@echo ""
	@echo "Security scans completed"
	@echo "Note: Low severity issues in system tools are expected"

# Clean invisible characters from all relevant files
clean_files:
	@echo "Cleaning invisible characters from files..."
	@echo ""
	@echo "=== Running Invisible Character Cleaner ==="
	@echo "Processing Python, Markdown, YAML, and other text files..."
	@python3 scripts/clean_invisible_chars.py . --clean --extensions py md yml yaml txt json toml cfg ini sh bash
	@echo ""
	@echo "Invisible character cleaning completed"
	@echo "Note: Backup files (.bak) created for safety"

# Generate comprehensive codebase statistics and reports
reports:
	@echo "Generating comprehensive codebase reports..."
	@echo ""
	@echo "=========================================="
	@echo "CODEBASE STATISTICS REPORT"
	@echo "=========================================="
	@echo ""
	@echo "=== FILE STRUCTURE ANALYSIS ==="
	@echo "Total files in project:"
	@find . -type f -not -path "./.git/*" -not -path "./__pycache__/*" -not -path "./.pytest_cache/*" -not -path "./.venv/*" -not -path "./venv/*" | wc -l
	@echo ""
	@echo "Python source files:"
	@find . -name "*.py" -not -path "./.git/*" -not -path "./__pycache__/*" -not -path "./.venv/*" -not -path "./venv/*" | wc -l
	@echo ""
	@echo "Documentation files:"
	@find . -name "*.md" -not -path "./.git/*" -not -path "./.venv/*" -not -path "./venv/*" | wc -l
	@echo ""
	@echo "Configuration files:"
	@find . -name "*.toml" -o -name "*.json" -o -name "*.yaml" -o -name "*.yml" -o -name "Makefile" -not -path "./.git/*" -not -path "./.venv/*" -not -path "./venv/*" | wc -l
	@echo ""
	@echo "=== 📏 CODE METRICS ==="
	@echo "Total lines of code (Python):"
	@find . -name "*.py" -not -path "./.git/*" -not -path "./__pycache__/*" -not -path "./.venv/*" -not -path "./venv/*" -exec wc -l {} + | tail -1
	@echo ""
	@echo "Lines of code by file:"
	@find . -name "*.py" -not -path "./.git/*" -not -path "./__pycache__/*" -not -path "./.venv/*" -not -path "./venv/*" -exec wc -l {} + | sort -nr
	@echo ""
	@echo "Total lines of documentation:"
	@find . -name "*.md" -not -path "./.git/*" -not -path "./.venv/*" -not -path "./venv/*" -exec wc -l {} + | tail -1
	@echo ""
	@echo "=== CODE COVERAGE ANALYSIS ==="
	@echo "Running tests with coverage..."
	@cd src && python3 -m coverage run -m unittest discover -s . -p "test_*.py" > /dev/null 2>&1
	@cd src && python3 -m coverage report --show-missing
	@echo ""
	@echo "Coverage summary:"
	@cd src && python3 -m coverage report --show-missing | tail -1
	@echo ""
	@echo "=== SECURITY ANALYSIS ==="
	@echo "Running Bandit security scan..."
	@python3 -m bandit -r src/ --ini .bandit -f txt -ll 2>/dev/null || echo "⚠️  Bandit scan completed (see output above for any issues)"
	@echo ""
	@echo "Running Safety dependency check..."
	@python3 -m safety scan 2>/dev/null || echo "⚠️  Safety scan completed (see output above for any issues)"
	@echo ""
	@echo "=== DEPENDENCY ANALYSIS ==="
	@echo "Runtime dependencies:"
	@if [ -f "pyproject.toml" ]; then \
		echo "Main project dependencies:"; \
		if awk '/^dependencies = \[/,/^\]/ {if (/^dependencies = \[/) next; if (/^\]/) exit; if (/^\s*"[a-zA-Z]/) print}' pyproject.toml > /dev/null 2>&1; then \
			awk '/^dependencies = \[/,/^\]/ {if (/^dependencies = \[/) next; if (/^\]/) exit; if (/^\s*"[a-zA-Z]/) print}' pyproject.toml | sed 's/^[[:space:]]*//' | sed 's/,$$//'; \
		else \
			echo "  (No runtime dependencies - uses Python standard library only)"; \
		fi; \
		echo ""; \
		echo "Development dependencies:"; \
		if awk '/^dev-dependencies = \[/,/^\]/ {if (/^dev-dependencies = \[/) next; if (/^\]/) exit; if (/^\s*"[a-zA-Z]/) print}' pyproject.toml > /dev/null 2>&1; then \
			awk '/^dev-dependencies = \[/,/^\]/ {if (/^dev-dependencies = \[/) next; if (/^\]/) exit; if (/^\s*"[a-zA-Z]/) print}' pyproject.toml | sed 's/^[[:space:]]*//' | sed 's/,$$//' | sed 's/^/  /'; \
		else \
			echo "  (No development dependencies found)"; \
		fi; \
		echo ""; \
		echo "Build system dependencies:"; \
		if grep "^requires = \[" pyproject.toml | grep -E '"[a-zA-Z]' > /dev/null; then \
			grep "^requires = \[" pyproject.toml | sed 's/.*\[//' | sed 's/\].*//' | sed 's/"//g' | sed 's/^/  /'; \
		else \
			echo "  (No build system dependencies found)"; \
		fi; \
	else \
		echo "No pyproject.toml found"; \
	fi
	@echo ""
	@echo "=== CODE QUALITY METRICS ==="
	@echo "Running style checks..."
	@echo "Flake8 violations:"
	@python3 -m flake8 src/ --max-line-length=79 --count --statistics 2>/dev/null || echo "Style check completed"
	@echo ""
	@echo "Import sorting status:"
	@python3 -m isort --check-only --diff src/wipeit.py src/device_detector.py src/test_wipeit.py src/test_device_detector.py 2>/dev/null && echo "Imports are properly sorted" || echo "⚠️  Import sorting issues found"
	@echo ""
	@echo "=== PROJECT STRUCTURE ==="
	@echo "Main source files:"
	@ls -la src/*.py 2>/dev/null | awk '{print $$9, $$5}' | column -t
	@echo ""
	@echo "Test files:"
	@ls -la src/test_*.py 2>/dev/null | awk '{print $$9, $$5}' | column -t
	@echo ""
	@echo "Documentation files:"
	@ls -la DOCS/*.md 2>/dev/null | awk '{print $$9, $$5}' | column -t
	@echo ""
	@echo "=== COMPLEXITY ANALYSIS ==="
	@echo "Function and class counts:"
	@echo "Classes:"
	@total_class_count=$$(grep -r "^class " src/ --include="*.py" | wc -l); \
	echo "  Total: $$total_class_count"; \
	test_class_count=$$(grep -r "^class Test" src/ --include="*.py" | wc -l); \
	codebase_class_count=$$(grep -r "^class " src/ --include="*.py" | grep -v ":class Test" | wc -l); \
	echo "  Codebase classes: $$codebase_class_count"; \
	if [ $$codebase_class_count -gt 0 ]; then \
		echo "  Codebase class names:"; \
		grep -r "^class " src/ --include="*.py" | grep -v ":class Test" | sed 's/^[^:]*:class /    /' | sed 's/(.*//' | sed 's/:.*//'; \
	fi; \
	echo "  Test classes: $$test_class_count"; \
	if [ $$test_class_count -gt 0 ]; then \
		echo "  Test class names:"; \
		grep -r "^class Test" src/ --include="*.py" | sed 's/^[^:]*:class /    /' | sed 's/(.*//' | sed 's/:.*//'; \
	fi
	@echo ""
	@echo "Functions:"
	@total_func_count=$$(grep -r "^def " src/ --include="*.py" | wc -l); \
	echo "  Total: $$total_func_count"; \
	codebase_func_count=$$(grep -r "^def " src/ --include="*.py" | grep -v ":def test_" | wc -l); \
	test_func_count=$$(grep -r "def test_" src/ --include="*.py" | wc -l); \
	echo "  Codebase functions: $$codebase_func_count"; \
	if [ $$codebase_func_count -gt 0 ]; then \
		echo "  Codebase function names:"; \
		grep -r "^def " src/ --include="*.py" | grep -v ":def test_" | sed 's/^[^:]*:def /    /' | sed 's/(.*//' | sed 's/:.*//'; \
	fi; \
	echo "  Test functions: $$test_func_count"; \
	if [ $$test_func_count -gt 0 ]; then \
		echo "  Test function names (first 10):"; \
		grep -r "def test_" src/ --include="*.py" | sed 's/^[^:]*:.*def /    /' | sed 's/(.*//' | sed 's/:.*//' | head -10; \
		if [ $$test_func_count -gt 10 ]; then \
			echo "    ... and $$((test_func_count - 10)) more"; \
		fi; \
	fi
	@echo ""
	@echo "=== CODE STYLE SUMMARY ==="
	@echo "Longest lines (>79 chars):"
	@find src/ -name "*.py" -not -path "./.venv/*" -not -path "./venv/*" -exec awk 'length($$0) > 79 {print FILENAME ":" NR ": " $$0}' {} \; | head -5
	@echo ""
	@echo "=== REPORT SUMMARY ==="
	@echo "Codebase analysis completed"
	@echo "Reports generated for:"
	@echo "   - File structure and metrics"
	@echo "   - Code coverage analysis"
	@echo "   - Security assessment"
	@echo "   - Dependency analysis"
	@echo "   - Code quality metrics"
	@echo "   - Project structure overview"
	@echo ""
	@echo "Use 'make tests' for detailed test results"
	@echo "Use 'make security' for focused security analysis"
	@echo "Use 'make lint' for detailed style analysis"

# Build distribution packages (wheel and source tarball)
build:
	@echo "Building distribution packages..."
	@echo ""
	@echo "=== Cleaning Previous Builds ==="
	@rm -rf dist/ build/ src/*.egg-info
	@echo "Removed old build artifacts"
	@echo ""
	@echo "=== Building Wheel and Source Distribution ==="
	@python3 -m build
	@echo ""
	@echo "=== Build Complete ==="
	@echo "Created packages in dist/:"
	@ls -lh dist/ | tail -n +2 | awk '{printf "  %-40s %10s\n", $$9, $$5}'
	@echo ""
	@echo "Distribution packages built successfully!"
	@echo ""
	@echo "To install locally:"
	@echo "  pip install dist/wipeit-$$(grep '^version' pyproject.toml | cut -d'"' -f2)-py3-none-any.whl"
	@echo ""
	@echo "To upload to PyPI (requires credentials):"
	@echo "  python3 -m twine upload dist/*"
