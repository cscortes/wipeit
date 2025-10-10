# Safety CLI Setup Guide

This document explains how to set up Safety CLI authentication for both local development and CI/CD.

## Overview

We've migrated from the deprecated `safety check` command to the new `safety scan` command. The new command requires authentication but provides enhanced security scanning capabilities.

## Local Development Setup

### Option 1: Interactive Authentication (Recommended)
```bash
# Run this command and follow the browser authentication
safety auth login
```

### Option 2: Headless Authentication
```bash
# For environments without browser access
safety auth login --headless
# Copy the provided URL to a browser and paste the response
```

### Verify Authentication
```bash
# Check if you're authenticated
safety auth status

# Test the scan command
safety scan
```

## CI/CD Setup (GitHub Actions)

**⚠️ IMPORTANT**: The GitHub Actions workflow will fail without the `SAFETY_API_KEY` secret. Follow these steps to set it up:

### 1. Get Your API Key
1. Go to https://platform.safetycli.com
2. Sign up or log in to your account (free account available)
3. Navigate to your profile/settings
4. Generate an API key

### 2. Add API Key to GitHub Secrets
1. Go to your GitHub repository
2. Navigate to **Settings** → **Secrets and variables** → **Actions**
3. Click **"New repository secret"**
4. **Name**: `SAFETY_API_KEY`
5. **Value**: Your API key from step 1
6. Click **"Add secret"**

### 3. Verify CI/CD Setup
The GitHub Actions workflow will automatically use the API key from the secret. If the secret is not set, the workflow will skip the safety scan and show a warning message.

## Migration Notes

### What Changed
- `safety check` → `safety scan`
- `--json --output file.json` → `--save-as json file.json`
- Added authentication requirement

### Benefits
- ✅ Future-proof (deprecation deadline: June 2024)
- ✅ Enhanced scanning capabilities
- ✅ Active support and updates
- ✅ Better integration with Safety Platform

### Troubleshooting

#### "Safety is not authenticated" Error
```bash
# Run authentication
safety auth login
```

#### "API key required" Error in CI/CD
- Ensure `SAFETY_API_KEY` secret is set in GitHub repository
- Verify the API key is valid and active

#### "No module named safety" Error
```bash
# Install/update safety
pip install -U safety
# or with uv
uv add --dev safety
```

#### "Missing command" or "No such option" Error in CI/CD
This usually means the `SAFETY_API_KEY` secret is not set or is empty:
1. Check that `SAFETY_API_KEY` secret exists in GitHub repository settings
2. Verify the secret value is not empty
3. Ensure the secret name is exactly `SAFETY_API_KEY` (case-sensitive)

#### "SAFETY_API_KEY secret not set" Warning
This is expected if you haven't set up the API key yet. The workflow will continue without failing, but safety scanning will be skipped.

## Commands Reference

### Local Development
```bash
# Check authentication status
safety auth status

# Run security scan
safety scan

# Run with detailed output
safety scan --detailed-output

# Save results to file
safety scan --save-as json results.json
```

### CI/CD
```bash
# With API key (automatically used in GitHub Actions)
safety --key $SAFETY_API_KEY scan

# Save JSON report
safety --key $SAFETY_API_KEY scan --save-as json report.json
```

## Support

- Documentation: https://docs.safetycli.com
- Support: support@safetycli.com
- Platform: https://platform.safetycli.com
