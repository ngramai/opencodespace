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

import textwrap

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
    
    
    def _generate_fly_toml_content(self, app_name: str) -> str:
        """Generate the fly.toml content."""
        return textwrap.dedent(f"""
            app = "{app_name}"
            primary_region = "ord"
            
            [build]
              dockerfile = ".opencodespace/Dockerfile"
            
            [env]
              PORT = "8080"
            
            [http_service]
              internal_port = 8080
              force_https = true
              auto_stop_machines = true
              auto_start_machines = true
              min_machines_running = 0
            
            [[vm]]
              cpu_kind = "shared"
              cpus = 1
              memory_mb = 1024
        """).strip()
    
    def _copy_deployment_files(self, path: Path) -> None:
        """Copy OpenCodeSpace deployment files to project directory."""
        # Create .opencodespace directory in target path
        target_dir = path / ".opencodespace"
        target_dir.mkdir(exist_ok=True)
        
        # Generate and write Dockerfile
        dockerfile_path = target_dir / "Dockerfile"
        if not dockerfile_path.exists():
            dockerfile_content = self._generate_dockerfile_content()
            dockerfile_path.write_text(dockerfile_content)
            logger.info(f"📄 Created .opencodespace/Dockerfile")
        else:
            logger.info(f"ℹ️  Dockerfile already exists in .opencodespace/")
        
        # Generate and write entrypoint.sh
        entrypoint_path = target_dir / "entrypoint.sh"
        if not entrypoint_path.exists():
            entrypoint_content = self._generate_entrypoint_content()
            entrypoint_path.write_text(entrypoint_content)
            entrypoint_path.chmod(0o755)
            logger.info(f"📄 Created .opencodespace/entrypoint.sh")
        else:
            logger.info(f"ℹ️  entrypoint.sh already exists in .opencodespace/")
        
        # Generate and write fly.toml in .opencodespace
        fly_toml_path = target_dir / "fly.toml"
        if not fly_toml_path.exists():
            fly_toml_content = self._generate_fly_toml_content(self.config.get("name", "opencodespace"))
            fly_toml_path.write_text(fly_toml_content)
            logger.info(f"📄 Created .opencodespace/fly.toml")
        else:
            logger.info(f"ℹ️  fly.toml already exists in .opencodespace/")
        
        # Copy fly.toml to root (Fly.io expects it there)
        root_fly_toml = path / "fly.toml"
        if not root_fly_toml.exists():
            shutil.copy(fly_toml_path, root_fly_toml)
            logger.info(f"📄 Copied fly.toml to project root")
        else:
            logger.info(f"ℹ️  fly.toml already exists in project root")
    
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
            # Store config for use in _copy_deployment_files
            self.config = config
            
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