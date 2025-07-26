"""Tests for the Local Docker provider."""

import pytest
from unittest.mock import Mock, patch, call
from pathlib import Path
import subprocess
from typing import Dict, Any

from opencodespace.providers.local import LocalProvider


class TestLocalProvider:
    """Test the LocalProvider class."""
    
    def test_provider_properties(self):
        """Test provider name and description."""
        provider = LocalProvider()
        assert provider.name == "Local Docker"
        assert provider.description == "Run development environment locally with Docker"
    
    @patch('subprocess.call')
    def test_check_requirements_docker_not_installed(self, mock_call):
        """Test check_requirements when Docker is not installed."""
        provider = LocalProvider()
        mock_call.return_value = 1  # which docker returns 1 (not found)
        
        with pytest.raises(RuntimeError, match="Docker is not installed"):
            provider.check_requirements()
    
    @patch('subprocess.run')
    @patch('subprocess.call')
    def test_check_requirements_docker_not_running(self, mock_call, mock_run):
        """Test check_requirements when Docker daemon is not running."""
        provider = LocalProvider()
        mock_call.return_value = 0  # which docker returns 0 (found)
        mock_run.side_effect = subprocess.CalledProcessError(1, ["docker", "info"])
        
        with pytest.raises(RuntimeError, match="Docker daemon is not running"):
            provider.check_requirements()
    
    @patch('subprocess.run')
    @patch('subprocess.call')
    def test_check_requirements_success(self, mock_call, mock_run):
        """Test successful requirements check."""
        provider = LocalProvider()
        mock_call.return_value = 0  # which docker returns 0
        mock_run.return_value = Mock()  # docker info succeeds
        
        # Should not raise any exception
        provider.check_requirements()
    
    def test_validate_config_valid_port(self):
        """Test config validation with valid port."""
        provider = LocalProvider()
        config = {"port": 8080}
        
        # Should not raise any exception
        provider.validate_config(config)
    
    def test_validate_config_invalid_port(self):
        """Test config validation with invalid port."""
        provider = LocalProvider()
        
        # Test invalid port types and values
        invalid_configs = [
            {"port": "invalid"},
            {"port": 0},
            {"port": -1},
            {"port": 70000},
            {"port": 1.5}
        ]
        
        for config in invalid_configs:
            with pytest.raises(ValueError, match="Port must be a valid number"):
                provider.validate_config(config)
    
    def test_validate_config_no_port(self):
        """Test config validation without port (should use default)."""
        provider = LocalProvider()
        config = {}
        
        # Should not raise any exception
        provider.validate_config(config)
    
    def test_get_container_name_with_name(self):
        """Test container name generation with explicit name."""
        provider = LocalProvider()
        config = {"name": "my-project"}
        
        result = provider._get_container_name(config)
        assert result == "opencodespace-my-project"
    
    def test_get_container_name_without_name(self):
        """Test container name generation without explicit name."""
        provider = LocalProvider()
        config = {}
        
        result = provider._get_container_name(config)
        assert result == "opencodespace-local"
    
    @patch('opencodespace.providers.local.files')
    @patch('opencodespace.providers.local.as_file')
    def test_build_docker_image_success(self, mock_as_file, mock_files, temp_project_dir):
        """Test successful Docker image building."""
        provider = LocalProvider()
        
        # Mock the resource files
        mock_dockerfile = Mock()
        mock_dockerfile.read_bytes.return_value = b"FROM codercom/code-server:latest\nEXPOSE 8080"
        
        mock_entrypoint = Mock()
        mock_entrypoint.read_bytes.return_value = b"#!/bin/bash\nexec code-server"
        
        mock_files.return_value.__truediv__.side_effect = lambda x: {
            'Dockerfile': mock_dockerfile,
            'entrypoint.sh': mock_entrypoint
        }[x]
        
        mock_as_file.return_value.__enter__.side_effect = [mock_dockerfile, mock_entrypoint]
        
        with patch('subprocess.run') as mock_run:
            mock_run.return_value = Mock(returncode=0)
            
            result = provider._build_docker_image(temp_project_dir)
            
            assert result == "opencodespace:latest"
            
            # Check that .opencodespace directory was created
            opencodespace_dir = temp_project_dir / ".opencodespace"
            assert opencodespace_dir.exists()
            
            # Check that Dockerfile was created
            dockerfile_path = opencodespace_dir / "Dockerfile"
            assert dockerfile_path.exists()
            
            # Check that entrypoint.sh was created and made executable
            entrypoint_path = opencodespace_dir / "entrypoint.sh"
            assert entrypoint_path.exists()
            assert entrypoint_path.stat().st_mode & 0o111  # Check executable bit
            
            # Verify docker build command was called
            mock_run.assert_called_once_with([
                "docker", "build", "-t", "opencodespace:latest", 
                "-f", str(dockerfile_path), str(temp_project_dir)
            ], check=True)
    
    @patch('opencodespace.providers.local.files')
    @patch('opencodespace.providers.local.as_file')
    def test_build_docker_image_build_failure(self, mock_as_file, mock_files, temp_project_dir):
        """Test Docker image build failure."""
        provider = LocalProvider()
        
        # Mock the resource files
        mock_dockerfile = Mock()
        mock_dockerfile.read_bytes.return_value = b"FROM codercom/code-server:latest"
        
        mock_entrypoint = Mock()
        mock_entrypoint.read_bytes.return_value = b"#!/bin/bash\nexec code-server"
        
        mock_files.return_value.__truediv__.side_effect = lambda x: {
            'Dockerfile': mock_dockerfile,
            'entrypoint.sh': mock_entrypoint
        }[x]
        
        mock_as_file.return_value.__enter__.side_effect = [mock_dockerfile, mock_entrypoint]
        
        with patch('subprocess.run') as mock_run:
            mock_run.side_effect = subprocess.CalledProcessError(1, ["docker", "build"])
            
            with pytest.raises(RuntimeError, match="Failed to build Docker image"):
                provider._build_docker_image(temp_project_dir)
    
    @patch('opencodespace.providers.local.files')
    @patch('opencodespace.providers.local.as_file')
    def test_build_docker_image_existing_files(self, mock_as_file, mock_files, temp_project_dir):
        """Test Docker image building when files already exist."""
        provider = LocalProvider()
        
        # Create existing .opencodespace directory and files
        opencodespace_dir = temp_project_dir / ".opencodespace"
        opencodespace_dir.mkdir()
        dockerfile_path = opencodespace_dir / "Dockerfile"
        dockerfile_path.write_text("existing dockerfile")
        entrypoint_path = opencodespace_dir / "entrypoint.sh"
        entrypoint_path.write_text("existing entrypoint")
        
        # Mock the resource files (should not be copied since files exist)
        mock_dockerfile = Mock()
        mock_dockerfile.read_bytes.return_value = b"FROM codercom/code-server:latest"
        
        mock_entrypoint = Mock()
        mock_entrypoint.read_bytes.return_value = b"#!/bin/bash\nexec code-server"
        
        mock_files.return_value.__truediv__.side_effect = lambda x: {
            'Dockerfile': mock_dockerfile,
            'entrypoint.sh': mock_entrypoint
        }[x]
        
        mock_as_file.return_value.__enter__.side_effect = [mock_dockerfile, mock_entrypoint]
        
        with patch('subprocess.run') as mock_run:
            mock_run.return_value = Mock(returncode=0)
            
            result = provider._build_docker_image(temp_project_dir)
            
            assert result == "opencodespace:latest"
            
            # Files should not have been overwritten
            assert dockerfile_path.read_text() == "existing dockerfile"
            assert entrypoint_path.read_text() == "existing entrypoint"
    
    @patch.object(LocalProvider, '_build_docker_image')
    @patch.object(LocalProvider, 'build_environment_vars')
    def test_build_docker_command_basic(self, mock_env_vars, mock_build_image, temp_project_dir):
        """Test building basic Docker command."""
        provider = LocalProvider()
        mock_build_image.return_value = "opencodespace:latest"
        mock_env_vars.return_value = {"TEST_VAR": "test_value"}
        
        config = {
            "name": "test-project",
            "upload_folder": True
        }
        
        result = provider._build_docker_command(temp_project_dir, config)
        
        expected = [
            "docker", "run",
            "--rm",
            "-d",
            "-p", "8080:8080",
            "--name", "opencodespace-test-project",
            "-e", "TEST_VAR=test_value",
            "-v", f"{str(temp_project_dir)}:/home/coder/workspace",
            "opencodespace:latest"
        ]
        
        assert result == expected
        mock_build_image.assert_called_once_with(temp_project_dir)
        mock_env_vars.assert_called_once_with(config)
    
    @patch.object(LocalProvider, '_build_docker_image')
    @patch.object(LocalProvider, 'build_environment_vars')
    def test_build_docker_command_custom_port(self, mock_env_vars, mock_build_image, temp_project_dir):
        """Test building Docker command with custom port."""
        provider = LocalProvider()
        mock_build_image.return_value = "opencodespace:latest"
        mock_env_vars.return_value = {}
        
        config = {
            "name": "test-project",
            "port": 9090,
            "upload_folder": False  # No volume mount
        }
        
        result = provider._build_docker_command(temp_project_dir, config)
        
        expected = [
            "docker", "run",
            "--rm",
            "-d",
            "-p", "9090:9090",
            "--name", "opencodespace-test-project",
            "opencodespace:latest"
        ]
        
        assert result == expected
    
    @patch.object(LocalProvider, '_build_docker_command')
    @patch.object(LocalProvider, 'check_requirements')
    @patch.object(LocalProvider, 'validate_config')
    def test_deploy_success(self, mock_validate, mock_check_req, mock_build_cmd, temp_project_dir):
        """Test successful deployment."""
        provider = LocalProvider()
        
        config = {"name": "test-project"}
        mock_build_cmd.return_value = ["docker", "run", "--name", "opencodespace-test-project", "image"]
        
        with patch('subprocess.run') as mock_run, \
             patch('time.sleep'):  # Skip the sleep
            
            # Mock container check (no existing container)
            mock_run.side_effect = [
                Mock(returncode=0, stdout=""),  # No existing container
                Mock(returncode=0)  # Successful docker run
            ]
            
            provider.deploy(temp_project_dir, config)
            
            mock_check_req.assert_called_once()
            mock_validate.assert_called_once_with(config)
            mock_build_cmd.assert_called_once_with(temp_project_dir, config)
            
            # Verify docker commands were called
            assert mock_run.call_count == 2
    
    @patch.object(LocalProvider, 'check_requirements')
    def test_deploy_existing_container(self, mock_check_req, temp_project_dir):
        """Test deployment when container already exists."""
        provider = LocalProvider()
        config = {"name": "test-project"}
        
        with patch('subprocess.run') as mock_run, \
             patch.object(provider, '_build_docker_command') as mock_build_cmd, \
             patch('time.sleep'):
            
            mock_build_cmd.return_value = ["docker", "run", "image"]
            
            # Mock existing container found and removal
            mock_run.side_effect = [
                Mock(returncode=0, stdout="container123\n"),  # Existing container found
                Mock(returncode=0),  # Successful removal
                Mock(returncode=0)   # Successful new container start
            ]
            
            provider.deploy(temp_project_dir, config)
            
            # Should call docker ps, docker rm, and docker run
            assert mock_run.call_count == 3
            
            # Check that docker rm was called
            remove_call = mock_run.call_args_list[1]
            assert "rm" in remove_call[0][0]
            assert "opencodespace-test-project" in remove_call[0][0]
    
    @patch.object(LocalProvider, 'check_requirements')
    def test_deploy_docker_run_failure(self, mock_check_req, temp_project_dir):
        """Test deployment failure when docker run fails."""
        provider = LocalProvider()
        config = {"name": "test-project"}
        
        with patch('subprocess.run') as mock_run, \
             patch.object(provider, '_build_docker_command') as mock_build_cmd:
            
            mock_build_cmd.return_value = ["docker", "run", "image"]
            
            # Mock docker run failure
            mock_run.side_effect = [
                Mock(returncode=0, stdout=""),  # No existing container
                subprocess.CalledProcessError(1, ["docker", "run"])  # Docker run fails
            ]
            
            with pytest.raises(RuntimeError, match="Docker container failed to start"):
                provider.deploy(temp_project_dir, config)
    
    @patch.object(LocalProvider, 'check_requirements')
    def test_deploy_generates_name_if_missing(self, mock_check_req, temp_project_dir):
        """Test that deployment generates name if not provided."""
        provider = LocalProvider()
        config = {}  # No name provided
        
        with patch('subprocess.run') as mock_run, \
             patch.object(provider, '_build_docker_command') as mock_build_cmd, \
             patch('time.sleep'):
            
            mock_build_cmd.return_value = ["docker", "run", "image"]
            mock_run.side_effect = [
                Mock(returncode=0, stdout=""),  # No existing container
                Mock(returncode=0)  # Successful docker run
            ]
            
            provider.deploy(temp_project_dir, config)
            
            # Name should be set to default
            assert config["name"] == "local"
    
    @patch.object(LocalProvider, 'check_requirements')
    def test_stop_success(self, mock_check_req):
        """Test successful container stop."""
        provider = LocalProvider()
        config = {"name": "test-project"}
        
        with patch('subprocess.run') as mock_run:
            # Mock running container found
            mock_run.side_effect = [
                Mock(returncode=0, stdout="container123\n"),  # Container is running
                Mock(returncode=0)  # Successful stop
            ]
            
            provider.stop(config)
            
            mock_check_req.assert_called_once()
            
            # Should call docker ps and docker stop
            assert mock_run.call_count == 2
            
            # Check docker stop command
            stop_call = mock_run.call_args_list[1]
            assert stop_call[0][0] == ["docker", "stop", "opencodespace-test-project"]
    
    @patch.object(LocalProvider, 'check_requirements')
    def test_stop_container_not_running(self, mock_check_req):
        """Test stop when container is not running."""
        provider = LocalProvider()
        config = {"name": "test-project"}
        
        with patch('subprocess.run') as mock_run:
            # Mock no running container found
            mock_run.return_value = Mock(returncode=0, stdout="")
            
            provider.stop(config)
            
            mock_check_req.assert_called_once()
            
            # Should only call docker ps, not docker stop
            assert mock_run.call_count == 1
    
    @patch.object(LocalProvider, 'check_requirements')
    def test_stop_docker_failure(self, mock_check_req):
        """Test stop when docker stop fails."""
        provider = LocalProvider()
        config = {"name": "test-project"}
        
        with patch('subprocess.run') as mock_run:
            mock_run.side_effect = [
                Mock(returncode=0, stdout="container123\n"),  # Container is running
                subprocess.CalledProcessError(1, ["docker", "stop"])  # Stop fails
            ]
            
            with pytest.raises(RuntimeError, match="Failed to stop container"):
                provider.stop(config)
    
    @patch.object(LocalProvider, 'check_requirements')
    def test_stop_generates_name_if_missing(self, mock_check_req):
        """Test that stop generates name if not provided."""
        provider = LocalProvider()
        config = {}  # No name provided
        
        with patch('subprocess.run') as mock_run:
            mock_run.return_value = Mock(returncode=0, stdout="")
            
            provider.stop(config)
            
            # Name should be set to default
            assert config["name"] == "local"
    
    @patch.object(LocalProvider, 'check_requirements')
    def test_remove_success(self, mock_check_req):
        """Test successful container removal."""
        provider = LocalProvider()
        config = {"name": "test-project"}
        
        with patch('subprocess.run') as mock_run:
            # Mock container exists
            mock_run.side_effect = [
                Mock(returncode=0, stdout="container123\n"),  # Container exists
                Mock(returncode=0)  # Successful removal
            ]
            
            provider.remove(config)
            
            mock_check_req.assert_called_once()
            
            # Should call docker ps and docker rm
            assert mock_run.call_count == 2
            
            # Check docker rm command
            rm_call = mock_run.call_args_list[1]
            assert rm_call[0][0] == ["docker", "rm", "-f", "opencodespace-test-project"]
    
    @patch.object(LocalProvider, 'check_requirements')
    def test_remove_container_not_exists(self, mock_check_req):
        """Test remove when container doesn't exist."""
        provider = LocalProvider()
        config = {"name": "test-project"}
        
        with patch('subprocess.run') as mock_run:
            # Mock no container found
            mock_run.return_value = Mock(returncode=0, stdout="")
            
            provider.remove(config)
            
            mock_check_req.assert_called_once()
            
            # Should only call docker ps, not docker rm
            assert mock_run.call_count == 1
    
    @patch.object(LocalProvider, 'check_requirements')
    def test_remove_docker_failure(self, mock_check_req):
        """Test remove when docker rm fails."""
        provider = LocalProvider()
        config = {"name": "test-project"}
        
        with patch('subprocess.run') as mock_run:
            mock_run.side_effect = [
                Mock(returncode=0, stdout="container123\n"),  # Container exists
                subprocess.CalledProcessError(1, ["docker", "rm"])  # Remove fails
            ]
            
            with pytest.raises(RuntimeError, match="Failed to remove container"):
                provider.remove(config)
    
    @patch.object(LocalProvider, 'check_requirements')
    def test_remove_generates_name_if_missing(self, mock_check_req):
        """Test that remove generates name if not provided."""
        provider = LocalProvider()
        config = {}  # No name provided
        
        with patch('subprocess.run') as mock_run:
            mock_run.return_value = Mock(returncode=0, stdout="")
            
            provider.remove(config)
            
            # Name should be set to default
            assert config["name"] == "local" 