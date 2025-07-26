"""Tests for the Fly.io provider."""

import pytest
from unittest.mock import Mock, patch, call
from pathlib import Path
import subprocess
import shutil
from typing import Dict, Any

from opencodespace.providers.fly import FlyProvider


class TestFlyProvider:
    """Test the FlyProvider class."""
    
    def test_provider_properties(self):
        """Test provider name and description."""
        provider = FlyProvider()
        assert provider.name == "fly.io"
        assert provider.description == "Deploy to Fly.io global application platform"
    
    def test_generate_app_name(self):
        """Test app name generation."""
        provider = FlyProvider()
        
        # Generate multiple names to test format
        for _ in range(10):
            name = provider.generate_app_name()
            
            # Should have format: word-word-number
            parts = name.split('-')
            assert len(parts) == 3
            
            # First two parts should be words from the lists
            assert parts[0] in provider.ADJECTIVES
            assert parts[1] in provider.NOUNS
            
            # Third part should be a number
            assert parts[2].isdigit()
            number = int(parts[2])
            assert 100 <= number <= 9999
    
    @patch('subprocess.call')
    def test_check_requirements_flyctl_not_installed(self, mock_call):
        """Test check_requirements when flyctl is not installed."""
        provider = FlyProvider()
        mock_call.return_value = 1  # which flyctl returns 1 (not found)
        
        with pytest.raises(RuntimeError, match="flyctl is not installed"):
            provider.check_requirements()
    
    @patch('subprocess.call')
    def test_check_requirements_success(self, mock_call):
        """Test successful requirements check."""
        provider = FlyProvider()
        mock_call.return_value = 0  # which flyctl returns 0
        
        # Should not raise any exception
        provider.check_requirements()
    
    def test_validate_config_generates_name(self):
        """Test config validation generates app name if missing."""
        provider = FlyProvider()
        config = {}
        
        provider.validate_config(config)
        
        # Name should be generated
        assert "name" in config
        assert isinstance(config["name"], str)
        assert len(config["name"]) > 0
        
        # Should have valid format
        parts = config["name"].split('-')
        assert len(parts) == 3
    
    def test_validate_config_keeps_existing_name(self):
        """Test config validation keeps existing valid name."""
        provider = FlyProvider()
        original_name = "my-test-app-123"
        config = {"name": original_name}
        
        provider.validate_config(config)
        
        # Name should remain unchanged
        assert config["name"] == original_name
    
    def test_validate_config_invalid_name_characters(self):
        """Test config validation with invalid characters in name."""
        provider = FlyProvider()
        
        invalid_names = [
            "app_with_underscores",
            "app with spaces",
            "app@with.special!chars",
            "app/with/slashes"
        ]
        
        for invalid_name in invalid_names:
            config = {"name": invalid_name}
            with pytest.raises(ValueError, match="must contain only letters, numbers, and hyphens"):
                provider.validate_config(config)
    
    def test_validate_config_name_too_long(self):
        """Test config validation with name that's too long."""
        provider = FlyProvider()
        config = {"name": "a" * 31}  # 31 characters, exceeds 30 limit
        
        with pytest.raises(ValueError, match="must be 30 characters or less"):
            provider.validate_config(config)
    
    def test_validate_config_valid_name_edge_cases(self):
        """Test config validation with valid edge case names."""
        provider = FlyProvider()
        
        valid_names = [
            "a",  # Single character
            "a" * 30,  # Exactly 30 characters
            "app-123",  # With hyphens and numbers
            "123-app-456"  # Starting with numbers
        ]
        
        for valid_name in valid_names:
            config = {"name": valid_name}
            provider.validate_config(config)  # Should not raise
            assert config["name"] == valid_name
    
    @patch('opencodespace.providers.fly.files')
    @patch('opencodespace.providers.fly.as_file')
    def test_copy_deployment_files_success(self, mock_as_file, mock_files, temp_project_dir):
        """Test successful copying of deployment files."""
        provider = FlyProvider()
        
        # Mock the resource files
        mock_dockerfile = Mock()
        mock_dockerfile.read_bytes.return_value = b"FROM codercom/code-server:latest\nEXPOSE 8080"
        
        mock_entrypoint = Mock()
        mock_entrypoint.read_bytes.return_value = b"#!/bin/bash\nexec code-server --bind-addr 0.0.0.0:8080"
        
        mock_fly_toml = Mock()
        mock_fly_toml.read_bytes.return_value = b'app = "test-app"\nprimary_region = "ord"'
        
        def mock_files_side_effect(resource_name):
            return {
                'Dockerfile': mock_dockerfile,
                'entrypoint.sh': mock_entrypoint,
                'fly.toml': mock_fly_toml
            }[resource_name]
        
        mock_files.return_value.__truediv__.side_effect = mock_files_side_effect
        mock_as_file.return_value.__enter__.side_effect = [
            mock_dockerfile, mock_entrypoint, mock_fly_toml
        ]
        
        provider._copy_deployment_files(temp_project_dir)
        
        # Check that .opencodespace directory was created
        opencodespace_dir = temp_project_dir / ".opencodespace"
        assert opencodespace_dir.exists()
        
        # Check that files were created
        dockerfile_path = opencodespace_dir / "Dockerfile"
        assert dockerfile_path.exists()
        
        entrypoint_path = opencodespace_dir / "entrypoint.sh"
        assert entrypoint_path.exists()
        assert entrypoint_path.stat().st_mode & 0o111  # Check executable bit
        
        # Check that fly.toml was copied to root
        fly_toml_path = temp_project_dir / "fly.toml"
        assert fly_toml_path.exists()
    
    @patch('opencodespace.providers.fly.files')
    @patch('opencodespace.providers.fly.as_file')
    def test_copy_deployment_files_missing_resource(self, mock_as_file, mock_files, temp_project_dir, capsys):
        """Test copying deployment files when some resources are missing."""
        provider = FlyProvider()
        
        # Mock only some resource files
        mock_dockerfile = Mock()
        mock_dockerfile.read_bytes.return_value = b"FROM codercom/code-server:latest"
        
        def mock_files_side_effect(resource_name):
            if resource_name == 'Dockerfile':
                return mock_dockerfile
            else:
                raise FileNotFoundError(f"{resource_name} not found")
        
        mock_files.return_value.__truediv__.side_effect = mock_files_side_effect
        mock_as_file.return_value.__enter__.return_value = mock_dockerfile
        
        provider._copy_deployment_files(temp_project_dir)
        
        # Should print warnings for missing files
        captured = capsys.readouterr()
        assert "Warning" in captured.out
        assert "entrypoint.sh not found" in captured.out
        assert "fly.toml not found" in captured.out
    
    def test_set_fly_secrets_with_env_vars(self, temp_project_dir):
        """Test setting Fly.io secrets with environment variables."""
        provider = FlyProvider()
        
        env_vars = {
            "PASSWORD": "test-password",
            "OPENAI_API_KEY": "sk-test-key",
            "GIT_REPO_URL": "git@github.com:test/repo.git"
        }
        
        with patch('subprocess.run') as mock_run:
            mock_run.return_value = Mock(returncode=0)
            
            provider._set_fly_secrets(temp_project_dir, env_vars)
            
            # Should call flyctl secrets set for each environment variable
            assert mock_run.call_count == 3
            
            # Check that each secret was set correctly
            calls = mock_run.call_args_list
            expected_secrets = [
                "PASSWORD=test-password",
                "OPENAI_API_KEY=sk-test-key",
                "GIT_REPO_URL=git@github.com:test/repo.git"
            ]
            
            for call_args, expected_secret in zip(calls, expected_secrets):
                assert call_args[0][0] == ["flyctl", "secrets", "set", expected_secret]
                assert call_args[1]["cwd"] == temp_project_dir
                assert call_args[1]["check"] is True
                assert call_args[1]["capture_output"] is True  # Hide sensitive output
    
    def test_set_fly_secrets_empty_env_vars(self, temp_project_dir):
        """Test setting Fly.io secrets with no environment variables."""
        provider = FlyProvider()
        
        with patch('subprocess.run') as mock_run:
            provider._set_fly_secrets(temp_project_dir, {})
            
            # Should not call flyctl at all
            mock_run.assert_not_called()
    
    def test_cleanup_deployment_files(self, temp_project_dir):
        """Test cleanup of deployment files."""
        provider = FlyProvider()
        
        # Create .opencodespace directory and fly.toml
        opencodespace_dir = temp_project_dir / ".opencodespace"
        opencodespace_dir.mkdir()
        (opencodespace_dir / "Dockerfile").write_text("test dockerfile")
        (opencodespace_dir / "entrypoint.sh").write_text("test entrypoint")
        
        fly_toml_path = temp_project_dir / "fly.toml"
        fly_toml_path.write_text("test fly.toml")
        
        # Verify files exist before cleanup
        assert opencodespace_dir.exists()
        assert fly_toml_path.exists()
        
        provider._cleanup_deployment_files(temp_project_dir)
        
        # Files should be removed
        assert not opencodespace_dir.exists()
        assert not fly_toml_path.exists()
    
    def test_cleanup_deployment_files_preserve_config_dir(self, temp_project_dir):
        """Test that cleanup doesn't remove the actual .opencodespace config directory."""
        provider = FlyProvider()
        
        # Create the actual config directory with config file
        config_dir = temp_project_dir / ".opencodespace"
        config_dir.mkdir()
        config_file = config_dir / "config.toml"
        config_file.write_text("test config")
        
        # Also create fly.toml
        fly_toml_path = temp_project_dir / "fly.toml"
        fly_toml_path.write_text("test fly.toml")
        
        provider._cleanup_deployment_files(temp_project_dir)
        
        # Config directory should still exist (it's the real config dir)
        assert config_dir.exists()
        assert config_file.exists()
        
        # fly.toml should be removed
        assert not fly_toml_path.exists()
    
    @patch.object(FlyProvider, '_cleanup_deployment_files')
    @patch.object(FlyProvider, '_set_fly_secrets')
    @patch.object(FlyProvider, '_copy_deployment_files')
    @patch.object(FlyProvider, 'build_environment_vars')
    @patch.object(FlyProvider, 'validate_config')
    @patch.object(FlyProvider, 'check_requirements')
    def test_deploy_success(self, mock_check_req, mock_validate, mock_env_vars, 
                           mock_copy_files, mock_set_secrets, mock_cleanup, temp_project_dir):
        """Test successful deployment to Fly.io."""
        provider = FlyProvider()
        
        config = {"name": "test-app"}
        mock_env_vars.return_value = {"PASSWORD": "test-password"}
        
        with patch('subprocess.run') as mock_run:
            mock_run.return_value = Mock(returncode=0)
            
            provider.deploy(temp_project_dir, config)
            
            # Verify all steps were called
            mock_check_req.assert_called_once()
            mock_validate.assert_called_once_with(config)
            mock_copy_files.assert_called_once_with(temp_project_dir)
            mock_env_vars.assert_called_once_with(config)
            mock_set_secrets.assert_called_once_with(temp_project_dir, {"PASSWORD": "test-password"})
            mock_cleanup.assert_called_once_with(temp_project_dir)
            
            # Verify flyctl commands were called
            assert mock_run.call_count == 2
            
            # Check flyctl launch command
            launch_call = mock_run.call_args_list[0]
            expected_launch = [
                "flyctl", "launch",
                "--copy-config",
                "--no-deploy",
                "--name", "test-app"
            ]
            assert launch_call[0][0] == expected_launch
            assert launch_call[1]["cwd"] == temp_project_dir
            assert launch_call[1]["check"] is True
            
            # Check flyctl deploy command
            deploy_call = mock_run.call_args_list[1]
            assert deploy_call[0][0] == ["flyctl", "deploy"]
            assert deploy_call[1]["cwd"] == temp_project_dir
            assert deploy_call[1]["check"] is True
    
    @patch.object(FlyProvider, '_cleanup_deployment_files')
    @patch.object(FlyProvider, '_copy_deployment_files')
    @patch.object(FlyProvider, 'check_requirements')
    def test_deploy_generates_name_if_missing(self, mock_check_req, mock_copy_files, 
                                             mock_cleanup, temp_project_dir):
        """Test that deployment generates app name if not provided."""
        provider = FlyProvider()
        config = {}  # No name provided
        
        with patch('subprocess.run') as mock_run, \
             patch.object(provider, 'validate_config') as mock_validate, \
             patch.object(provider, 'build_environment_vars') as mock_env_vars, \
             patch.object(provider, '_set_fly_secrets') as mock_set_secrets:
            
            mock_run.return_value = Mock(returncode=0)
            mock_env_vars.return_value = {}
            
            provider.deploy(temp_project_dir, config)
            
            # validate_config should have generated a name
            mock_validate.assert_called_once_with(config)
            assert "name" in config
    
    @patch.object(FlyProvider, '_cleanup_deployment_files')
    @patch.object(FlyProvider, '_copy_deployment_files')
    @patch.object(FlyProvider, 'check_requirements')
    def test_deploy_flyctl_launch_failure(self, mock_check_req, mock_copy_files, 
                                         mock_cleanup, temp_project_dir):
        """Test deployment failure when flyctl launch fails."""
        provider = FlyProvider()
        config = {"name": "test-app"}
        
        with patch('subprocess.run') as mock_run, \
             patch.object(provider, 'validate_config'), \
             patch.object(provider, 'build_environment_vars') as mock_env_vars, \
             patch.object(provider, '_set_fly_secrets'):
            
            mock_env_vars.return_value = {}
            # Mock flyctl launch failure
            mock_run.side_effect = subprocess.CalledProcessError(1, ["flyctl", "launch"])
            
            with pytest.raises(RuntimeError, match="Fly.io deployment failed"):
                provider.deploy(temp_project_dir, config)
            
            # Cleanup should still be called
            mock_cleanup.assert_called_once_with(temp_project_dir)
    
    @patch.object(FlyProvider, '_cleanup_deployment_files')
    @patch.object(FlyProvider, '_copy_deployment_files')
    @patch.object(FlyProvider, 'check_requirements')
    def test_deploy_flyctl_deploy_failure(self, mock_check_req, mock_copy_files, 
                                         mock_cleanup, temp_project_dir):
        """Test deployment failure when flyctl deploy fails."""
        provider = FlyProvider()
        config = {"name": "test-app"}
        
        with patch('subprocess.run') as mock_run, \
             patch.object(provider, 'validate_config'), \
             patch.object(provider, 'build_environment_vars') as mock_env_vars, \
             patch.object(provider, '_set_fly_secrets'):
            
            mock_env_vars.return_value = {}
            # Mock flyctl launch success, deploy failure
            mock_run.side_effect = [
                Mock(returncode=0),  # launch succeeds
                subprocess.CalledProcessError(1, ["flyctl", "deploy"])  # deploy fails
            ]
            
            with pytest.raises(RuntimeError, match="Fly.io deployment failed"):
                provider.deploy(temp_project_dir, config)
            
            # Cleanup should still be called
            mock_cleanup.assert_called_once_with(temp_project_dir)
    
    @patch.object(FlyProvider, 'check_requirements')
    def test_stop_success(self, mock_check_req):
        """Test successful app stop (scale to 0)."""
        provider = FlyProvider()
        config = {"name": "test-app"}
        
        with patch('subprocess.run') as mock_run:
            mock_run.return_value = Mock(returncode=0)
            
            provider.stop(config)
            
            mock_check_req.assert_called_once()
            
            # Check flyctl scale command
            mock_run.assert_called_once_with([
                "flyctl", "scale", "count", "0", "--app", "test-app"
            ], check=True)
    
    @patch.object(FlyProvider, 'check_requirements')
    def test_stop_no_app_name(self, mock_check_req):
        """Test stop when no app name is provided."""
        provider = FlyProvider()
        config = {}  # No name
        
        with pytest.raises(RuntimeError, match="No app name found in configuration"):
            provider.stop(config)
    
    @patch.object(FlyProvider, 'check_requirements')
    def test_stop_flyctl_failure(self, mock_check_req):
        """Test stop when flyctl scale fails."""
        provider = FlyProvider()
        config = {"name": "test-app"}
        
        with patch('subprocess.run') as mock_run:
            mock_run.side_effect = subprocess.CalledProcessError(1, ["flyctl", "scale"])
            
            with pytest.raises(RuntimeError, match="Failed to stop Fly.io app"):
                provider.stop(config)
    
    @patch.object(FlyProvider, 'check_requirements')
    def test_remove_success(self, mock_check_req):
        """Test successful app removal."""
        provider = FlyProvider()
        config = {"name": "test-app"}
        
        with patch('subprocess.run') as mock_run:
            mock_run.return_value = Mock(returncode=0)
            
            provider.remove(config)
            
            mock_check_req.assert_called_once()
            
            # Check flyctl apps destroy command
            mock_run.assert_called_once_with([
                "flyctl", "apps", "destroy", "test-app", "--yes"
            ], check=True)
    
    @patch.object(FlyProvider, 'check_requirements')
    def test_remove_no_app_name(self, mock_check_req):
        """Test remove when no app name is provided."""
        provider = FlyProvider()
        config = {}  # No name
        
        with pytest.raises(RuntimeError, match="No app name found in configuration"):
            provider.remove(config)
    
    @patch.object(FlyProvider, 'check_requirements')
    def test_remove_app_not_found(self, mock_check_req):
        """Test remove when app doesn't exist (should not raise error)."""
        provider = FlyProvider()
        config = {"name": "nonexistent-app"}
        
        with patch('subprocess.run') as mock_run:
            # Mock "Could not find App" error
            error = subprocess.CalledProcessError(1, ["flyctl", "apps", "destroy"])
            error.stderr = "Could not find App 'nonexistent-app'"
            mock_run.side_effect = error
            
            # Should not raise an exception, just print info message
            provider.remove(config)
            
            mock_check_req.assert_called_once()
    
    @patch.object(FlyProvider, 'check_requirements')
    def test_remove_flyctl_failure(self, mock_check_req):
        """Test remove when flyctl destroy fails with other error."""
        provider = FlyProvider()
        config = {"name": "test-app"}
        
        with patch('subprocess.run') as mock_run:
            # Mock generic flyctl error
            error = subprocess.CalledProcessError(1, ["flyctl", "apps", "destroy"])
            error.stderr = "Some other error"
            mock_run.side_effect = error
            
            with pytest.raises(RuntimeError, match="Failed to remove Fly.io app"):
                provider.remove(config)
    
    def test_adjectives_and_nouns_lists(self):
        """Test that adjectives and nouns lists are not empty and contain valid words."""
        provider = FlyProvider()
        
        # Lists should not be empty
        assert len(provider.ADJECTIVES) > 0
        assert len(provider.NOUNS) > 0
        
        # All items should be strings with no spaces or special characters
        for adjective in provider.ADJECTIVES:
            assert isinstance(adjective, str)
            assert len(adjective) > 0
            assert adjective.isalnum()
            assert adjective.islower()
        
        for noun in provider.NOUNS:
            assert isinstance(noun, str)
            assert len(noun) > 0
            assert noun.isalnum()
            assert noun.islower()
    
    def test_app_name_generation_uniqueness(self):
        """Test that app name generation produces different names."""
        provider = FlyProvider()
        
        # Generate 20 names and check they're all different
        names = set()
        for _ in range(20):
            name = provider.generate_app_name()
            names.add(name)
        
        # With random numbers, we should get different names
        # (very small chance of collision, but mathematically possible)
        assert len(names) > 15  # Allow for some potential collisions
    
    def test_validate_config_preserves_other_fields(self):
        """Test that validate_config doesn't modify other configuration fields."""
        provider = FlyProvider()
        
        config = {
            "platform": "fly",
            "upload_folder": False,
            "git_repo_url": "git@github.com:test/repo.git",
            "env": {"OPENAI_API_KEY": "sk-test"}
        }
        
        original_config = config.copy()
        
        provider.validate_config(config)
        
        # Name should be added
        assert "name" in config
        
        # Other fields should be unchanged
        for key, value in original_config.items():
            assert config[key] == value 