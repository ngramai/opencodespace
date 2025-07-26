# PyPI Publishing Setup

This document explains how to set up automatic publishing to PyPI using GitHub Actions.

## Overview

The repository includes GitHub Actions workflows for:
- **CI**: Running tests and building packages on every push/PR
- **Release Preparation**: Bumping versions and creating draft releases
- **PyPI Publishing**: Automatically publishing to PyPI when releases are published

## Setting Up PyPI Publishing

### 1. Configure PyPI Trusted Publisher

1. Go to [PyPI](https://pypi.org) and log in to your account
2. Navigate to "Manage" → "Publishing" → "Add a new pending publisher"
3. Fill in the details:
   - **Owner**: `devadutta` (your GitHub username)
   - **Repository name**: `opencodespace`
   - **Workflow name**: `publish-to-pypi.yml`
   - **Environment name**: `pypi`

### 2. Create the PyPI Environment

1. Go to your GitHub repository
2. Navigate to "Settings" → "Environments"
3. Click "New environment"
4. Name it `pypi`
5. Add protection rules if desired (e.g., require reviewers)

### 3. Publishing Process

#### Option A: Using the Release Workflow (Recommended)

1. Go to "Actions" tab in your repository
2. Find "Prepare Release" workflow
3. Click "Run workflow"
4. Enter the version number (e.g., `0.2.0`)
5. This will:
   - Update version numbers in all files
   - Commit the changes
   - Create a draft release
6. Go to "Releases" and edit the draft release
7. Add release notes and publish the release
8. The PyPI publishing workflow will automatically trigger

#### Option B: Manual Release

1. Manually update version in:
   - `src/opencodespace/__init__.py`
   - `pyproject.toml`  
   - `setup.py`
2. Commit and push changes
3. Create a new release with tag `v0.2.0` (for version 0.2.0)
4. The PyPI workflow will automatically trigger

## Workflow Files

- `.github/workflows/ci.yml` - Continuous integration
- `.github/workflows/release.yml` - Version management helper
- `.github/workflows/publish-to-pypi.yml` - PyPI publishing

## Security Features

- Uses PyPI's trusted publisher feature (no API tokens needed)
- Signs packages with Sigstore for security
- Uploads signed packages to GitHub releases
- Only publishes on tagged releases for safety

## Testing the Build

The CI workflow tests package building on every push. You can also test locally:

```bash
# Install build tools
pip install build twine

# Build the package
python -m build

# Check the package
twine check dist/*

# Test install
pip install dist/*.whl
opencodespace --version
``` 