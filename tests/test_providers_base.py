"""Tests for the base provider interface and provider registry."""

import pytest
from unittest.mock import Mock, patch, MagicMock
from pathlib import Path
from typing import Dict, Any

from opencodespace.providers.base import Provider
from opencodespace.providers.registry import ProviderRegistry
from opencodespace.providers import LocalProvider, FlyProvider


class TestProvider(Provider):
    """Test implementation of Provider for testing base functionality."""
    
    @property
    def name(self) -> str:
        return "test"
    
    @property
    def description(self) -> str:
        return "Test provider for unit testing"
    
    def check_requirements(self) -> None:
        pass
    
    def deploy(self, path: Path, config: Dict[str, Any]) -> None:
        pass
    
    def stop(self, config: Dict[str, Any]) -> None:
        pass
    
    def remove(self, config: Dict[str, Any]) -> None:
        pass


class BrokenProvider(Provider):
    """Provider that doesn't implement required methods for testing."""
    
    @property
    def name(self) -> str:
        return "broken"


class TestBaseProvider:
    """Test the base Provider class functionality."""
    
    def test_provider_interface(self):
        """Test that Provider is properly abstract."""
        # Should not be able to instantiate abstract Provider
        with pytest.raises(TypeError):
            Provider()
    
    def test_test_provider_implementation(self):
        """Test our test provider implementation."""
        provider = TestProvider()
        assert provider.name == "test"
        assert provider.description == "Test provider for unit testing"
        
        # Should not raise any exceptions
        provider.check_requirements()
        provider.deploy(Path("/fake"), {})
        provider.stop({})
        provider.remove({})
    
    def test_broken_provider_instantiation(self):
        """Test that incomplete provider implementations cannot be instantiated."""
        with pytest.raises(TypeError):
            BrokenProvider()
    
    def test_default_description(self):
        """Test the default description property."""
        provider = TestProvider()
        # Override to use default implementation
        provider.__class__.description = Provider.description
        expected = f"{provider.name} provider"
        assert provider.description == expected
    
    def test_validate_config_default(self):
        """Test default validate_config does nothing."""
        provider = TestProvider()
        # Should not raise any exceptions
        provider.validate_config({"test": "config"})
    
    @patch('subprocess.run')
    def test_setup_git_config(self, mock_run):
        """Test Git configuration setup."""
        provider = TestProvider()
        env_vars = {}
        
        # Mock git config responses
        mock_run.side_effect = [
            Mock(returncode=0, stdout="John Doe\n"),  # git config user.name
            Mock(returncode=0, stdout="john@example.com\n")  # git config user.email
        ]
        
        provider._setup_git_config(env_vars)
        
        assert env_vars["GIT_USER_NAME"] == "John Doe"
        assert env_vars["GIT_USER_EMAIL"] == "john@example.com"
        
        # Verify git commands were called
        assert mock_run.call_count == 2
        mock_run.assert_any_call(
            ["git", "config", "user.name"],
            capture_output=True,
            text=True
        )
        mock_run.assert_any_call(
            ["git", "config", "user.email"],
            capture_output=True,
            text=True
        )
    
    @patch('subprocess.run')
    def test_setup_git_config_missing(self, mock_run):
        """Test Git configuration when git config is missing."""
        provider = TestProvider()
        env_vars = {}
        
        # Mock git config failures
        mock_run.side_effect = [
            Mock(returncode=1, stdout=""),  # git config user.name fails
            Mock(returncode=1, stdout="")   # git config user.email fails
        ]
        
        provider._setup_git_config(env_vars)
        
        # No git config should be added
        assert "GIT_USER_NAME" not in env_vars
        assert "GIT_USER_EMAIL" not in env_vars
    
    def test_setup_ssh_key_success(self, temp_project_dir):
        """Test SSH key setup with valid key file."""
        provider = TestProvider()
        env_vars = {}
        
        # Create a fake SSH key file
        ssh_key_path = temp_project_dir / "test_key"
        ssh_key_content = "-----BEGIN OPENSSH PRIVATE KEY-----\nfake_key_content\n-----END OPENSSH PRIVATE KEY-----"
        ssh_key_path.write_text(ssh_key_content)
        
        config = {"ssh_key_path": str(ssh_key_path)}
        
        result = provider._setup_ssh_key(config, env_vars)
        
        assert result is True
        assert env_vars["SSH_PRIVATE_KEY"] == ssh_key_content
    
    def test_setup_ssh_key_missing_file(self):
        """Test SSH key setup with missing key file."""
        provider = TestProvider()
        env_vars = {}
        
        config = {"ssh_key_path": "/nonexistent/key"}
        
        result = provider._setup_ssh_key(config, env_vars)
        
        assert result is False
        assert "SSH_PRIVATE_KEY" not in env_vars
    
    def test_setup_ssh_key_no_config(self):
        """Test SSH key setup with no SSH key in config."""
        provider = TestProvider()
        env_vars = {}
        config = {}
        
        result = provider._setup_ssh_key(config, env_vars)
        
        assert result is False
        assert "SSH_PRIVATE_KEY" not in env_vars
    
    def test_setup_vscode_config_with_extensions(self, temp_project_dir):
        """Test VS Code configuration setup with extensions."""
        provider = TestProvider()
        env_vars = {}
        
        # Create fake settings file
        settings_path = temp_project_dir / "settings.json"
        settings_content = '{"editor.fontSize": 14, "workbench.colorTheme": "Dark"}'
        settings_path.write_text(settings_content)
        
        config = {
            "vscode_config": {
                "copy_extensions": True,
                "copy_settings": True,
                "vscode_extensions_list": ["ms-python.python", "ms-vscode.vscode-json"],
                "vscode_settings_path": str(settings_path)
            }
        }
        
        provider._setup_vscode_config(config, env_vars)
        
        assert env_vars["VSCODE_EXTENSIONS"] == "ms-python.python,ms-vscode.vscode-json"
        assert env_vars["VSCODE_SETTINGS"] == settings_content
    
    def test_setup_vscode_config_no_copy(self):
        """Test VS Code configuration setup when copying is disabled."""
        provider = TestProvider()
        env_vars = {}
        
        config = {
            "vscode_config": {
                "copy_extensions": False,
                "copy_settings": False
            }
        }
        
        provider._setup_vscode_config(config, env_vars)
        
        assert "VSCODE_EXTENSIONS" not in env_vars
        assert "VSCODE_SETTINGS" not in env_vars
    
    def test_setup_cursor_config_with_extensions(self, temp_project_dir):
        """Test Cursor configuration setup with extensions."""
        provider = TestProvider()
        env_vars = {}
        
        # Create fake settings file
        settings_path = temp_project_dir / "settings.json"
        settings_content = '{"cursor.ai.enabled": true, "editor.fontSize": 14}'
        settings_path.write_text(settings_content)
        
        config = {
            "vscode_config": {
                "copy_extensions": True,
                "copy_settings": True,
                "cursor_extensions_list": ["cursor.ai", "ms-python.python"],
                "cursor_settings_path": str(settings_path)
            }
        }
        
        provider._setup_cursor_config(config, env_vars)
        
        assert env_vars["CURSOR_EXTENSIONS"] == "cursor.ai,ms-python.python"
        assert env_vars["CURSOR_SETTINGS"] == settings_content
    
    def test_check_ssh_and_upload_warning_no_ssh_no_upload(self, capsys):
        """Test warning when both SSH and upload are disabled."""
        provider = TestProvider()
        config = {"upload_folder": False}
        
        provider._check_ssh_and_upload_warning(config, has_ssh_key=False)
        
        captured = capsys.readouterr()
        assert "Warning: No SSH key provided and folder upload disabled." in captured.out
        assert "empty workspace and no git access" in captured.out
    
    def test_check_ssh_and_upload_warning_with_ssh(self, capsys):
        """Test no warning when SSH key is available."""
        provider = TestProvider()
        config = {"upload_folder": False}
        
        provider._check_ssh_and_upload_warning(config, has_ssh_key=True)
        
        captured = capsys.readouterr()
        assert "Warning" not in captured.out
    
    def test_check_ssh_and_upload_warning_with_upload(self, capsys):
        """Test no warning when upload is enabled."""
        provider = TestProvider()
        config = {"upload_folder": True}
        
        provider._check_ssh_and_upload_warning(config, has_ssh_key=False)
        
        captured = capsys.readouterr()
        assert "Warning" not in captured.out
    
    @patch('subprocess.run')
    def test_build_environment_vars_complete(self, mock_run, temp_project_dir):
        """Test building environment variables with all options."""
        provider = TestProvider()
        
        # Create SSH key and settings files
        ssh_key_path = temp_project_dir / "ssh_key"
        ssh_key_path.write_text("fake-ssh-key-content")
        
        vscode_settings_path = temp_project_dir / "vscode_settings.json"
        vscode_settings_path.write_text('{"editor.fontSize": 14}')
        
        cursor_settings_path = temp_project_dir / "cursor_settings.json"
        cursor_settings_path.write_text('{"cursor.ai.enabled": true}')
        
        config = {
            "env": {"CUSTOM_VAR": "custom_value"},
            "vscode_password": "test-password",
            "git_repo_url": "git@github.com:test/repo.git",
            "ssh_key_path": str(ssh_key_path),
            "upload_folder": True,
            "vscode_config": {
                "copy_extensions": True,
                "copy_settings": True,
                "vscode_extensions_list": ["ms-python.python"],
                "cursor_extensions_list": ["cursor.ai"],
                "vscode_settings_path": str(vscode_settings_path),
                "cursor_settings_path": str(cursor_settings_path)
            }
        }
        
        # Mock git config
        mock_run.side_effect = [
            Mock(returncode=0, stdout="Test User\n"),
            Mock(returncode=0, stdout="test@example.com\n")
        ]
        
        env_vars = provider.build_environment_vars(config)
        
        # Check all expected environment variables
        assert env_vars["CUSTOM_VAR"] == "custom_value"
        assert env_vars["PASSWORD"] == "test-password"
        assert env_vars["GIT_REPO_URL"] == "git@github.com:test/repo.git"
        assert env_vars["SSH_PRIVATE_KEY"] == "fake-ssh-key-content"
        assert env_vars["GIT_USER_NAME"] == "Test User"
        assert env_vars["GIT_USER_EMAIL"] == "test@example.com"
        assert env_vars["VSCODE_EXTENSIONS"] == "ms-python.python"
        assert env_vars["CURSOR_EXTENSIONS"] == "cursor.ai"
        assert env_vars["VSCODE_SETTINGS"] == '{"editor.fontSize": 14}'
        assert env_vars["CURSOR_SETTINGS"] == '{"cursor.ai.enabled": true}'
        assert "SKIP_GIT_SETUP" not in env_vars
    
    @patch('subprocess.run')
    def test_build_environment_vars_minimal(self, mock_run):
        """Test building environment variables with minimal config."""
        provider = TestProvider()
        
        config = {
            "upload_folder": False
            # No SSH key, no git setup
        }
        
        # Mock git config failures
        mock_run.side_effect = [
            Mock(returncode=1, stdout=""),
            Mock(returncode=1, stdout="")
        ]
        
        env_vars = provider.build_environment_vars(config)
        
        # Should set SKIP_GIT_SETUP when no SSH and no upload
        assert env_vars["SKIP_GIT_SETUP"] == "true"
        assert "SSH_PRIVATE_KEY" not in env_vars
        assert "GIT_REPO_URL" not in env_vars


class TestProviderRegistry:
    """Test the ProviderRegistry class."""
    
    def test_empty_registry(self):
        """Test empty registry initialization."""
        registry = ProviderRegistry()
        assert len(registry) == 0
        assert registry.list_providers() == []
        assert registry.get_provider_info() == {}
    
    def test_register_provider(self):
        """Test registering a provider."""
        registry = ProviderRegistry()
        registry.register(TestProvider)
        
        assert len(registry) == 1
        assert "test" in registry
        assert registry.list_providers() == ["test"]
        
        provider_info = registry.get_provider_info()
        assert provider_info["test"] == "Test provider for unit testing"
    
    def test_register_duplicate_provider(self):
        """Test registering a provider with duplicate name."""
        registry = ProviderRegistry()
        registry.register(TestProvider)
        
        with pytest.raises(ValueError, match="Provider 'test' is already registered"):
            registry.register(TestProvider)
    
    def test_unregister_provider(self):
        """Test unregistering a provider."""
        registry = ProviderRegistry()
        registry.register(TestProvider)
        
        assert "test" in registry
        registry.unregister("test")
        assert "test" not in registry
        assert len(registry) == 0
    
    def test_unregister_nonexistent_provider(self):
        """Test unregistering a provider that doesn't exist."""
        registry = ProviderRegistry()
        
        with pytest.raises(KeyError, match="Provider 'nonexistent' not found"):
            registry.unregister("nonexistent")
    
    def test_get_provider(self):
        """Test getting a provider instance."""
        registry = ProviderRegistry()
        registry.register(TestProvider)
        
        provider = registry.get("test")
        assert isinstance(provider, TestProvider)
        assert provider.name == "test"
    
    def test_get_nonexistent_provider(self):
        """Test getting a provider that doesn't exist."""
        registry = ProviderRegistry()
        registry.register(TestProvider)
        
        with pytest.raises(ValueError, match="Unknown provider 'nonexistent'"):
            registry.get("nonexistent")
    
    def test_get_provider_error_message_includes_available(self):
        """Test that error message includes available providers."""
        registry = ProviderRegistry()
        registry.register(TestProvider)
        
        with pytest.raises(ValueError, match="Available providers: test"):
            registry.get("nonexistent")
    
    def test_multiple_providers(self):
        """Test registry with multiple providers."""
        registry = ProviderRegistry()
        registry.register(LocalProvider)
        registry.register(FlyProvider)
        
        assert len(registry) == 2
        providers = registry.list_providers()
        assert "Local Docker" in providers
        assert "fly.io" in providers
        
        # Should be sorted
        assert providers == sorted(providers)
        
        # Test getting both providers
        local_provider = registry.get("Local Docker")
        assert isinstance(local_provider, LocalProvider)
        
        fly_provider = registry.get("fly.io")
        assert isinstance(fly_provider, FlyProvider)
    
    def test_provider_info_with_multiple_providers(self):
        """Test getting provider info with multiple providers."""
        registry = ProviderRegistry()
        registry.register(LocalProvider)
        registry.register(FlyProvider)
        
        info = registry.get_provider_info()
        assert len(info) == 2
        assert "Local Docker" in info
        assert "fly.io" in info
        assert "Docker" in info["Local Docker"]
        assert "Fly.io" in info["fly.io"]
    
    def test_contains_operator(self):
        """Test the __contains__ operator."""
        registry = ProviderRegistry()
        registry.register(TestProvider)
        
        assert "test" in registry
        assert "nonexistent" not in registry
    
    def test_len_operator(self):
        """Test the __len__ operator."""
        registry = ProviderRegistry()
        assert len(registry) == 0
        
        registry.register(TestProvider)
        assert len(registry) == 1
        
        registry.register(LocalProvider)
        assert len(registry) == 2
        
        registry.unregister("test")
        assert len(registry) == 1 