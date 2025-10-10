# Continuous Integration and Deployment (CI/CD)

**⚠️ WARNING: This tool is EXTREMELY DESTRUCTIVE and will PERMANENTLY DESTROY data! ⚠️**

This document describes the CI/CD pipeline for the wipeit project using GitHub Actions.

**🚨 USE AT YOUR OWN RISK - ALL DATA WILL BE IRREVERSIBLY DESTROYED! 🚨**

## Overview

The wipeit project uses GitHub Actions for:
- **Continuous Integration**: Automated testing on every push and pull request
- **Code Quality**: Linting and security checks
- **Release Management**: Automated package building and publishing
- **Status Monitoring**: Weekly health checks and reporting

## Workflows

### 1. CI Pipeline (`ci.yml`)

**Trigger**: Push to main/master, Pull requests
**Purpose**: Fast feedback on code changes

**Features**:
- Tests on Python 3.8, 3.11, 3.12
- Unit test execution
- Coverage reporting
- Command-line interface testing
- Buffer size parsing validation
- Progress file functionality testing

**Duration**: ~2-3 minutes

### 2. Comprehensive Tests (`tests.yml`)

**Trigger**: Push to main/master/develop, Pull requests
**Purpose**: Thorough testing and quality assurance

**Features**:
- Tests on Python 3.8, 3.9, 3.10, 3.11, 3.12
- Unit tests with coverage
- Import sorting checks (isort)
- Linting (flake8)
- Security scanning (bandit, safety)
- Package building and validation

**Duration**: ~5-7 minutes

### 3. Release Pipeline (`release.yml`)

**Trigger**: Git tags (v*)
**Purpose**: Automated package publishing

**Features**:
- Pre-release testing
- Package building
- PyPI publishing
- GitHub release creation
- Changelog integration

**Duration**: ~3-5 minutes

### 4. Status Monitoring (`status.yml`)

**Trigger**: Weekly schedule, Manual dispatch
**Purpose**: Health monitoring and reporting

**Features**:
- Comprehensive test suite
- Coverage analysis
- Edge case testing
- Integration workflow validation
- Test report generation

**Duration**: ~4-6 minutes

## Test Coverage

### Unit Tests (27 tests)
- **TestParseSize**: Buffer size parsing (5 tests)
- **TestProgressFileFunctions**: Progress file management (8 tests)
- **TestResumeFileFunctions**: Resume file detection (5 tests)
- **TestDeviceInfoFunctions**: Device information (2 tests)
- **TestMainFunction**: Command-line interface (5 tests)
- **TestIntegration**: End-to-end workflows (2 tests)

### Coverage Metrics
- **Current Coverage**: 82% overall
- **Test File Coverage**: 98%
- **Main Code Coverage**: 64%

### Test Execution
```bash
# Run all tests
python3 test_wipeit.py

# Run with verbose output
python3 test_wipeit.py -v

# Run with coverage
coverage run test_wipeit.py
coverage report
```

## Quality Gates

### Required Checks
- [ ] All unit tests pass
- [ ] Coverage above 80%
- [ ] No linting errors
- [ ] No security vulnerabilities
- [ ] Import sorting compliance

### Optional Checks
- [ ] Performance benchmarks
- [ ] Integration tests
- [ ] Documentation updates

## Local Testing

### Pre-commit Testing
```bash
# Run the CI simulation script
./test-ci.sh

# Run specific test categories
python3 test_wipeit.py TestParseSize -v
python3 test_wipeit.py TestProgressFileFunctions -v
```

### Code Formatting (Local Only)
```bash
# Fix line length issues before committing
make pre-git-prep

# Run linting checks
make lint

# Run security scans
make security
```

### Manual Testing
```bash
# Test help functionality
python3 wipeit.py --help

# Test version
python3 wipeit.py --version

# Test buffer size parsing
python3 -c "from wipeit import parse_size; print(parse_size('1G'))"
```

## Security

### Automated Security Checks
- **Bandit**: Python security linting
- **Safety**: Dependency vulnerability scanning
- **CodeQL**: Static analysis (if enabled)

### Security Best Practices
- No hardcoded credentials
- Input validation
- Error handling
- Root privilege checks

## Dependencies

### GitHub Actions
- `actions/checkout@v4`
- `actions/setup-python@v4`
- `actions/cache@v3`
- `actions/upload-artifact@v3`
- `codecov/codecov-action@v3`

### Python Dependencies
- `coverage`: Test coverage
- `flake8`: Linting
- `isort`: Import sorting
- `bandit`: Security scanning
- `safety`: Dependency scanning
- `build`: Package building
- `twine`: Package publishing

## Monitoring

### Status Badges
- CI Status: ![CI](https://github.com/lcortes/wipeit/actions/workflows/ci.yml/badge.svg)
- Tests Status: ![Tests](https://github.com/lcortes/wipeit/actions/workflows/tests.yml/badge.svg)
- Python Version: ![Python 3.8+](https://img.shields.io/badge/python-3.8+-blue.svg)
- License: ![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)

### Notifications
- Email notifications for failed builds
- Slack integration (if configured)
- GitHub notifications

## Troubleshooting

### Common Issues

#### Test Failures
```bash
# Check test output
python3 test_wipeit.py -v

# Check coverage
coverage run test_wipeit.py
coverage report
```

#### Permission Errors
```bash
# Ensure proper permissions
chmod +x wipeit.py
chmod +x test-ci.sh
```

#### Dependency Issues
```bash
# Update dependencies
pip3 install --upgrade pip
pip3 install coverage flake8 isort bandit safety
```

### Debug Mode
```bash
# Run with debug output
python3 -u test_wipeit.py -v 2>&1 | tee test-output.log
```

## Best Practices

### Development Workflow
1. Create feature branch
2. Make changes
3. Run local tests: `./test-ci.sh`
4. Commit changes
5. Push to GitHub
6. Create pull request
7. Review CI results
8. Merge after approval

### Code Quality
- Write tests for new features
- Maintain test coverage above 80%
- Follow PEP 8 style guidelines
- Add documentation for new features
- Update CHANGES.md for significant changes

### Security
- Never commit credentials
- Validate all inputs
- Handle errors gracefully
- Test with non-root user
- Review security scan results

## Future Improvements

### Planned Enhancements
- [ ] Performance benchmarking
- [ ] Cross-platform testing
- [ ] Docker container testing
- [ ] Integration with external services
- [ ] Automated dependency updates
- [ ] Code quality metrics dashboard

### Monitoring Enhancements
- [ ] Real-time test results
- [ ] Performance regression detection
- [ ] Automated rollback on failures
- [ ] Custom metrics and alerts

## Resources

### Documentation
- [GitHub Actions Documentation](https://docs.github.com/en/actions)
- [Python Testing Guide](https://docs.python.org/3/library/unittest.html)
- [Coverage.py Documentation](https://coverage.readthedocs.io/)

### Tools
- [Bandit Security Scanner](https://bandit.readthedocs.io/)
- [Flake8 Linter](https://flake8.pycqa.org/)
- [isort Import Sorter](https://pycqa.github.io/isort/)

### Support
- GitHub Issues for bug reports
- GitHub Discussions for questions
- Pull requests for contributions
