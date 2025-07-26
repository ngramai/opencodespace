"""Pytest configuration and shared fixtures for OpenCodeSpace tests."""

import os
import tempfile
import pytest
from pathlib import Path
from unittest.mock import Mock, patch, MagicMock
from typing import Dict, Any
import shutil
import subprocess

# Import the modules we'll be testing
from opencodespace.main import OpenCodeSpace
from opencodespace.providers import FlyProvider, LocalProvider, ProviderRegistry


@pytest.fixture
def temp_project_dir():
    """Create a temporary project directory for testing."""
    with tempfile.TemporaryDirectory() as temp_dir:
        project_path = Path(temp_dir)
        yield project_path


@pytest.fixture
def git_project_dir():
    """Create a temporary project directory with git initialized."""
    with tempfile.TemporaryDirectory() as temp_dir:
        project_path = Path(temp_dir)
        
        # Initialize git repository
        subprocess.run(["git", "init"], cwd=project_path, check=True, 
                      capture_output=True)
        subprocess.run(["git", "config", "user.name", "Test User"], 
                      cwd=project_path, check=True, capture_output=True)
        subprocess.run(["git", "config", "user.email", "test@example.com"], 
                      cwd=project_path, check=True, capture_output=True)
        
        # Add a remote
        subprocess.run(["git", "remote", "add", "origin", 
                       "git@github.com:test/repo.git"], 
                      cwd=project_path, check=True, capture_output=True)
        
        yield project_path


@pytest.fixture
def sample_config():
    """Provide a sample configuration dictionary."""
    return {
        "name": "test-project",
        "platform": "local",
        "upload_folder": True,
        "git_branching": True,
        "api_keys": ["OPENAI_API_KEY", "ANTHROPIC_API_KEY"],
        "env": {
            "OPENAI_API_KEY": "sk-test-key",
            "ANTHROPIC_API_KEY": "sk-ant-test-key"
        },
        "vscode_config": {
            "copy_settings": True,
            "copy_extensions": True,
            "detected_editors": ["vscode", "cursor"],
            "vscode_settings_path": "/fake/path/to/vscode/settings.json",
            "cursor_settings_path": "/fake/path/to/cursor/settings.json",
            "vscode_extensions_list": ["ms-python.python", "ms-vscode.vscode-json"],
            "cursor_extensions_list": ["cursor.ai", "ms-python.python"]
        }
    }


@pytest.fixture
def fly_config():
    """Provide a sample Fly.io configuration."""
    return {
        "name": "test-fly-app",
        "platform": "fly",
        "upload_folder": False,
        "git_repo_url": "git@github.com:test/repo.git",
        "ssh_key_path": "/fake/path/to/ssh/key",
        "vscode_password": "test-password-123",
        "env": {
            "OPENAI_API_KEY": "sk-test-key"
        }
    }


@pytest.fixture
def mock_docker():
    """Mock Docker subprocess calls."""
    with patch('subprocess.run') as mock_run, \
         patch('subprocess.call') as mock_call:
        
        # Mock successful Docker checks
        mock_call.return_value = 0  # which docker
        mock_run.return_value = Mock(returncode=0, stdout="", stderr="")
        
        yield mock_run, mock_call


@pytest.fixture
def mock_flyctl():
    """Mock flyctl subprocess calls."""
    with patch('subprocess.run') as mock_run, \
         patch('subprocess.call') as mock_call:
        
        # Mock successful flyctl checks
        mock_call.return_value = 0  # which flyctl
        mock_run.return_value = Mock(returncode=0, stdout="", stderr="")
        
        yield mock_run, mock_call


@pytest.fixture
def mock_git():
    """Mock git subprocess calls."""
    with patch('subprocess.run') as mock_run:
        mock_run.return_value = Mock(
            returncode=0, 
            stdout="git@github.com:test/repo.git\n",
            stderr=""
        )
        yield mock_run


@pytest.fixture
def mock_vscode_detection():
    """Mock VS Code and Cursor detection."""
    def mock_run_side_effect(cmd, **kwargs):
        if "code" in cmd and "--version" in cmd:
            return Mock(returncode=0, stdout="1.74.0\n", stderr="")
        elif "cursor" in cmd and "--version" in cmd:
            return Mock(returncode=0, stdout="0.19.0\n", stderr="")
        elif "code" in cmd and "--list-extensions" in cmd:
            return Mock(returncode=0, stdout="ms-python.python\nms-vscode.vscode-json\n", stderr="")
        elif "cursor" in cmd and "--list-extensions" in cmd:
            return Mock(returncode=0, stdout="cursor.ai\nms-python.python\n", stderr="")
        else:
            return Mock(returncode=1, stdout="", stderr="command not found")
    
    with patch('subprocess.run', side_effect=mock_run_side_effect), \
         patch('pathlib.Path.exists') as mock_exists:
        
        # Mock editor installation paths - return True for most cases to avoid blocking
        mock_exists.return_value = True
        yield


@pytest.fixture
def mock_ssh_dir():
    """Mock SSH directory with test keys."""
    with tempfile.TemporaryDirectory() as temp_dir:
        ssh_dir = Path(temp_dir) / ".ssh"
        ssh_dir.mkdir()
        
        # Create fake SSH keys
        (ssh_dir / "id_rsa").write_text("fake private key content")
        (ssh_dir / "id_rsa.pub").write_text("fake public key content")
        (ssh_dir / "id_ed25519").write_text("fake ed25519 private key")
        (ssh_dir / "id_ed25519.pub").write_text("fake ed25519 public key")
        
        with patch('pathlib.Path.home', return_value=Path(temp_dir)):
            yield ssh_dir


@pytest.fixture
def opencodespace_instance():
    """Create an OpenCodeSpace instance for testing."""
    return OpenCodeSpace()


@pytest.fixture
def provider_registry():
    """Create a provider registry for testing."""
    registry = ProviderRegistry()
    registry.register(LocalProvider)
    registry.register(FlyProvider)
    return registry


@pytest.fixture
def mock_questionary():
    """Mock questionary for interactive testing."""
    with patch('questionary.confirm') as mock_confirm, \
         patch('questionary.select') as mock_select, \
         patch('questionary.text') as mock_text:
        
        # Set default responses
        mock_confirm.return_value.ask.return_value = True
        mock_select.return_value.ask.return_value = "local"
        mock_text.return_value.ask.return_value = "test-response"
        
        yield {
            'confirm': mock_confirm,
            'select': mock_select,
            'text': mock_text
        }


@pytest.fixture
def mock_toml():
    """Mock TOML file operations."""
    with patch('toml.load') as mock_load, \
         patch('toml.dump') as mock_dump:
        yield mock_load, mock_dump


@pytest.fixture
def mock_importlib_resources():
    """Mock importlib.resources for testing package resources."""
    with patch('opencodespace.providers.local.files') as mock_files, \
         patch('opencodespace.providers.local.as_file') as mock_as_file, \
         patch('opencodespace.providers.fly.files') as mock_fly_files, \
         patch('opencodespace.providers.fly.as_file') as mock_fly_as_file:
        
        # Mock file content
        mock_dockerfile_content = b"""
FROM codercom/code-server:latest
USER root
RUN apt-get update && apt-get install -y git
USER coder
EXPOSE 8080
"""
        
        mock_entrypoint_content = b"""#!/bin/bash
set -e
exec code-server --bind-addr 0.0.0.0:8080 --auth password
"""
        
        mock_fly_toml_content = b"""
app = "test-app"
primary_region = "ord"

[build]
  dockerfile = ".opencodespace/Dockerfile"

[[services]]
  http_checks = []
  internal_port = 8080
  processes = ["app"]
  protocol = "tcp"
  script_checks = []
"""
        
        # Mock resource files
        mock_resource = Mock()
        mock_resource.read_bytes.side_effect = lambda: {
            'Dockerfile': mock_dockerfile_content,
            'entrypoint.sh': mock_entrypoint_content,
            'fly.toml': mock_fly_toml_content
        }.get(mock_resource.name, b"")
        
        mock_files.return_value.__truediv__.return_value = mock_resource
        mock_as_file.return_value.__enter__.return_value = mock_resource
        mock_fly_files.return_value.__truediv__.return_value = mock_resource
        mock_fly_as_file.return_value.__enter__.return_value = mock_resource
        
        yield


@pytest.fixture(autouse=True)
def clean_environment():
    """Clean environment variables before each test."""
    original_env = os.environ.copy()
    
    # Remove any OpenCodeSpace-related environment variables
    env_vars_to_clean = [
        'PASSWORD', 'GIT_REPO_URL', 'SSH_PRIVATE_KEY', 'GIT_USER_NAME',
        'GIT_USER_EMAIL', 'VSCODE_EXTENSIONS', 'CURSOR_EXTENSIONS',
        'VSCODE_SETTINGS', 'CURSOR_SETTINGS', 'SKIP_GIT_SETUP'
    ]
    
    for var in env_vars_to_clean:
        os.environ.pop(var, None)
    
    yield
    
    # Restore original environment
    os.environ.clear()
    os.environ.update(original_env)


class MockClickContext:
    """Mock Click context for testing CLI commands."""
    
    def __init__(self, **kwargs):
        self.obj = kwargs
        self.params = {}
    
    def ensure_object(self, obj_type):
        if not hasattr(self, 'obj') or not isinstance(self.obj, dict):
            self.obj = {}
        return self.obj
    
    def invoke(self, command, **kwargs):
        """Mock command invocation."""
        return command.callback(**kwargs)
    
    def exit(self, code=0):
        """Mock context exit."""
        raise SystemExit(code)


@pytest.fixture
def mock_click_context():
    """Provide a mock Click context."""
    return MockClickContext(
        yes=False, 
        opencodespace=OpenCodeSpace()
    )


# Helper functions for tests
def create_test_file(path: Path, content: str = "test content") -> Path:
    """Create a test file with content."""
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content)
    return path


def create_test_config(project_path: Path, config: Dict[str, Any]) -> Path:
    """Create a test configuration file."""
    config_dir = project_path / ".opencodespace"
    config_dir.mkdir(exist_ok=True)
    config_path = config_dir / "config.toml"
    
    import toml
    with open(config_path, 'w') as f:
        toml.dump(config, f)
    
    return config_path


def assert_config_saved(project_path: Path, expected_config: Dict[str, Any]):
    """Assert that configuration was saved correctly."""
    config_path = project_path / ".opencodespace" / "config.toml"
    assert config_path.exists()
    
    import toml
    saved_config = toml.load(config_path)
    
    # Check key fields
    for key, value in expected_config.items():
        assert saved_config.get(key) == value 