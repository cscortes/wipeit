# Release Checklist

This document outlines the step-by-step process for preparing and releasing a new version of wipeit.

## Pre-Release Preparation

### 1. Clean Files
Remove invisible characters from all source files:
```bash
make clean_files
```

### 2. Code Quality Review
- Review all modified and new files
- Ensure all files conform to `PROGRAMMING_STYLE_GUIDE.md`
- Verify code formatting, naming conventions, and documentation standards

### 3. Pre-Git Preparation
Run pre-git checks and formatting:
```bash
make pre-git-prep
```

## Testing and Validation

### 4. Security Scan
Run security analysis on the codebase:
```bash
make security
```
**If security scan fails:**
- **STOP** the release process
- Review and address all security issues identified
- Do not proceed until all security concerns are resolved

**If security scan passes:**
- Continue to the next step

### 5. Run Test Suite
Execute all unit and integration tests:
```bash
make tests
```
**If tests fail:**
- **STOP** the release process
- Investigate and fix failing tests
- Re-run tests until all pass
- Do not proceed until all tests pass

**If tests pass:**
- Continue to the next step

## Version Management

### 6. Update Version Number
Bump the semantic version number according to the change type:
- **Patch** (x.y.Z): Bug fixes and minor changes
- **Minor** (x.Y.0): New features, backward compatible
- **Major** (X.0.0): Breaking changes

Update version in the following locations:
- `pyproject.toml`
- `src/wipeit.py`
- `src/test_wipeit.py`
- Any other Python files containing version information

## Documentation Updates

### 7. Update Documentation
Review and update all relevant documentation:
- `CHANGES.md` - Add release notes with changes, fixes, and new features
- `README.md` - Update usage examples, requirements, or features if needed
- `TESTDESIGN.md` - Document new tests or testing approaches
- `ARCH.md` - Update architecture documentation if design changed

## Git Operations

### 8. Create Version Tag
Create a Git tag for the new version:
```bash
git tag -a v<VERSION> -m "Release version <VERSION>"
```
Example: `git tag -a v1.3.0 -m "Release version 1.3.0"`

### 9. Commit Changes
Stage and commit all release-related changes:
```bash
git add .
git commit -m "Release version <VERSION>"
```

### 10. Push to Repository
Push commits and tags to the remote repository:
```bash
git push origin master
git push origin v<VERSION>
```

## Post-Release

### 11. Build Distribution
Build the distribution packages:
```bash
python -m build
```

### 12. Verify Distribution
- Check that wheel and source distribution were created in `dist/`
- Verify version numbers in distribution filenames match the release version

## Release Complete ✓

The release process is now complete. Verify that the new version is available in the repository and all documentation is up to date.
