"""Tests for the main OpenCodeSpace class and CLI interface."""

import pytest
import tempfile
import toml
import subprocess
from unittest.mock import Mock, patch, call, MagicMock
from pathlib import Path
from typing import Dict, Any
import click
from click.testing import CliRunner

from opencodespace.main import OpenCodeSpace, cli, deploy, stop, remove, main
from opencodespace.providers import LocalProvider, FlyProvider


class TestOpenCodeSpace:
    """Test the OpenCodeSpace class."""
    
    def test_initialization(self):
        """Test OpenCodeSpace initialization."""
        ocs = OpenCodeSpace()
        
        # Should have providers registered
        providers = ocs.provider_registry.list_providers()
        assert "Local Docker" in providers
        assert "fly.io" in providers
        assert len(providers) == 2
    
    def test_load_default_config(self):
        """Test loading default configuration."""
        ocs = OpenCodeSpace()
        config = ocs.load_default_config()
        
        # Check default values
        assert config["name"] == ""
        assert config["platform"] == "local"
        assert config["upload_folder"] is True
        assert config["git_branching"] is True
        assert config["api_keys"] == []
        assert config["env"] == {}
        assert isinstance(config["vscode_config"], dict)
        assert config["vscode_config"]["copy_settings"] is False
        assert config["vscode_config"]["copy_extensions"] is False
    
    def test_load_existing_config(self, temp_project_dir, sample_config):
        """Test loading existing configuration."""
        ocs = OpenCodeSpace()
        
        # Create config file
        create_test_config(temp_project_dir, sample_config)
        
        with patch('toml.load', return_value=sample_config):
            config = ocs.load_or_init_config(temp_project_dir, non_interactive=False)
        
        assert config == sample_config
    
    def test_load_or_init_config_non_interactive(self, temp_project_dir):
        """Test config initialization in non-interactive mode."""
        ocs = OpenCodeSpace()
        
        with patch.object(ocs, 'create_default_config') as mock_create_default:
            mock_create_default.return_value = {"platform": "local", "name": "test"}
            
            config = ocs.load_or_init_config(temp_project_dir, non_interactive=True)
            
            mock_create_default.assert_called_once_with(temp_project_dir)
            
            # Config should be saved
            config_path = temp_project_dir / ".opencodespace" / "config.toml"
            assert config_path.exists()
    
    def test_load_or_init_config_interactive(self, temp_project_dir, mock_questionary):
        """Test config initialization in interactive mode."""
        ocs = OpenCodeSpace()
        
        with patch.object(ocs, 'run_interactive_setup') as mock_interactive:
            mock_interactive.return_value = {"platform": "local", "name": "test"}
            
            config = ocs.load_or_init_config(temp_project_dir, non_interactive=False)
            
            mock_interactive.assert_called_once()
            
            # Config should be saved
            config_path = temp_project_dir / ".opencodespace" / "config.toml"
            assert config_path.exists()
    
    def test_create_default_config_with_git(self, temp_project_dir, git_project_dir):
        """Test creating default config with git repository."""
        ocs = OpenCodeSpace()
        
        with patch('subprocess.run') as mock_run:
            mock_run.return_value = Mock(
                returncode=0,
                stdout="git@github.com:test/repo.git\n"
            )
            
            config = ocs.create_default_config(git_project_dir)
            
            assert config["git_repo_url"] == "git@github.com:test/repo.git"
            assert config["platform"] == "local"
            assert config["upload_folder"] is True
    
    def test_create_default_config_no_git(self, temp_project_dir):
        """Test creating default config without git repository."""
        ocs = OpenCodeSpace()
        
        config = ocs.create_default_config(temp_project_dir)
        
        assert "git_repo_url" not in config
        assert config["platform"] == "local"
        assert config["upload_folder"] is True
    
    def test_load_config_missing_file(self, temp_project_dir):
        """Test loading config when file doesn't exist."""
        ocs = OpenCodeSpace()
        
        with pytest.raises(SystemExit):
            ocs.load_config(temp_project_dir)
    
    def test_load_config_success(self, temp_project_dir, sample_config):
        """Test successful config loading."""
        ocs = OpenCodeSpace()
        
        # Create config file
        create_test_config(temp_project_dir, sample_config)
        
        config = ocs.load_config(temp_project_dir)
        assert config["name"] == sample_config["name"]
        assert config["platform"] == sample_config["platform"]
    
    def test_save_config(self, temp_project_dir, sample_config):
        """Test saving configuration."""
        ocs = OpenCodeSpace()
        
        ocs.save_config(temp_project_dir, sample_config)
        
        # Verify config was saved
        config_path = temp_project_dir / ".opencodespace" / "config.toml"
        assert config_path.exists()
        
        saved_config = toml.load(config_path)
        assert saved_config["name"] == sample_config["name"]
    
    def test_print_welcome_box(self, capsys):
        """Test welcome box printing."""
        ocs = OpenCodeSpace()
        ocs.print_welcome_box()
        
        captured = capsys.readouterr()
        assert "Welcome to OpenCodeSpace!" in captured.out
        assert "Version:" in captured.out
        assert "Interactive setup wizard" in captured.out
        assert "╭" in captured.out  # Box drawing characters
        assert "╰" in captured.out
    
    def test_generate_password(self):
        """Test password generation."""
        ocs = OpenCodeSpace()
        
        # Test default length
        password = ocs.generate_password()
        assert len(password) == 12
        assert isinstance(password, str)
        
        # Test custom length
        password_long = ocs.generate_password(20)
        assert len(password_long) == 20
        
        # Test that passwords are different
        password2 = ocs.generate_password()
        assert password != password2
        
        # Test that password contains expected character types
        import string
        allowed_chars = string.ascii_letters + string.digits + "!@#$%^&*"
        for char in password:
            assert char in allowed_chars
    
    def test_detect_git_repo_with_git(self, git_project_dir):
        """Test git repository detection with git repo."""
        ocs = OpenCodeSpace()
        
        with patch('subprocess.run') as mock_run:
            mock_run.return_value = Mock(
                returncode=0,
                stdout="git@github.com:test/repo.git\n"
            )
            
            result = ocs.detect_git_repo(git_project_dir)
            assert result == "git@github.com:test/repo.git"
    
    def test_detect_git_repo_no_git(self, temp_project_dir):
        """Test git repository detection without git repo."""
        ocs = OpenCodeSpace()
        
        result = ocs.detect_git_repo(temp_project_dir)
        assert result is None
    
    def test_detect_git_repo_no_remote(self, temp_project_dir):
        """Test git repository detection with git but no remote."""
        ocs = OpenCodeSpace()
        
        # Create .git directory but simulate no remote
        git_dir = temp_project_dir / ".git"
        git_dir.mkdir()
        
        with patch('subprocess.run') as mock_run:
            mock_run.side_effect = subprocess.CalledProcessError(1, ["git", "remote"])
            
            result = ocs.detect_git_repo(temp_project_dir)
            assert result is None
    
    def test_select_ssh_key_for_git_no_ssh_dir(self, temp_project_dir):
        """Test SSH key selection when no .ssh directory exists."""
        ocs = OpenCodeSpace()
        
        with patch('pathlib.Path.home', return_value=temp_project_dir):
            result = ocs.select_ssh_key_for_git()
            assert result is None
    
    def test_select_ssh_key_for_git_no_keys(self, temp_project_dir):
        """Test SSH key selection when .ssh directory has no keys."""
        ocs = OpenCodeSpace()
        
        # Create empty .ssh directory
        ssh_dir = temp_project_dir / ".ssh"
        ssh_dir.mkdir()
        
        with patch('pathlib.Path.home', return_value=temp_project_dir):
            result = ocs.select_ssh_key_for_git()
            assert result is None
    
    def test_select_ssh_key_for_git_with_keys(self, mock_ssh_dir, mock_questionary):
        """Test SSH key selection with available keys."""
        ocs = OpenCodeSpace()
        
        # Mock user selecting the first key
        mock_questionary['select'].return_value.ask.return_value = "id_rsa"
        
        result = ocs.select_ssh_key_for_git()
        
        assert result is not None
        assert result.name == "id_rsa"
        assert result.exists()
    
    def test_select_ssh_key_for_git_skip(self, mock_ssh_dir, mock_questionary):
        """Test SSH key selection when user chooses to skip."""
        ocs = OpenCodeSpace()
        
        # Mock user selecting "Skip"
        mock_questionary['select'].return_value.ask.return_value = "Skip"
        
        result = ocs.select_ssh_key_for_git()
        assert result is None
    
    def test_detect_vscode_installation(self, mock_vscode_detection):
        """Test VS Code and Cursor installation detection."""
        ocs = OpenCodeSpace()
        
        result = ocs.detect_vscode_installation()
        
        assert isinstance(result, dict)
        assert "vscode" in result
        assert "cursor" in result
        assert result["vscode"] is True
        assert result["cursor"] is True
    
    def test_detect_vscode_installation_none_installed(self):
        """Test detection when no editors are installed."""
        ocs = OpenCodeSpace()
        
        with patch('subprocess.run') as mock_run, \
             patch('pathlib.Path.exists', return_value=False):
            
            # Mock command failures
            mock_run.side_effect = subprocess.CalledProcessError(1, ["command"])
            
            result = ocs.detect_vscode_installation()
            
            assert result["vscode"] is False
            assert result["cursor"] is False
    
    def test_get_editor_settings_paths(self, mock_vscode_detection):
        """Test getting editor settings paths."""
        ocs = OpenCodeSpace()
        
        result = ocs.get_editor_settings_paths()
        
        assert isinstance(result, dict)
        assert "vscode" in result
        assert "cursor" in result
        # Paths should be detected based on mock
        assert result["vscode"] is not None
        assert result["cursor"] is not None
    
    def test_get_editor_extensions(self, mock_vscode_detection):
        """Test getting editor extensions."""
        ocs = OpenCodeSpace()
        
        result = ocs.get_editor_extensions()
        
        assert isinstance(result, dict)
        assert "vscode" in result
        assert "cursor" in result
        assert isinstance(result["vscode"], list)
        assert isinstance(result["cursor"], list)
        assert len(result["vscode"]) > 0
        assert len(result["cursor"]) > 0
    
    def test_get_editor_extensions_no_editors(self):
        """Test getting extensions when no editors are available."""
        ocs = OpenCodeSpace()
        
        with patch('subprocess.run') as mock_run:
            mock_run.side_effect = subprocess.CalledProcessError(1, ["command"])
            
            result = ocs.get_editor_extensions()
            
            assert result["vscode"] == []
            assert result["cursor"] == []
    
    def test_setup_vscode_config_copy_no_editors(self, sample_config):
        """Test VS Code config setup when no editors detected."""
        ocs = OpenCodeSpace()
        
        with patch.object(ocs, 'detect_vscode_installation', return_value={"vscode": False, "cursor": False}):
            result = ocs.setup_vscode_config_copy(sample_config)
            
            # Should return config unchanged
            assert result == sample_config
    
    def test_setup_vscode_config_copy_with_editors(self, sample_config, mock_vscode_detection, mock_questionary):
        """Test VS Code config setup with editors detected."""
        ocs = OpenCodeSpace()
        
        # Mock user confirming all options
        mock_questionary['confirm'].return_value.ask.return_value = True
        
        with patch.object(ocs, 'get_editor_settings_paths') as mock_settings, \
             patch.object(ocs, 'get_editor_extensions') as mock_extensions:
            
            mock_settings.return_value = {
                "vscode": Path("/fake/vscode/settings.json"),
                "cursor": Path("/fake/cursor/settings.json")
            }
            mock_extensions.return_value = {
                "vscode": ["ms-python.python", "ms-vscode.vscode-json"],
                "cursor": ["cursor.ai", "ms-python.python"]
            }
            
            result = ocs.setup_vscode_config_copy(sample_config)
            
            # Should have updated vscode_config
            vscode_config = result["vscode_config"]
            assert vscode_config["copy_settings"] is True
            assert vscode_config["copy_extensions"] is True
            assert vscode_config["detected_editors"] == ["vscode", "cursor"]
    
    def test_setup_vscode_config_copy_user_declines(self, sample_config, mock_vscode_detection, mock_questionary):
        """Test VS Code config setup when user declines."""
        ocs = OpenCodeSpace()
        
        # Mock user declining to copy config
        mock_questionary['confirm'].return_value.ask.return_value = False
        
        result = ocs.setup_vscode_config_copy(sample_config)
        
        # Should return config unchanged
        assert result == sample_config
    
    @patch('opencodespace.main.questionary')
    def test_run_interactive_setup_basic_flow(self, mock_q, temp_project_dir, mock_vscode_detection):
        """Test basic interactive setup flow."""
        ocs = OpenCodeSpace()
        
        # Mock questionary responses
        mock_q.select.return_value.ask.return_value = "local"
        mock_q.confirm.return_value.ask.return_value = False  # Decline all options
        
        config = ocs.load_default_config()
        
        with patch.object(ocs, 'detect_git_repo', return_value=None), \
             patch.object(ocs, 'setup_vscode_config_copy') as mock_vscode_setup:
            
            mock_vscode_setup.return_value = config
            
            result = ocs.run_interactive_setup(temp_project_dir, config)
            
            assert result["platform"] == "local"
            mock_vscode_setup.assert_called_once()
    
    def test_validate_project_path_valid(self, temp_project_dir):
        """Test project path validation with valid path."""
        ocs = OpenCodeSpace()
        
        # Should not raise any exception
        ocs.validate_project_path(temp_project_dir)
    
    def test_validate_project_path_nonexistent(self):
        """Test project path validation with nonexistent path."""
        ocs = OpenCodeSpace()
        
        with pytest.raises(SystemExit):
            ocs.validate_project_path(Path("/nonexistent/path"))
    
    def test_validate_project_path_not_directory(self, temp_project_dir):
        """Test project path validation with file instead of directory."""
        ocs = OpenCodeSpace()
        
        # Create a file
        test_file = temp_project_dir / "testfile.txt"
        test_file.write_text("test")
        
        with pytest.raises(SystemExit):
            ocs.validate_project_path(test_file)
    
    def test_deploy_with_existing_config(self, temp_project_dir, sample_config):
        """Test deploy with existing configuration."""
        ocs = OpenCodeSpace()
        
        # Create config file
        create_test_config(temp_project_dir, sample_config)
        
        with patch.object(ocs, 'load_config', return_value=sample_config) as mock_load, \
             patch.object(ocs, 'save_config') as mock_save:
            
            # Mock provider
            mock_provider = Mock()
            ocs.provider_registry.register = Mock()
            ocs.provider_registry.get = Mock(return_value=mock_provider)
            
            ocs.deploy(temp_project_dir, non_interactive=False, platform=None)
            
            mock_load.assert_called_once_with(temp_project_dir)
            mock_provider.deploy.assert_called_once_with(temp_project_dir, sample_config)
            mock_save.assert_called_once_with(temp_project_dir, sample_config)
    
    def test_deploy_platform_override(self, temp_project_dir, sample_config):
        """Test deploy with platform override."""
        ocs = OpenCodeSpace()
        
        with patch.object(ocs, 'load_or_init_config', return_value=sample_config) as mock_load, \
             patch.object(ocs, 'save_config') as mock_save:
            
            # Mock provider
            mock_provider = Mock()
            ocs.provider_registry.get = Mock(return_value=mock_provider)
            
            ocs.deploy(temp_project_dir, non_interactive=False, platform="fly")
            
            # Platform should be overridden
            assert sample_config["platform"] == "fly"
            mock_provider.deploy.assert_called_once_with(temp_project_dir, sample_config)
    
    def test_stop_command(self, temp_project_dir, sample_config):
        """Test stop command."""
        ocs = OpenCodeSpace()
        
        with patch.object(ocs, 'load_config', return_value=sample_config):
            # Mock provider
            mock_provider = Mock()
            ocs.provider_registry.get = Mock(return_value=mock_provider)
            
            ocs.stop(temp_project_dir)
            
            mock_provider.stop.assert_called_once_with(sample_config)
    
    def test_remove_command(self, temp_project_dir, sample_config):
        """Test remove command."""
        ocs = OpenCodeSpace()
        
        with patch.object(ocs, 'load_config', return_value=sample_config):
            # Mock provider
            mock_provider = Mock()
            ocs.provider_registry.get = Mock(return_value=mock_provider)
            
            ocs.remove(temp_project_dir)
            
            mock_provider.remove.assert_called_once_with(sample_config)
    
    def test_list_providers(self):
        """Test listing providers."""
        ocs = OpenCodeSpace()
        
        providers = ocs.list_providers()
        assert isinstance(providers, list)
        assert "Local Docker" in providers
        assert "fly.io" in providers
    
    def test_get_provider_info(self):
        """Test getting provider info."""
        ocs = OpenCodeSpace()
        
        info = ocs.get_provider_info()
        assert isinstance(info, dict)
        assert "Local Docker" in info
        assert "fly.io" in info
        assert "Docker" in info["Local Docker"]


class TestCLI:
    """Test the CLI interface."""
    
    def test_cli_version(self):
        """Test --version flag."""
        runner = CliRunner()
        result = runner.invoke(cli, ['--version'])
        
        assert result.exit_code == 0
        assert "OpenCodeSpace" in result.output
        assert "0.1.0" in result.output
    
    def test_cli_list_providers(self):
        """Test --list-providers flag."""
        runner = CliRunner()
        result = runner.invoke(cli, ['--list-providers'])
        
        assert result.exit_code == 0
        assert "Available providers:" in result.output
        assert "Local Docker" in result.output
        assert "fly.io" in result.output
    
    def test_cli_deploy_default(self, temp_project_dir):
        """Test deploy command with default arguments."""
        runner = CliRunner()
        
        with patch('opencodespace.main.OpenCodeSpace') as mock_ocs_class:
            mock_ocs = Mock()
            mock_ocs_class.return_value = mock_ocs
            
            result = runner.invoke(deploy, [str(temp_project_dir)])
            
            assert result.exit_code == 0
            mock_ocs.validate_project_path.assert_called_once()
            mock_ocs.deploy.assert_called_once()
    
    def test_cli_deploy_with_platform(self, temp_project_dir):
        """Test deploy command with platform argument."""
        runner = CliRunner()
        
        with patch('opencodespace.main.OpenCodeSpace') as mock_ocs_class:
            mock_ocs = Mock()
            mock_ocs_class.return_value = mock_ocs
            
            result = runner.invoke(deploy, [str(temp_project_dir), '--platform', 'fly'])
            
            assert result.exit_code == 0
            # Check that deploy was called with platform override
            call_args = mock_ocs.deploy.call_args
            assert call_args[0][1] is False  # non_interactive
            assert call_args[0][2] == 'fly'  # platform
    
    def test_cli_deploy_with_yes_flag(self, temp_project_dir):
        """Test deploy command with --yes flag."""
        runner = CliRunner()
        
        with patch('opencodespace.main.OpenCodeSpace') as mock_ocs_class:
            mock_ocs = Mock()
            mock_ocs_class.return_value = mock_ocs
            
            result = runner.invoke(cli, ['--yes', 'deploy', str(temp_project_dir)])
            
            assert result.exit_code == 0
            # Check that deploy was called with non_interactive=True
            call_args = mock_ocs.deploy.call_args
            assert call_args[0][1] is True  # non_interactive
    
    def test_cli_stop_command(self, temp_project_dir):
        """Test stop command."""
        runner = CliRunner()
        
        with patch('opencodespace.main.OpenCodeSpace') as mock_ocs_class:
            mock_ocs = Mock()
            mock_ocs_class.return_value = mock_ocs
            
            result = runner.invoke(stop, [str(temp_project_dir)])
            
            assert result.exit_code == 0
            mock_ocs.validate_project_path.assert_called_once()
            mock_ocs.stop.assert_called_once()
    
    def test_cli_remove_command(self, temp_project_dir):
        """Test remove command."""
        runner = CliRunner()
        
        with patch('opencodespace.main.OpenCodeSpace') as mock_ocs_class:
            mock_ocs = Mock()
            mock_ocs_class.return_value = mock_ocs
            
            result = runner.invoke(remove, [str(temp_project_dir)])
            
            assert result.exit_code == 0
            mock_ocs.validate_project_path.assert_called_once()
            mock_ocs.remove.assert_called_once()
    
    def test_cli_default_command_invokes_deploy(self, temp_project_dir):
        """Test that CLI without subcommand defaults to deploy."""
        runner = CliRunner()
        
        with patch('opencodespace.main.OpenCodeSpace') as mock_ocs_class:
            mock_ocs = Mock()
            mock_ocs_class.return_value = mock_ocs
            
            # Test with current directory
            result = runner.invoke(cli, [])
            
            assert result.exit_code == 0
            mock_ocs.deploy.assert_called_once()
    
    def test_cli_runtime_error_handling(self, temp_project_dir):
        """Test CLI error handling for RuntimeError."""
        runner = CliRunner()
        
        with patch('opencodespace.main.OpenCodeSpace') as mock_ocs_class:
            mock_ocs = Mock()
            mock_ocs.deploy.side_effect = RuntimeError("Test error")
            mock_ocs_class.return_value = mock_ocs
            
            result = runner.invoke(deploy, [str(temp_project_dir)])
            
            assert result.exit_code == 1
            assert "Error: Test error" in result.output
    
    def test_cli_keyboard_interrupt_handling(self, temp_project_dir):
        """Test CLI error handling for KeyboardInterrupt."""
        runner = CliRunner()
        
        with patch('opencodespace.main.OpenCodeSpace') as mock_ocs_class:
            mock_ocs = Mock()
            mock_ocs.deploy.side_effect = KeyboardInterrupt()
            mock_ocs_class.return_value = mock_ocs
            
            result = runner.invoke(deploy, [str(temp_project_dir)])
            
            assert result.exit_code == 130
            assert "Operation cancelled by user" in result.output
    
    def test_cli_unexpected_error_handling(self, temp_project_dir):
        """Test CLI error handling for unexpected exceptions."""
        runner = CliRunner()
        
        with patch('opencodespace.main.OpenCodeSpace') as mock_ocs_class:
            mock_ocs = Mock()
            mock_ocs.deploy.side_effect = ValueError("Unexpected error")
            mock_ocs_class.return_value = mock_ocs
            
            result = runner.invoke(deploy, [str(temp_project_dir)])
            
            assert result.exit_code == 1
            assert "Unexpected error: Unexpected error" in result.output
    
    def test_main_function(self):
        """Test main entry point function."""
        with patch('opencodespace.main.cli') as mock_cli:
            main()
            mock_cli.assert_called_once()


# Helper functions for tests (repeated from conftest.py for clarity)
def create_test_config(project_path: Path, config: Dict[str, Any]) -> Path:
    """Create a test configuration file."""
    config_dir = project_path / ".opencodespace"
    config_dir.mkdir(exist_ok=True)
    config_path = config_dir / "config.toml"
    
    with open(config_path, 'w') as f:
        toml.dump(config, f)
    
    return config_path 