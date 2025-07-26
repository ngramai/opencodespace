"""Integration tests for OpenCodeSpace end-to-end workflows."""

import pytest
import subprocess
import tempfile
import toml
from pathlib import Path
from unittest.mock import Mock, patch, call
from click.testing import CliRunner

from opencodespace.main import OpenCodeSpace, cli
from opencodespace.providers import LocalProvider, FlyProvider


class TestLocalDockerIntegration:
    """Integration tests for the complete Local Docker workflow."""
    
    @patch('subprocess.run')
    @patch('subprocess.call')
    @patch('opencodespace.providers.local.files')
    @patch('opencodespace.providers.local.as_file')
    def test_complete_local_deploy_workflow(self, mock_as_file, mock_files, 
                                           mock_call, mock_run, temp_project_dir):
        """Test complete local deployment workflow from CLI to container running."""
        runner = CliRunner()
        
        # Mock Docker availability
        mock_call.return_value = 0  # Docker is available
        
        # Mock Docker operations
        mock_run.side_effect = [
            Mock(returncode=0, stdout=""),  # docker info (check daemon)
            Mock(returncode=0, stdout=""),  # docker ps (check existing container)
            Mock(returncode=0),  # docker build
            Mock(returncode=0),  # docker run
        ]
        
        # Mock resource files for Docker build
        mock_dockerfile = Mock()
        mock_dockerfile.read_bytes.return_value = b"FROM codercom/code-server:latest\nEXPOSE 8080"
        mock_entrypoint = Mock()
        mock_entrypoint.read_bytes.return_value = b"#!/bin/bash\nexec code-server"
        
        mock_files.return_value.__truediv__.side_effect = lambda x: {
            'Dockerfile': mock_dockerfile,
            'entrypoint.sh': mock_entrypoint
        }[x]
        mock_as_file.return_value.__enter__.side_effect = [mock_dockerfile, mock_entrypoint]
        
        # Run CLI deploy command with --yes flag (non-interactive)
        with patch('time.sleep'):  # Skip the sleep
            result = runner.invoke(cli, ['--yes', 'deploy', str(temp_project_dir), '--platform', 'local'])
        
        assert result.exit_code == 0
        
        # Verify Docker commands were called in correct order
        docker_calls = [call for call in mock_run.call_args_list if call[0][0][0] == 'docker']
        assert len(docker_calls) >= 3  # info, ps, build, run
        
        # Verify config was created
        config_path = temp_project_dir / ".opencodespace" / "config.toml"
        assert config_path.exists()
        
        config = toml.load(config_path)
        assert config["platform"] == "local"
        assert config["name"] == "local"  # Default name for local
    
    @patch('subprocess.run')
    @patch('subprocess.call')
    def test_complete_local_stop_workflow(self, mock_call, mock_run, temp_project_dir, sample_config):
        """Test complete local stop workflow."""
        runner = CliRunner()
        
        # Create config file
        create_test_config(temp_project_dir, sample_config)
        
        # Mock Docker availability and running container
        mock_call.return_value = 0
        mock_run.side_effect = [
            Mock(returncode=0, stdout=""),  # docker info
            Mock(returncode=0, stdout="container123\n"),  # docker ps (container running)
            Mock(returncode=0),  # docker stop
        ]
        
        result = runner.invoke(cli, ['stop', str(temp_project_dir)])
        
        assert result.exit_code == 0
        
        # Verify stop command was called
        stop_calls = [call for call in mock_run.call_args_list 
                     if 'stop' in call[0][0]]
        assert len(stop_calls) == 1
    
    @patch('subprocess.run')
    @patch('subprocess.call')
    def test_complete_local_remove_workflow(self, mock_call, mock_run, temp_project_dir, sample_config):
        """Test complete local remove workflow."""
        runner = CliRunner()
        
        # Create config file
        create_test_config(temp_project_dir, sample_config)
        
        # Mock Docker availability and existing container
        mock_call.return_value = 0
        mock_run.side_effect = [
            Mock(returncode=0, stdout=""),  # docker info
            Mock(returncode=0, stdout="container123\n"),  # docker ps -a
            Mock(returncode=0),  # docker rm
        ]
        
        result = runner.invoke(cli, ['remove', str(temp_project_dir)])
        
        assert result.exit_code == 0
        
        # Verify remove command was called
        rm_calls = [call for call in mock_run.call_args_list 
                   if 'rm' in call[0][0]]
        assert len(rm_calls) == 1


class TestFlyIntegration:
    """Integration tests for the complete Fly.io workflow."""
    
    @patch('subprocess.run')
    @patch('subprocess.call')
    @patch('opencodespace.providers.fly.files')
    @patch('opencodespace.providers.fly.as_file')
    def test_complete_fly_deploy_workflow(self, mock_as_file, mock_files, 
                                         mock_call, mock_run, temp_project_dir):
        """Test complete Fly.io deployment workflow."""
        runner = CliRunner()
        
        # Mock flyctl availability
        mock_call.return_value = 0  # flyctl is available
        
        # Mock flyctl operations
        mock_run.side_effect = [
            Mock(returncode=0),  # flyctl launch
            Mock(returncode=0),  # flyctl secrets set (multiple calls)
            Mock(returncode=0),  # flyctl secrets set
            Mock(returncode=0),  # flyctl deploy
        ]
        
        # Mock resource files
        mock_dockerfile = Mock()
        mock_dockerfile.read_bytes.return_value = b"FROM codercom/code-server:latest"
        mock_entrypoint = Mock()
        mock_entrypoint.read_bytes.return_value = b"#!/bin/bash\nexec code-server"
        mock_fly_toml = Mock()
        mock_fly_toml.read_bytes.return_value = b'app = "test-app"'
        
        mock_files.return_value.__truediv__.side_effect = lambda x: {
            'Dockerfile': mock_dockerfile,
            'entrypoint.sh': mock_entrypoint,
            'fly.toml': mock_fly_toml
        }[x]
        mock_as_file.return_value.__enter__.side_effect = [
            mock_dockerfile, mock_entrypoint, mock_fly_toml
        ]
        
        # Run CLI deploy command
        result = runner.invoke(cli, ['--yes', 'deploy', str(temp_project_dir), '--platform', 'fly'])
        
        assert result.exit_code == 0
        
        # Verify flyctl commands were called
        flyctl_calls = [call for call in mock_run.call_args_list 
                       if call[0][0][0] == 'flyctl']
        assert len(flyctl_calls) >= 2  # launch and deploy (secrets may vary)
        
        # Verify launch command
        launch_calls = [call for call in flyctl_calls if 'launch' in call[0][0]]
        assert len(launch_calls) == 1
        
        # Verify deploy command
        deploy_calls = [call for call in flyctl_calls if 'deploy' in call[0][0]]
        assert len(deploy_calls) == 1
    
    @patch('subprocess.run')
    @patch('subprocess.call')
    def test_complete_fly_stop_workflow(self, mock_call, mock_run, temp_project_dir, fly_config):
        """Test complete Fly.io stop workflow."""
        runner = CliRunner()
        
        # Create config file
        create_test_config(temp_project_dir, fly_config)
        
        # Mock flyctl availability
        mock_call.return_value = 0
        mock_run.return_value = Mock(returncode=0)
        
        result = runner.invoke(cli, ['stop', str(temp_project_dir)])
        
        assert result.exit_code == 0
        
        # Verify scale command was called
        scale_calls = [call for call in mock_run.call_args_list 
                      if 'scale' in call[0][0]]
        assert len(scale_calls) == 1
        assert 'count' in scale_calls[0][0][0]
        assert '0' in scale_calls[0][0][0]
    
    @patch('subprocess.run')
    @patch('subprocess.call')
    def test_complete_fly_remove_workflow(self, mock_call, mock_run, temp_project_dir, fly_config):
        """Test complete Fly.io remove workflow."""
        runner = CliRunner()
        
        # Create config file
        create_test_config(temp_project_dir, fly_config)
        
        # Mock flyctl availability
        mock_call.return_value = 0
        mock_run.return_value = Mock(returncode=0)
        
        result = runner.invoke(cli, ['remove', str(temp_project_dir)])
        
        assert result.exit_code == 0
        
        # Verify destroy command was called
        destroy_calls = [call for call in mock_run.call_args_list 
                        if 'destroy' in call[0][0]]
        assert len(destroy_calls) == 1
        assert '--yes' in destroy_calls[0][0][0]


class TestInteractiveWorkflows:
    """Integration tests for interactive setup workflows."""
    
    @patch('opencodespace.main.questionary')
    @patch('subprocess.run')
    @patch('subprocess.call')
    def test_interactive_setup_with_git_and_editors(self, mock_call, mock_run, mock_q, 
                                                   git_project_dir, mock_vscode_detection):
        """Test interactive setup with git repository and editor detection."""
        runner = CliRunner()
        
        # Mock Docker availability
        mock_call.return_value = 0
        
        # Mock Git operations
        mock_run.side_effect = [
            Mock(returncode=0, stdout="git@github.com:test/repo.git\n"),  # git remote
            Mock(returncode=0, stdout="Test User\n"),  # git config user.name
            Mock(returncode=0, stdout="test@example.com\n"),  # git config user.email
            Mock(returncode=0, stdout=""),  # docker info
            Mock(returncode=0, stdout=""),  # docker ps
            Mock(returncode=0),  # docker build
            Mock(returncode=0),  # docker run
        ]
        
        # Mock questionary responses for interactive setup
        mock_q.select.return_value.ask.side_effect = [
            "local",  # platform selection
            "id_rsa"  # SSH key selection
        ]
        mock_q.confirm.return_value.ask.side_effect = [
            True,   # Clone repository?
            True,   # Copy editor config?
            True,   # Copy VS Code settings?
            True,   # Copy VS Code extensions?
            True,   # Copy Cursor settings?
            True,   # Copy Cursor extensions?
        ]
        
        with patch('opencodespace.providers.local.files') as mock_files, \
             patch('opencodespace.providers.local.as_file') as mock_as_file, \
             patch('pathlib.Path.home') as mock_home, \
             patch('time.sleep'):
            
            # Mock SSH directory
            ssh_dir = git_project_dir / ".ssh"
            ssh_dir.mkdir()
            (ssh_dir / "id_rsa").write_text("fake key")
            mock_home.return_value = git_project_dir
            
            # Mock Docker files
            mock_dockerfile = Mock()
            mock_dockerfile.read_bytes.return_value = b"FROM codercom/code-server:latest"
            mock_entrypoint = Mock()
            mock_entrypoint.read_bytes.return_value = b"#!/bin/bash\nexec code-server"
            
            mock_files.return_value.__truediv__.side_effect = lambda x: {
                'Dockerfile': mock_dockerfile,
                'entrypoint.sh': mock_entrypoint
            }[x]
            mock_as_file.return_value.__enter__.side_effect = [mock_dockerfile, mock_entrypoint]
            
            result = runner.invoke(cli, ['deploy', str(git_project_dir)])
        
        assert result.exit_code == 0
        
        # Verify config was created with correct settings
        config_path = git_project_dir / ".opencodespace" / "config.toml"
        assert config_path.exists()
        
        config = toml.load(config_path)
        assert config["platform"] == "local"
        assert config["git_repo_url"] == "git@github.com:test/repo.git"
        assert config["upload_folder"] is False  # Should be False when cloning
        assert "ssh_key_path" in config
        assert config["vscode_config"]["copy_settings"] is True
        assert config["vscode_config"]["copy_extensions"] is True
    
    @patch('opencodespace.main.questionary')
    @patch('subprocess.run')
    @patch('subprocess.call')
    def test_interactive_setup_decline_all_options(self, mock_call, mock_run, mock_q, temp_project_dir):
        """Test interactive setup when user declines all optional features."""
        runner = CliRunner()
        
        # Mock Docker availability
        mock_call.return_value = 0
        mock_run.side_effect = [
            Mock(returncode=0, stdout=""),  # docker info
            Mock(returncode=0, stdout=""),  # docker ps
            Mock(returncode=0),  # docker build
            Mock(returncode=0),  # docker run
        ]
        
        # Mock questionary responses - decline everything
        mock_q.select.return_value.ask.return_value = "local"
        mock_q.confirm.return_value.ask.return_value = False
        
        with patch('opencodespace.providers.local.files') as mock_files, \
             patch('opencodespace.providers.local.as_file') as mock_as_file, \
             patch('opencodespace.main.OpenCodeSpace.detect_vscode_installation') as mock_detect, \
             patch('time.sleep'):
            
            # Mock no editors detected
            mock_detect.return_value = {"vscode": False, "cursor": False}
            
            # Mock Docker files
            mock_dockerfile = Mock()
            mock_dockerfile.read_bytes.return_value = b"FROM codercom/code-server:latest"
            mock_entrypoint = Mock()
            mock_entrypoint.read_bytes.return_value = b"#!/bin/bash\nexec code-server"
            
            mock_files.return_value.__truediv__.side_effect = lambda x: {
                'Dockerfile': mock_dockerfile,
                'entrypoint.sh': mock_entrypoint
            }[x]
            mock_as_file.return_value.__enter__.side_effect = [mock_dockerfile, mock_entrypoint]
            
            result = runner.invoke(cli, ['deploy', str(temp_project_dir)])
        
        assert result.exit_code == 0
        
        # Verify minimal config was created
        config_path = temp_project_dir / ".opencodespace" / "config.toml"
        assert config_path.exists()
        
        config = toml.load(config_path)
        assert config["platform"] == "local"
        assert config["upload_folder"] is False  # User declined folder upload
        assert "git_repo_url" not in config
        assert "ssh_key_path" not in config


class TestErrorHandlingIntegration:
    """Integration tests for error handling scenarios."""
    
    @patch('subprocess.call')
    def test_docker_not_installed_error(self, mock_call, temp_project_dir):
        """Test error when Docker is not installed."""
        runner = CliRunner()
        
        # Mock Docker not available
        mock_call.return_value = 1  # which docker returns 1
        
        result = runner.invoke(cli, ['--yes', 'deploy', str(temp_project_dir), '--platform', 'local'])
        
        assert result.exit_code == 1
        assert "Docker is not installed" in result.output
    
    @patch('subprocess.run')
    @patch('subprocess.call')
    def test_docker_daemon_not_running_error(self, mock_call, mock_run, temp_project_dir):
        """Test error when Docker daemon is not running."""
        runner = CliRunner()
        
        # Mock Docker installed but daemon not running
        mock_call.return_value = 0  # which docker returns 0
        mock_run.side_effect = subprocess.CalledProcessError(1, ["docker", "info"])
        
        result = runner.invoke(cli, ['--yes', 'deploy', str(temp_project_dir), '--platform', 'local'])
        
        assert result.exit_code == 1
        assert "Docker daemon is not running" in result.output
    
    @patch('subprocess.call')
    def test_flyctl_not_installed_error(self, mock_call, temp_project_dir):
        """Test error when flyctl is not installed."""
        runner = CliRunner()
        
        # Mock flyctl not available
        mock_call.return_value = 1  # which flyctl returns 1
        
        result = runner.invoke(cli, ['--yes', 'deploy', str(temp_project_dir), '--platform', 'fly'])
        
        assert result.exit_code == 1
        assert "flyctl is not installed" in result.output
    
    def test_invalid_project_path_error(self):
        """Test error with invalid project path."""
        runner = CliRunner()
        
        result = runner.invoke(cli, ['deploy', '/nonexistent/path'])
        
        assert result.exit_code == 1
        assert "Directory does not exist" in result.output
    
    def test_missing_config_error(self, temp_project_dir):
        """Test error when trying to stop/remove without config."""
        runner = CliRunner()
        
        result = runner.invoke(cli, ['stop', str(temp_project_dir)])
        
        assert result.exit_code == 1
        assert "No .opencodespace/config.toml found" in result.output


class TestConfigurationPersistence:
    """Integration tests for configuration file persistence and loading."""
    
    def test_config_persistence_across_commands(self, temp_project_dir, sample_config, mock_docker):
        """Test that configuration persists correctly across commands."""
        runner = CliRunner()
        mock_run, mock_call = mock_docker
        
        # Create initial config
        create_test_config(temp_project_dir, sample_config)
        
        # Mock successful Docker operations
        mock_run.side_effect = [
            Mock(returncode=0, stdout=""),  # docker info
            Mock(returncode=0, stdout="container123\n"),  # docker ps
            Mock(returncode=0),  # docker stop
        ]
        
        # Run stop command
        result = runner.invoke(cli, ['stop', str(temp_project_dir)])
        assert result.exit_code == 0
        
        # Verify config still exists and is unchanged
        config_path = temp_project_dir / ".opencodespace" / "config.toml"
        assert config_path.exists()
        
        loaded_config = toml.load(config_path)
        assert loaded_config["name"] == sample_config["name"]
        assert loaded_config["platform"] == sample_config["platform"]
    
    @patch('subprocess.run')
    @patch('subprocess.call')
    @patch('opencodespace.providers.local.files')
    @patch('opencodespace.providers.local.as_file')
    def test_config_update_during_deploy(self, mock_as_file, mock_files, mock_call, mock_run, temp_project_dir):
        """Test that configuration is updated correctly during deployment."""
        runner = CliRunner()
        
        # Mock Docker availability
        mock_call.return_value = 0
        mock_run.side_effect = [
            Mock(returncode=0, stdout=""),  # docker info
            Mock(returncode=0, stdout=""),  # docker ps
            Mock(returncode=0),  # docker build
            Mock(returncode=0),  # docker run
        ]
        
        # Mock resource files
        mock_dockerfile = Mock()
        mock_dockerfile.read_bytes.return_value = b"FROM codercom/code-server:latest"
        mock_entrypoint = Mock()
        mock_entrypoint.read_bytes.return_value = b"#!/bin/bash\nexec code-server"
        
        mock_files.return_value.__truediv__.side_effect = lambda x: {
            'Dockerfile': mock_dockerfile,
            'entrypoint.sh': mock_entrypoint
        }[x]
        mock_as_file.return_value.__enter__.side_effect = [mock_dockerfile, mock_entrypoint]
        
        # Deploy without existing config
        with patch('time.sleep'):
            result = runner.invoke(cli, ['--yes', 'deploy', str(temp_project_dir)])
        
        assert result.exit_code == 0
        
        # Verify config was created and contains expected values
        config_path = temp_project_dir / ".opencodespace" / "config.toml"
        assert config_path.exists()
        
        config = toml.load(config_path)
        assert config["platform"] == "local"
        assert config["name"] == "local"  # Should be auto-generated


class TestPlatformSwitching:
    """Integration tests for switching between platforms."""
    
    @patch('subprocess.run')
    @patch('subprocess.call')
    @patch('opencodespace.providers.local.files')
    @patch('opencodespace.providers.local.as_file')
    def test_platform_override_with_existing_config(self, mock_as_file, mock_files, mock_call, mock_run, 
                                                   temp_project_dir, fly_config):
        """Test overriding platform when config exists for different platform."""
        runner = CliRunner()
        
        # Create config for Fly.io
        create_test_config(temp_project_dir, fly_config)
        
        # Mock Docker availability
        mock_call.return_value = 0
        mock_run.side_effect = [
            Mock(returncode=0, stdout=""),  # docker info
            Mock(returncode=0, stdout=""),  # docker ps
            Mock(returncode=0),  # docker build
            Mock(returncode=0),  # docker run
        ]
        
        # Mock resource files
        mock_dockerfile = Mock()
        mock_dockerfile.read_bytes.return_value = b"FROM codercom/code-server:latest"
        mock_entrypoint = Mock()
        mock_entrypoint.read_bytes.return_value = b"#!/bin/bash\nexec code-server"
        
        mock_files.return_value.__truediv__.side_effect = lambda x: {
            'Dockerfile': mock_dockerfile,
            'entrypoint.sh': mock_entrypoint
        }[x]
        mock_as_file.return_value.__enter__.side_effect = [mock_dockerfile, mock_entrypoint]
        
        # Deploy with platform override to local
        with patch('time.sleep'):
            result = runner.invoke(cli, ['deploy', str(temp_project_dir), '--platform', 'local'])
        
        assert result.exit_code == 0
        
        # Verify config was updated to use local platform
        config_path = temp_project_dir / ".opencodespace" / "config.toml"
        updated_config = toml.load(config_path)
        assert updated_config["platform"] == "local"
        # Other settings should be preserved
        assert updated_config["name"] == fly_config["name"]


# Helper function for integration tests
def create_test_config(project_path: Path, config: dict) -> Path:
    """Create a test configuration file."""
    config_dir = project_path / ".opencodespace"
    config_dir.mkdir(exist_ok=True)
    config_path = config_dir / "config.toml"
    
    with open(config_path, 'w') as f:
        toml.dump(config, f)
    
    return config_path 