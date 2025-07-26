#!/usr/bin/env python3
"""
Test runner script for OpenCodeSpace.

This script provides a convenient way to run tests with different configurations
and options. It handles test discovery, coverage reporting, and parallel execution.
"""

import argparse
import subprocess
import sys
import os
from pathlib import Path


class TestRunner:
    """Main test runner class."""
    
    def __init__(self):
        self.project_root = Path(__file__).parent
        self.test_dir = self.project_root / "tests"
        
    def run_command(self, cmd, description=""):
        """Run a command and handle errors."""
        if description:
            print(f"\n🔧 {description}")
        
        print(f"Running: {' '.join(cmd)}")
        result = subprocess.run(cmd, cwd=self.project_root)
        
        if result.returncode != 0:
            print(f"❌ Command failed with exit code {result.returncode}")
            sys.exit(result.returncode)
        
        return result
    
    def install_dependencies(self):
        """Install test dependencies."""
        self.run_command([
            sys.executable, "-m", "pip", "install", 
            "-r", "tests/test_requirements.txt"
        ], "Installing test dependencies")
    
    def install_package(self):
        """Install the package in development mode."""
        self.run_command([
            sys.executable, "-m", "pip", "install", "-e", "."
        ], "Installing package in development mode")
    
    def run_tests(self, args):
        """Run tests with specified arguments."""
        cmd = [sys.executable, "-m", "pytest"]
        
        # Add test directory
        cmd.append(str(self.test_dir))
        
        # Add coverage options if requested
        if args.coverage:
            cmd.extend([
                "--cov=src/opencodespace",
                "--cov-report=term-missing",
                "--cov-report=html:htmlcov",
                "--cov-report=xml"
            ])
            if args.coverage_fail:
                cmd.append(f"--cov-fail-under={args.coverage_fail}")
        
        # Add parallel execution
        if args.parallel:
            cmd.extend(["-n", str(args.parallel) if args.parallel != "auto" else "auto"])
        
        # Add verbosity
        if args.verbose:
            cmd.append("-v")
        
        # Add specific test markers
        if args.markers:
            cmd.extend(["-m", args.markers])
        
        # Add specific test files/classes/methods
        if args.tests:
            cmd.extend(args.tests)
        
        # Add extra pytest args
        if args.pytest_args:
            cmd.extend(args.pytest_args)
        
        description = f"Running tests"
        if args.markers:
            description += f" (markers: {args.markers})"
        if args.tests:
            description += f" (specific: {', '.join(args.tests)})"
        
        self.run_command(cmd, description)
    
    def run_quick_tests(self):
        """Run quick unit tests only."""
        cmd = [
            sys.executable, "-m", "pytest",
            str(self.test_dir),
            "-m", "unit or (not integration and not slow)",
            "-v"
        ]
        self.run_command(cmd, "Running quick unit tests")
    
    def run_integration_tests(self):
        """Run integration tests only."""
        cmd = [
            sys.executable, "-m", "pytest",
            str(self.test_dir),
            "-m", "integration",
            "-v"
        ]
        self.run_command(cmd, "Running integration tests")
    
    def run_coverage_report(self):
        """Generate and display coverage report."""
        cmd = [
            sys.executable, "-m", "pytest",
            str(self.test_dir),
            "--cov=src/opencodespace",
            "--cov-report=term-missing",
            "--cov-report=html:htmlcov",
            "--cov-report=xml",
            "--cov-fail-under=85"
        ]
        self.run_command(cmd, "Generating coverage report")
        
        print("\n📊 Coverage report generated:")
        print("  - Terminal: displayed above")
        print("  - HTML: htmlcov/index.html")
        print("  - XML: coverage.xml")
    
    def lint_tests(self):
        """Run linting on test files."""
        # Check if flake8 is available
        try:
            cmd = [sys.executable, "-m", "flake8", str(self.test_dir)]
            self.run_command(cmd, "Linting test files")
        except FileNotFoundError:
            print("ℹ️  flake8 not found, skipping linting")
    
    def check_test_structure(self):
        """Check test file structure and naming."""
        print("\n🔍 Checking test structure...")
        
        test_files = list(self.test_dir.glob("test_*.py"))
        if not test_files:
            print("❌ No test files found!")
            sys.exit(1)
        
        print(f"✅ Found {len(test_files)} test files:")
        for test_file in sorted(test_files):
            print(f"  - {test_file.name}")
        
        # Check for conftest.py
        conftest = self.test_dir / "conftest.py"
        if conftest.exists():
            print("✅ conftest.py found")
        else:
            print("⚠️  conftest.py not found")
        
        # Check for test requirements
        test_req = self.test_dir / "test_requirements.txt"
        if test_req.exists():
            print("✅ test_requirements.txt found")
        else:
            print("⚠️  test_requirements.txt not found")


def main():
    """Main entry point."""
    parser = argparse.ArgumentParser(
        description="Test runner for OpenCodeSpace",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python run_tests.py                          # Run all tests
  python run_tests.py --quick                  # Run only unit tests
  python run_tests.py --integration            # Run only integration tests
  python run_tests.py --coverage               # Run with coverage
  python run_tests.py --parallel auto          # Run in parallel
  python run_tests.py --markers "unit"         # Run tests with specific markers
  python run_tests.py --tests test_main.py     # Run specific test file
  python run_tests.py --setup                  # Install dependencies only
  python run_tests.py --check                  # Check test structure
        """
    )
    
    # Main actions
    parser.add_argument(
        "--setup", 
        action="store_true",
        help="Install test dependencies and package"
    )
    parser.add_argument(
        "--quick", 
        action="store_true",
        help="Run quick unit tests only"
    )
    parser.add_argument(
        "--integration", 
        action="store_true",
        help="Run integration tests only"
    )
    parser.add_argument(
        "--coverage", 
        action="store_true",
        help="Generate coverage report"
    )
    parser.add_argument(
        "--coverage-fail",
        type=int,
        default=85,
        help="Fail if coverage is below this percentage (default: 85)"
    )
    parser.add_argument(
        "--check", 
        action="store_true",
        help="Check test structure and exit"
    )
    parser.add_argument(
        "--lint", 
        action="store_true",
        help="Run linting on test files"
    )
    
    # Test execution options
    parser.add_argument(
        "--parallel", 
        nargs="?",
        const="auto",
        help="Run tests in parallel (specify number or 'auto')"
    )
    parser.add_argument(
        "--verbose", "-v",
        action="store_true",
        help="Verbose output"
    )
    parser.add_argument(
        "--markers", "-m",
        help="Run tests with specific markers (e.g., 'unit', 'integration')"
    )
    parser.add_argument(
        "--tests", "-t",
        nargs="+",
        help="Specific test files, classes, or methods to run"
    )
    parser.add_argument(
        "--pytest-args",
        nargs=argparse.REMAINDER,
        help="Additional arguments to pass to pytest"
    )
    
    args = parser.parse_args()
    runner = TestRunner()
    
    print("🧪 OpenCodeSpace Test Runner")
    print("=" * 50)
    
    # Handle setup
    if args.setup:
        runner.install_dependencies()
        runner.install_package()
        print("\n✅ Setup complete!")
        return
    
    # Handle structure check
    if args.check:
        runner.check_test_structure()
        return
    
    # Handle linting
    if args.lint:
        runner.lint_tests()
        return
    
    # Ensure dependencies are installed
    if not (runner.test_dir / "test_requirements.txt").exists():
        print("❌ Test requirements file not found!")
        print("Run with --setup to install dependencies")
        sys.exit(1)
    
    try:
        import pytest
    except ImportError:
        print("❌ pytest not found! Installing dependencies...")
        runner.install_dependencies()
    
    # Run specific test types
    if args.quick:
        runner.run_quick_tests()
    elif args.integration:
        runner.run_integration_tests()
    elif args.coverage:
        runner.run_coverage_report()
    else:
        # Run tests with specified options
        runner.run_tests(args)
    
    print("\n✅ Tests completed successfully!")


if __name__ == "__main__":
    main() 