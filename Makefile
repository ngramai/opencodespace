# OpenCodeSpace Makefile
# ======================
# Alternative interface to build.py for common development tasks

.PHONY: help install test test-quick clean build lint all

# Default target
help:
	@echo "🚀 OpenCodeSpace Build Commands"
	@echo "================================"
	@echo ""
	@echo "Available targets:"
	@echo "  install     Install dependencies and package in development mode"
	@echo "  test        Run the complete test suite"
	@echo "  test-quick  Run quick tests only"
	@echo "  clean       Clean build artifacts and cache files"
	@echo "  build       Build the package for distribution"
	@echo "  lint        Run code linting and formatting checks"
	@echo "  all         Run the complete build pipeline"
	@echo "  help        Show this help message"
	@echo ""
	@echo "Examples:"
	@echo "  make install    # Install dependencies"
	@echo "  make test-quick # Run quick tests"
	@echo "  make clean      # Clean build artifacts"
	@echo "  make all        # Full build pipeline"
	@echo ""
	@echo "For more advanced options, use: python build.py help"

install:
	@python build.py install

test:
	@python build.py test

test-quick:
	@python build.py test --quick

clean:
	@python build.py clean

build:
	@python build.py build

lint:
	@python build.py lint

all:
	@python build.py all 