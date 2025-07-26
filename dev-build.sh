#!/bin/bash
# OpenCodeSpace Build Script (Shell Version)
# ===========================================
# Simple shell wrapper around the Python build script

set -e  # Exit on any error

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
BLUE='\033[0;34m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Helper functions
print_header() {
    echo -e "${BLUE}🚀 OpenCodeSpace Build Script${NC}"
    echo -e "${BLUE}================================${NC}"
}

print_usage() {
    echo "Usage: $0 [command]"
    echo ""
    echo "Commands:"
    echo "  install     Install dependencies and package in development mode"
    echo "  test        Run the complete test suite"
    echo "  test-quick  Run quick tests only"
    echo "  clean       Clean build artifacts and cache files"
    echo "  build       Build the package for distribution"
    echo "  lint        Run code linting and formatting checks"
    echo "  all         Run the complete build pipeline"
    echo "  help        Show this help message"
    echo ""
    echo "Examples:"
    echo "  $0 install    # Install dependencies"
    echo "  $0 test-quick # Run quick tests"
    echo "  $0 clean      # Clean build artifacts"
    echo "  $0 all        # Full build pipeline"
}

# Main script
print_header

case "${1:-help}" in
    install)
        python build.py install
        ;;
    test)
        python build.py test
        ;;
    test-quick)
        python build.py test --quick
        ;;
    clean)
        python build.py clean
        ;;
    build)
        python build.py build
        ;;
    lint)
        python build.py lint
        ;;
    all)
        python build.py all
        ;;
    help)
        print_usage
        ;;
    *)
        echo -e "${RED}Error: Unknown command '$1'${NC}"
        echo ""
        print_usage
        exit 1
        ;;
esac 