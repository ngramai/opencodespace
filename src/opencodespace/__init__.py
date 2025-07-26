"""
OpenCodeSpace - Launch disposable VS Code development environments.

This package provides a CLI tool for quickly spinning up development containers
with AI tooling support, either locally using Docker or remotely on various
cloud platforms.
"""

from .main import main

__version__ = "0.4.0"
__author__ = "OpenCodeSpace Contributors"
__all__ = ["main"]