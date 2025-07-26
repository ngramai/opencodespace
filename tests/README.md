# OpenCodeSpace Test Suite

This directory contains comprehensive end-to-end tests for the OpenCodeSpace project. The test suite covers all major functionality including provider systems, CLI interface, configuration management, and integration workflows.

## 📁 Test Structure

```
tests/
├── conftest.py                 # Pytest configuration and shared fixtures
├── test_providers_base.py      # Tests for base provider interface and registry
├── test_providers_local.py     # Tests for Local Docker provider
├── test_providers_fly.py       # Tests for Fly.io provider  
├── test_main.py               # Tests for main OpenCodeSpace class and CLI
├── test_integration.py        # End-to-end integration tests
├── test_requirements.txt      # Testing dependencies
└── README.md                  # This file
```

## 🚀 Running Tests

### Prerequisites

1. **Install test dependencies:**
   ```bash
   pip install -r tests/test_requirements.txt
   ```

2. **Install the package in development mode:**
   ```bash
   pip install -e .
   ```

### Basic Test Execution

```bash
# Run all tests
pytest

# Run with verbose output
pytest -v

# Run specific test file
pytest tests/test_main.py

# Run specific test class
pytest tests/test_main.py::TestOpenCodeSpace

# Run specific test method
pytest tests/test_main.py::TestOpenCodeSpace::test_initialization
```

### Test Categories

Tests are organized using pytest markers:

```bash
# Run only unit tests (fast)
pytest -m unit

# Run only integration tests 
pytest -m integration

# Run CLI tests
pytest -m cli

# Run provider tests
pytest -m providers

# Skip slow tests
pytest -m "not slow"
```

### Coverage Reports

```bash
# Generate coverage report
pytest --cov=src/opencodespace

# Generate HTML coverage report
pytest --cov=src/opencodespace --cov-report=html

# View coverage report
open htmlcov/index.html
```

### Parallel Execution

```bash
# Run tests in parallel (requires pytest-xdist)
pytest -n auto

# Specify number of workers
pytest -n 4
```

## 🧪 Test Categories

### Unit Tests

**Location:** `test_providers_base.py`, `test_providers_local.py`, `test_providers_fly.py`, `test_main.py`

- Test individual components in isolation
- Use extensive mocking to avoid external dependencies
- Focus on edge cases and error conditions
- Fast execution (< 1 second per test)

**Examples:**
- Provider interface compliance
- Configuration validation
- Command building logic
- Error handling

### Integration Tests

**Location:** `test_integration.py`

- Test complete workflows from start to finish
- Test interaction between multiple components
- Simulate real-world usage scenarios
- Use mocking for external services (Docker, flyctl)

**Examples:**
- Complete deploy → stop → remove workflows
- Interactive setup wizards
- Configuration persistence
- Platform switching

### CLI Tests

**Location:** `test_main.py::TestCLI`

- Test command-line interface using Click's testing utilities
- Test argument parsing and validation
- Test error handling and user feedback
- Test help text and version information

## 🔧 Test Fixtures

### Common Fixtures (conftest.py)

- **`temp_project_dir`** - Temporary directory for test projects
- **`git_project_dir`** - Temporary directory with initialized git repository
- **`sample_config`** - Sample configuration for local deployment
- **`fly_config`** - Sample configuration for Fly.io deployment
- **`mock_docker`** - Mock Docker subprocess calls
- **`mock_flyctl`** - Mock flyctl subprocess calls
- **`mock_vscode_detection`** - Mock VS Code/Cursor detection
- **`mock_questionary`** - Mock interactive prompts

### Usage Examples

```python
def test_example(temp_project_dir, sample_config, mock_docker):
    """Test that uses multiple fixtures."""
    # temp_project_dir provides a clean temporary directory
    # sample_config provides realistic configuration
    # mock_docker mocks all Docker interactions
    pass
```

## 🎯 Test Coverage

The test suite aims for comprehensive coverage of:

- **Provider System** (95%+ coverage)
  - Base provider interface
  - Local Docker provider
  - Fly.io provider
  - Provider registry

- **Configuration Management** (90%+ coverage)
  - TOML file loading/saving
  - Default configuration generation
  - Interactive setup workflows
  - Validation and error handling

- **CLI Interface** (85%+ coverage)
  - Command parsing
  - Error handling
  - Help text
  - Non-interactive mode

- **Integration Workflows** (80%+ coverage)
  - Complete deployment workflows
  - Multi-step operations
  - Error recovery

## 🔍 Mocking Strategy

### External Dependencies

All external dependencies are mocked to ensure:
- Tests run in isolation
- No actual Docker containers are created
- No actual Fly.io deployments are made
- No actual files are written outside test directories

### Key Mocked Components

1. **Subprocess calls** - Mock `docker`, `flyctl`, `git` commands
2. **File system operations** - Mock file reading/writing when needed
3. **Network operations** - Mock any HTTP requests
4. **Interactive prompts** - Mock questionary inputs
5. **Resource files** - Mock package resource loading

### Example Mocking

```python
@patch('subprocess.run')
def test_docker_deployment(mock_run, temp_project_dir):
    """Example of mocking subprocess calls."""
    # Mock successful Docker operations
    mock_run.side_effect = [
        Mock(returncode=0, stdout=""),  # docker info
        Mock(returncode=0, stdout=""),  # docker ps
        Mock(returncode=0),             # docker build
        Mock(returncode=0),             # docker run
    ]
    
    # Test logic here...
    
    # Verify correct commands were called
    assert mock_run.call_count == 4
```

## 🐛 Debugging Tests

### Verbose Output

```bash
# Show all print statements and logging
pytest -s

# Show detailed test progress
pytest -v

# Show local variables on failure
pytest -l
```

### Running Individual Tests

```bash
# Debug specific failing test
pytest tests/test_main.py::TestOpenCodeSpace::test_deploy -v -s
```

### Test Data Inspection

```bash
# Drop into debugger on first failure
pytest --pdb

# Drop into debugger on every test
pytest --pdb-trace
```

## 🔧 Adding New Tests

### Test File Naming

- `test_*.py` for test files
- `Test*` for test classes  
- `test_*` for test methods

### Test Organization

1. **Group related tests** in the same test class
2. **Use descriptive names** that explain what is being tested
3. **Include docstrings** explaining the test purpose
4. **Use appropriate fixtures** to reduce boilerplate

### Example Test

```python
class TestNewFeature:
    """Tests for the new feature functionality."""
    
    def test_feature_success_case(self, temp_project_dir, sample_config):
        """Test that new feature works correctly with valid input."""
        # Arrange
        feature = NewFeature()
        
        # Act
        result = feature.do_something(sample_config)
        
        # Assert
        assert result.success is True
        assert result.message == "Expected success message"
    
    def test_feature_error_case(self):
        """Test that new feature handles errors appropriately."""
        feature = NewFeature()
        
        with pytest.raises(ValueError, match="Expected error message"):
            feature.do_something(invalid_config)
```

## 📊 Performance Considerations

### Test Execution Time

- **Unit tests**: < 1 second each
- **Integration tests**: < 10 seconds each
- **Full test suite**: < 2 minutes

### Optimization Tips

1. **Use parallel execution** for faster results
2. **Mock external dependencies** to avoid network delays
3. **Reuse fixtures** when possible
4. **Group related assertions** in single tests when appropriate

## 🎯 Quality Standards

### Test Quality Checklist

- [ ] Tests are isolated and don't depend on external state
- [ ] Tests clean up after themselves  
- [ ] Tests have clear, descriptive names
- [ ] Tests include appropriate error cases
- [ ] Mocks are used appropriately for external dependencies
- [ ] Tests run quickly (< 10 seconds for integration tests)
- [ ] Tests are deterministic (no flaky behavior)

### Code Coverage Goals

- **Overall coverage**: 85%+
- **Core functionality**: 95%+
- **Error handling**: 80%+
- **CLI interface**: 85%+

## 🤝 Contributing

When adding new functionality:

1. **Write tests first** (TDD approach recommended)
2. **Add appropriate test markers** for categorization
3. **Update this README** if adding new test categories
4. **Ensure all tests pass** before submitting PR
5. **Maintain coverage standards** (85%+ overall)

### Test Review Checklist

- [ ] Tests cover happy path scenarios
- [ ] Tests cover error conditions
- [ ] Tests are properly isolated
- [ ] Mocking is appropriate and complete
- [ ] Test names are descriptive
- [ ] Coverage metrics are maintained

---

For questions about the test suite, please refer to the main project documentation or open an issue. 