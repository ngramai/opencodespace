#!/usr/bin/env python3
"""
OpenCodeSpace Build Script
==========================

Automates common development tasks including dependency installation,
package building, testing, and deployment preparation.

Usage:
    python build.py [command] [options]

Commands:
    install     Install dependencies and package in development mode
    test        Run the test suite (with optional quick mode)
    clean       Clean build artifacts and cache files
    build       Build the package for distribution
    lint        Run code linting and formatting checks
    all         Run the complete build pipeline
    help        Show this help message

Examples:
    python build.py install          # Install dependencies
    python build.py test --quick     # Run quick tests
    python build.py clean            # Clean build artifacts
    python build.py all              # Full build pipeline
"""

import os
import sys
import subprocess
import shutil
import argparse
from pathlib import Path


class Colors:
    """ANSI color codes for terminal output."""
    HEADER = '\033[95m'
    OKBLUE = '\033[94m'
    OKCYAN = '\033[96m'
    OKGREEN = '\033[92m'
    WARNING = '\033[93m'
    FAIL = '\033[91m'
    ENDC = '\033[0m'
    BOLD = '\033[1m'


def print_step(message: str):
    """Print a build step with formatting."""
    print(f"\n{Colors.OKBLUE}🔨 {message}{Colors.ENDC}")


def print_success(message: str):
    """Print a success message."""
    print(f"{Colors.OKGREEN}✅ {message}{Colors.ENDC}")


def print_warning(message: str):
    """Print a warning message."""
    print(f"{Colors.WARNING}⚠️  {message}{Colors.ENDC}")


def print_error(message: str):
    """Print an error message."""
    print(f"{Colors.FAIL}❌ {message}{Colors.ENDC}")


def run_command(cmd: list, description: str, check: bool = True) -> bool:
    """Run a command and handle errors."""
    print(f"Running: {' '.join(cmd)}")
    try:
        result = subprocess.run(cmd, check=check, capture_output=True, text=True)
        if result.returncode == 0:
            print_success(f"{description} completed successfully")
            return True
        else:
            print_error(f"{description} failed with exit code {result.returncode}")
            if result.stderr:
                print(f"Error output: {result.stderr}")
            return False
    except subprocess.CalledProcessError as e:
        print_error(f"{description} failed: {e}")
        if e.stderr:
            print(f"Error output: {e.stderr}")
        return False
    except FileNotFoundError:
        print_error(f"Command not found: {cmd[0]}")
        return False


def check_uv_installed() -> bool:
    """Check if uv is installed."""
    try:
        subprocess.run(["uv", "--version"], check=True, capture_output=True)
        return True
    except (subprocess.CalledProcessError, FileNotFoundError):
        return False


def install_dependencies():
    """Install project dependencies and package in development mode."""
    print_step("Installing dependencies and package")
    
    if not check_uv_installed():
        print_error("uv is not installed. Please install uv first:")
        print("curl -LsSf https://astral.sh/uv/install.sh | sh")
        return False
    
    # Install dependencies
    if not run_command(["uv", "pip", "install", "-r", "requirements.txt"], 
                      "Installing requirements"):
        return False
    
    # Install test dependencies
    test_req_path = Path("tests/test_requirements.txt")
    if test_req_path.exists():
        if not run_command(["uv", "pip", "install", "-r", str(test_req_path)], 
                          "Installing test requirements"):
            return False
    
    # Install package in development mode
    if not run_command(["uv", "pip", "install", "-e", "."], 
                      "Installing package in development mode"):
        return False
    
    print_success("All dependencies installed successfully")
    return True


def run_tests(quick: bool = False):
    """Run the test suite."""
    if quick:
        print_step("Running quick tests")
        cmd = ["python", "run_tests.py", "--quick"]
    else:
        print_step("Running full test suite")
        cmd = ["python", "run_tests.py"]
    
    return run_command(cmd, "Test execution", check=False)


def clean_build():
    """Clean build artifacts and cache files."""
    print_step("Cleaning build artifacts")
    
    patterns_to_remove = [
        "build/",
        "dist/",
        "*.egg-info/",
        "__pycache__/",
        "**/__pycache__/",
        ".pytest_cache/",
        ".coverage",
        "htmlcov/",
        "*.pyc",
        "**/*.pyc",
        "*.pyo",
        "**/*.pyo",
    ]
    
    removed_count = 0
    for pattern in patterns_to_remove:
        if "**/" in pattern:
            # Recursive pattern
            for path in Path(".").rglob(pattern.replace("**/", "")):
                if path.exists():
                    if path.is_dir():
                        shutil.rmtree(path)
                    else:
                        path.unlink()
                    removed_count += 1
        else:
            # Non-recursive pattern
            for path in Path(".").glob(pattern):
                if path.exists():
                    if path.is_dir():
                        shutil.rmtree(path)
                    else:
                        path.unlink()
                    removed_count += 1
    
    print_success(f"Cleaned {removed_count} files/directories")
    return True


def build_package():
    """Build the package for distribution."""
    print_step("Building package")
    
    # Clean first
    clean_build()
    
    # Build using setuptools
    if not run_command(["python", "-m", "build"], "Package building"):
        # Fallback to setup.py if build module not available
        print_warning("python -m build failed, trying setup.py")
        if not run_command(["python", "setup.py", "sdist", "bdist_wheel"], 
                          "Package building with setup.py"):
            return False
    
    print_success("Package built successfully")
    return True


def run_lint():
    """Run code linting and formatting checks."""
    print_step("Running code quality checks")
    
    success = True
    
    # Check if flake8 is available
    try:
        subprocess.run(["flake8", "--version"], check=True, capture_output=True)
        if not run_command(["flake8", "src/", "tests/"], "Flake8 linting", check=False):
            success = False
    except (subprocess.CalledProcessError, FileNotFoundError):
        print_warning("flake8 not found, skipping linting")
    
    # Check if black is available
    try:
        subprocess.run(["black", "--version"], check=True, capture_output=True)
        if not run_command(["black", "--check", "src/", "tests/"], "Black formatting check", check=False):
            print_warning("Code formatting issues found. Run 'black src/ tests/' to fix.")
            success = False
    except (subprocess.CalledProcessError, FileNotFoundError):
        print_warning("black not found, skipping format checking")
    
    if success:
        print_success("All code quality checks passed")
    
    return success


def run_all():
    """Run the complete build pipeline."""
    print_step("Running complete build pipeline")
    
    steps = [
        ("Installing dependencies", install_dependencies),
        ("Running tests", lambda: run_tests(quick=False)),
        ("Running lint checks", run_lint),
        ("Building package", build_package),
    ]
    
    for step_name, step_func in steps:
        if not step_func():
            print_error(f"Build pipeline failed at: {step_name}")
            return False
    
    print_success("🎉 Complete build pipeline completed successfully!")
    return True


def show_help():
    """Show help information."""
    print(__doc__)


def main():
    """Main entry point."""
    parser = argparse.ArgumentParser(description="OpenCodeSpace Build Script")
    parser.add_argument("command", nargs="?", default="help",
                       choices=["install", "test", "clean", "build", "lint", "all", "help"],
                       help="Command to run")
    parser.add_argument("--quick", action="store_true",
                       help="Run quick tests (only for test command)")
    
    args = parser.parse_args()
    
    print(f"{Colors.HEADER}{Colors.BOLD}🚀 OpenCodeSpace Build Script{Colors.ENDC}")
    print(f"{Colors.HEADER}================================{Colors.ENDC}")
    
    success = False
    
    if args.command == "install":
        success = install_dependencies()
    elif args.command == "test":
        success = run_tests(quick=args.quick)
    elif args.command == "clean":
        success = clean_build()
    elif args.command == "build":
        success = build_package()
    elif args.command == "lint":
        success = run_lint()
    elif args.command == "all":
        success = run_all()
    elif args.command == "help":
        show_help()
        success = True
    else:
        print_error(f"Unknown command: {args.command}")
        show_help()
    
    if not success and args.command != "help":
        sys.exit(1)


if __name__ == "__main__":
    main() 