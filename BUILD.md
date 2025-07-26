# Build System Documentation

This project includes a comprehensive build system with multiple interfaces for development tasks.

## Development Build Script

The project includes a development build script at `dev-build.py` that provides a unified interface for common development tasks:

```bash
# Quick development setup
python dev-build.py install

# Run tests during development  
python dev-build.py test --quick

# Full build pipeline
python dev-build.py all
```

## Build System Overview

Three equivalent interfaces for development tasks:

- **`python dev-build.py [command]`** - Feature-rich Python script (cross-platform)
- **`make [target]`** - Traditional Makefile interface (Unix/Linux)
- **`./build.sh [command]`** - Simple shell script wrapper

### Available Commands

| Command | Description |
|---------|-------------|
| `install` | Install dependencies and package in development mode |
| `test` | Run the complete test suite |
| `test-quick` | Run quick tests (recommended for development) |
| `clean` | Clean build artifacts and cache files |
| `build` | Build package for distribution |
| `lint` | Run code quality checks |
| `all` | Run complete build pipeline |

### Examples

```bash
# Development workflow
python dev-build.py install     # Set up development environment
python dev-build.py test-quick  # Test your changes
python dev-build.py all         # Full build pipeline before PR

# Building for distribution
python dev-build.py clean
python dev-build.py build

# Get help
python dev-build.py help
make help
./build.sh help
```

## Package Building

For package distribution, the project uses modern Python packaging standards:

```bash
# Install build tools
pip install build

# Build wheel and source distribution
python -m build

# Check package
pip install twine
twine check dist/*
```

This is also handled automatically by the GitHub Actions CI/CD pipeline. 