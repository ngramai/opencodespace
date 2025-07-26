"""Fly.io provider implementation."""

import logging
import random
import shutil
import subprocess
from pathlib import Path
from typing import Any, Dict

try:
    from importlib.metadata import version
except ImportError:
    # Python 3.7 compatibility
    from importlib_metadata import version

from .base import Provider

# Set up logger for fly provider
logger = logging.getLogger('opencodespace')

# Import CONFIG_DIR from parent module
CONFIG_DIR = ".opencodespace"


class FlyProvider(Provider):
    """
    Provider for deploying to Fly.io platform.
    
    This provider uses the flyctl CLI to deploy applications to Fly.io's
    global application platform.
    """
    
    # Word lists for random name generation
    ADJECTIVES = [
        "quick", "brave", "calm", "eager", "fancy", "gentle", "happy", "jolly",
        "kind", "lively", "merry", "nice", "proud", "silly", "witty", "young",
        "bright", "clever", "swift", "bold", "cool", "warm", "wild", "free"
    ]
    
    NOUNS = [
        "panda", "tiger", "eagle", "whale", "koala", "otter", "zebra", "shark",
        "raven", "moose", "gecko", "heron", "bison", "crane", "robin", "finch",
        "cloud", "river", "storm", "wave", "spark", "star", "moon", "comet"
    ]
    
    @property
    def name(self) -> str:
        return "fly"
    
    @property
    def description(self) -> str:
        return "Deploy to Fly.io global application platform"
    
    def generate_app_name(self) -> str:
        """Generate a random app name in format: word-word-123."""
        adjective = random.choice(self.ADJECTIVES)
        noun = random.choice(self.NOUNS)
        number = random.randint(100, 9999)
        return f"{adjective}-{noun}-{number}"
    
    def check_requirements(self) -> None:
        """Check if flyctl is installed."""
        if subprocess.call(["which", "flyctl"], stdout=subprocess.DEVNULL) != 0:
            raise RuntimeError(
                "flyctl is not installed. "
                "Please install from https://fly.io/docs/hands-on/install-flyctl/"
            )
    
    def validate_config(self, config: Dict[str, Any]) -> None:
        """Validate Fly.io specific configuration."""
        # Generate app name if not provided
        if not config.get("name"):
            config["name"] = self.generate_app_name()
        
        # Validate app name format (Fly.io requirements)
        app_name = config["name"]
        if not app_name.replace("-", "").isalnum():
            raise ValueError(
                "Application name must contain only letters, numbers, and hyphens"
            )
        if len(app_name) > 30:
            raise ValueError("Application name must be 30 characters or less")
    
    def _copy_deployment_files(self, path: Path) -> None:
        """Copy OpenCodeSpace deployment files to project directory."""
        # Create .opencodespace directory in target path
        target_dir = path / ".opencodespace"
        target_dir.mkdir(exist_ok=True)
        
        # Copy OpenCodeSpace Docker files to project directory using pkg_resources
        files_to_copy = ["Dockerfile", "entrypoint.sh", "fly.toml"]
        
        for filename in files_to_copy:
            try:
                # Load resource data using importlib.resources
                from importlib.resources import files, as_file
                resource_path = files('opencodespace') / '.opencodespace' / filename
                with as_file(resource_path) as resource_file:
                    content = resource_file.read_bytes()
                target_file = target_dir / filename
                if filename == "entrypoint.sh":
                    # Write as binary to preserve line endings and make executable
                    target_file.write_bytes(content)
                    target_file.chmod(0o755)
                else:
                    target_file.write_bytes(content)
            except FileNotFoundError:
                logger.info(f"Warning: {filename} not found in package resources")
        
        # Copy fly.toml to root (Fly.io expects it there)
        try:
            # Load fly.toml template using importlib.resources
            from importlib.resources import files, as_file
            resource_path = files('opencodespace') / '.opencodespace' / 'fly.toml'
            with as_file(resource_path) as resource_file:
                fly_content = resource_file.read_bytes()
            (path / "fly.toml").write_bytes(fly_content)
            logger.info(f"📄 Copied fly.toml to project root")
        except FileNotFoundError:
            logger.info(f"Warning: fly.toml not found in package resources")
    
    def _set_fly_secrets(self, path: Path, env_vars: Dict[str, str]) -> None:
        """Set environment variables as Fly.io secrets."""
        if env_vars:
            logger.info(f"🔐 Setting environment variables...")
            for key, val in env_vars.items():
                subprocess.run(
                    ["flyctl", "secrets", "set", f"{key}={val}"], 
                    cwd=path,
                    check=True,
                    capture_output=True  # Hide sensitive output
                )
    
    def _cleanup_deployment_files(self, path: Path) -> None:
        """Clean up copied deployment files."""
        # Remove .opencodespace directory
        target_dir = path / ".opencodespace"
        if target_dir.exists() and target_dir != path / CONFIG_DIR:
            shutil.rmtree(target_dir)
            logger.info(f"🧹 Cleaned up .opencodespace directory")
        
        # Remove fly.toml from root
        fly_toml_path = path / "fly.toml"
        if fly_toml_path.exists():
            fly_toml_path.unlink()
            logger.info(f"🧹 Cleaned up fly.toml")
    
    def deploy(self, path: Path, config: Dict[str, Any]) -> None:
        """Deploy application to Fly.io."""
        self.check_requirements()
        
        # Generate app name if not set
        if not config.get("name"):
            config["name"] = self.generate_app_name()
        
        self.validate_config(config)
        
        try:
            # Copy deployment files
            self._copy_deployment_files(path)
            
            # Launch the app without deploying first
            logger.info(f"📱 Launching Fly.io app: {config['name']}")
            subprocess.run(
                [
                    "flyctl", "launch",
                    "--copy-config",
                    "--no-deploy",
                    "--name", config["name"]
                ], 
                cwd=path,
                check=True
            )
            
            # Get all environment variables using base class method
            env_vars = self.build_environment_vars(config)
            
            # Set secrets for environment variables
            self._set_fly_secrets(path, env_vars)
            
            # Deploy the application
            logger.info(f"🚀 Deploying to Fly.io...")
            subprocess.run(["flyctl", "deploy"], cwd=path, check=True)
            
            logger.info(f"✅ Deployment successful!")
            logger.info(f"🌐 Your app is available at: https://{config['name']}.fly.dev")
            
        except subprocess.CalledProcessError as e:
            raise RuntimeError(f"Fly.io deployment failed: {e}")
        finally:
            # Clean up copied files
            self._cleanup_deployment_files(path)
    
    def stop(self, config: Dict[str, Any]) -> None:
        """Stop (scale to 0) the Fly.io application."""
        self.check_requirements()
        
        app_name = config.get("name")
        if not app_name:
            raise RuntimeError("No app name found in configuration")
        
        try:
            logger.info(f"🛑 Stopping Fly.io app: {app_name}")
            
            # Scale the app to 0 instances
            subprocess.run(
                ["flyctl", "scale", "count", "0", "--app", app_name],
                check=True
            )
            
            logger.info(f"✅ App stopped successfully (scaled to 0 instances)")
            
        except subprocess.CalledProcessError as e:
            raise RuntimeError(f"Failed to stop Fly.io app: {e}")
    
    def remove(self, config: Dict[str, Any]) -> None:
        """Destroy the Fly.io application."""
        self.check_requirements()
        
        app_name = config.get("name")
        if not app_name:
            raise RuntimeError("No app name found in configuration")
        
        try:
            logger.info(f"🗑️  Removing Fly.io app: {app_name}")
            
            # Destroy the app (with --yes to skip confirmation)
            subprocess.run(
                ["flyctl", "apps", "destroy", app_name, "--yes"],
                check=True
            )
            
            logger.info(f"✅ App removed successfully")
            
        except subprocess.CalledProcessError as e:
            # Check if app doesn't exist
            if "Could not find App" in str(e):
                logger.info(f"ℹ️  App not found (may have been already removed)")
            else:
                raise RuntimeError(f"Failed to remove Fly.io app: {e}")