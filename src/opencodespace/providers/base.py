"""Base provider interface for OpenCodeSpace."""

import logging
import subprocess
import textwrap
from abc import ABC, abstractmethod
from pathlib import Path
from typing import Any, Dict

# Set up logger for providers
logger = logging.getLogger('opencodespace')


class Provider(ABC):
    """
    Abstract base class for deployment providers.
    
    All providers must implement this interface to be compatible with
    the OpenCodeSpace deployment system.
    """
    
    @abstractmethod
    def check_requirements(self) -> None:
        """
        Check if required tools/dependencies are installed.
        
        Raises:
            RuntimeError: If requirements are not met
        """
        pass
    
    @abstractmethod
    def deploy(self, path: Path, config: Dict[str, Any]) -> None:
        """
        Deploy the development environment.
        
        Args:
            path: Project directory path
            config: Configuration dictionary containing deployment settings
            
        Raises:
            RuntimeError: If deployment fails
        """
        pass
    
    @abstractmethod
    def stop(self, config: Dict[str, Any]) -> None:
        """
        Stop the development environment.
        
        Args:
            config: Configuration dictionary containing deployment settings
            
        Raises:
            RuntimeError: If stop operation fails
        """
        pass
    
    @abstractmethod
    def remove(self, config: Dict[str, Any]) -> None:
        """
        Remove/destroy the development environment.
        
        Args:
            config: Configuration dictionary containing deployment settings
            
        Raises:
            RuntimeError: If removal fails
        """
        pass
    
    @property
    @abstractmethod
    def name(self) -> str:
        """
        Return the provider name.
        
        This name is used in configuration files and CLI commands.
        
        Returns:
            Provider identifier string
        """
        pass
    
    @property
    def description(self) -> str:
        """
        Return a human-readable description of the provider.
        
        Returns:
            Provider description
        """
        return f"{self.name} provider"
    
    def validate_config(self, config: Dict[str, Any]) -> None:
        """
        Validate provider-specific configuration.
        
        Override this method to add custom validation logic.
        
        Args:
            config: Configuration dictionary
            
        Raises:
            ValueError: If configuration is invalid
        """
        pass
    
    def _setup_git_config(self, env_vars: Dict[str, str]) -> None:
        """
        Add Git user configuration to environment variables.
        
        Args:
            env_vars: Environment variables dictionary to update
        """
        # Add Git user info if available
        git_config = subprocess.run(
            ["git", "config", "user.name"],
            capture_output=True,
            text=True
        )
        if git_config.returncode == 0 and git_config.stdout.strip():
            env_vars["GIT_USER_NAME"] = git_config.stdout.strip()
        
        git_config = subprocess.run(
            ["git", "config", "user.email"],
            capture_output=True,
            text=True
        )
        if git_config.returncode == 0 and git_config.stdout.strip():
            env_vars["GIT_USER_EMAIL"] = git_config.stdout.strip()
    
    def _setup_ssh_key(self, config: Dict[str, Any], env_vars: Dict[str, str]) -> bool:
        """
        Add SSH key to environment variables if provided.
        
        Args:
            config: Configuration dictionary
            env_vars: Environment variables dictionary to update
            
        Returns:
            True if SSH key was added, False otherwise
        """
        ssh_key_path = config.get("ssh_key_path")
        if ssh_key_path and Path(ssh_key_path).exists():
            with open(ssh_key_path, 'r') as f:
                env_vars["SSH_PRIVATE_KEY"] = f.read()
            return True
        return False
    
    def _setup_vscode_config(self, config: Dict[str, Any], env_vars: Dict[str, str]) -> None:
        """
        Add VS Code configuration to environment variables.
        
        Args:
            config: Configuration dictionary
            env_vars: Environment variables dictionary to update
        """
        vscode_config = config.get("vscode_config", {})
        
        if vscode_config.get("copy_extensions", False):
            # VS Code extensions
            vscode_extensions = vscode_config.get("vscode_extensions_list", [])
            if vscode_extensions:
                env_vars["VSCODE_EXTENSIONS"] = ",".join(vscode_extensions)
                logger.info(f"🧩 Will install {len(vscode_extensions)} VS Code extensions")
        
        if vscode_config.get("copy_settings", False):
            # VS Code settings
            vscode_settings_path = vscode_config.get("vscode_settings_path")
            if vscode_settings_path and Path(vscode_settings_path).exists():
                with open(vscode_settings_path, 'r') as f:
                    env_vars["VSCODE_SETTINGS"] = f.read()
                logger.info("📄 Will copy VS Code settings")
    
    def _setup_cursor_config(self, config: Dict[str, Any], env_vars: Dict[str, str]) -> None:
        """
        Add Cursor configuration to environment variables.
        
        Args:
            config: Configuration dictionary
            env_vars: Environment variables dictionary to update
        """
        vscode_config = config.get("vscode_config", {})
        
        if vscode_config.get("copy_extensions", False):
            # Cursor extensions
            cursor_extensions = vscode_config.get("cursor_extensions_list", [])
            if cursor_extensions:
                env_vars["CURSOR_EXTENSIONS"] = ",".join(cursor_extensions)
                logger.info(f"🧩 Will install {len(cursor_extensions)} Cursor extensions")
        
        if vscode_config.get("copy_settings", False):
            # Cursor settings
            cursor_settings_path = vscode_config.get("cursor_settings_path")
            if cursor_settings_path and Path(cursor_settings_path).exists():
                with open(cursor_settings_path, 'r') as f:
                    env_vars["CURSOR_SETTINGS"] = f.read()
                logger.info("📄 Will copy Cursor settings")
    
    def _check_ssh_and_upload_warning(self, config: Dict[str, Any], has_ssh_key: bool) -> None:
        """
        Display warning if both SSH key and upload folder are disabled.
        
        Args:
            config: Configuration dictionary
            has_ssh_key: Whether SSH key is available
        """
        upload_folder = config.get("upload_folder", False)
        git_repo_url = config.get("git_repo_url")
        
        if not has_ssh_key and not upload_folder:
            logger.info("⚠️  Warning: No SSH key provided and folder upload disabled.")
            logger.info("   The container will start with an empty workspace and no git access.")
            logger.info("   Consider enabling folder upload or providing an SSH key for git operations.")
        elif upload_folder and not git_repo_url:
            logger.info("ℹ️  Info: Uploading folder without git repository cloning.")
            logger.info("   Git operations will be skipped to avoid initialization issues.")
    
    def _setup_ai_api_keys(self, config: Dict[str, Any], env_vars: Dict[str, str]) -> None:
        """
        Setup AI API keys as environment variables.
        
        Args:
            config: Configuration dictionary
            env_vars: Environment variables dictionary to update
        """
        ai_api_keys = config.get("ai_api_keys", {})
        
        for key_name, api_key in ai_api_keys.items():
            if api_key and api_key.strip():
                env_vars[key_name] = api_key.strip()
                logger.info(f"🤖 Will set {key_name} environment variable")
    
    def build_environment_vars(self, config: Dict[str, Any]) -> Dict[str, str]:
        """
        Build complete environment variables dictionary from configuration.
        
        Args:
            config: Configuration dictionary
            
        Returns:
            Environment variables dictionary
        """
        env_vars = config.get("env", {}).copy()
        
        # Add VS Code password if provided
        if "vscode_password" in config:
            env_vars["PASSWORD"] = config["vscode_password"]
        
        # Add Git repository URL if provided
        if "git_repo_url" in config:
            env_vars["GIT_REPO_URL"] = config["git_repo_url"]
        
        # Setup SSH key and check for warnings
        has_ssh_key = self._setup_ssh_key(config, env_vars)
        self._check_ssh_and_upload_warning(config, has_ssh_key)
        
        # Add SKIP_GIT_SETUP if no SSH key and no upload folder
        # OR if upload folder is enabled but no git repo URL is provided
        upload_folder = config.get("upload_folder", False)
        git_repo_url = config.get("git_repo_url")
        
        if not has_ssh_key and not upload_folder:
            env_vars["SKIP_GIT_SETUP"] = "true"
        elif upload_folder and not git_repo_url:
            # When uploading folder without a specific git repo, skip git operations
            # to avoid failures when initializing git in uploaded folders
            env_vars["SKIP_GIT_SETUP"] = "true"
        
        # Setup Git configuration
        self._setup_git_config(env_vars)
        
        # Setup VS Code and Cursor configuration
        self._setup_vscode_config(config, env_vars)
        self._setup_cursor_config(config, env_vars)
        
        # Setup AI API keys
        self._setup_ai_api_keys(config, env_vars)
        
        return env_vars
    
    def _generate_dockerfile_content(self) -> str:
        """Generate the Dockerfile content."""
        return textwrap.dedent("""
            FROM codercom/code-server:latest
            
            USER root
            
            # Install essential development tools
            RUN apt-get update && apt-get install -y \\
                git \\
                openssh-client \\
                curl \\
                wget \\
                vim \\
                nano \\
                build-essential \\
                python3 \\
                python3-pip \\
                && rm -rf /var/lib/apt/lists/*
            
            # Install Node.js 24.x
            RUN curl -fsSL https://deb.nodesource.com/setup_24.x | bash - && \\
                apt-get install -y nodejs && \\
                rm -rf /var/lib/apt/lists/*
            
            RUN npm install -g @google/gemini-cli
            RUN npm install -g @anthropic-ai/claude-code
            
                # Create workspace directory
            RUN mkdir -p /home/coder/workspace && \\
                chown -R coder:coder /home/coder/workspace
            
            # Set up SSH directory for coder user
            RUN mkdir -p /home/coder/.ssh && \\
                chown -R coder:coder /home/coder/.ssh && \\
                chmod 700 /home/coder/.ssh
            
            # Copy entrypoint script
            COPY .opencodespace/entrypoint.sh /usr/local/bin/entrypoint.sh
            RUN chmod +x /usr/local/bin/entrypoint.sh
            
            USER coder
            
            # Set working directory
            WORKDIR /home/coder/workspace
            
            # Environment variables
            ENV GIT_TERMINAL_PROMPT=0
            ENV SHELL=/bin/bash
            
            # Expose code-server port
            EXPOSE 8080
            
            ENTRYPOINT ["/usr/local/bin/entrypoint.sh"]
        """).strip()
    
    def _generate_entrypoint_content(self) -> str:
        """Generate the entrypoint.sh content."""
        return textwrap.dedent("""
            #!/bin/bash
            set -e
            
            # Function to generate branch name
            generate_branch_name() {
                echo "opencodespace-$(date +%Y%m%d-%H%M%S)-$(openssl rand -hex 4)"
            }
            
            # Function to setup Gemini configuration
            setup_gemini_config() {
                echo "Setting up Gemini configuration..."
                
                # Create Gemini config directory
                mkdir -p /home/coder/.gemini
                
                # Create settings.json with default configuration
                cat > /home/coder/.gemini/settings.json << 'EOF'
            {
              "theme": "Default",
              "selectedAuthType": "gemini-api-key"
            }
            EOF
                
                # Set proper ownership
                chown -R coder:coder /home/coder/.gemini/
                
                echo "Gemini configuration setup complete."
            }
            
            # Function to setup VS Code configuration
            setup_vscode_config() {
                echo "Setting up VS Code configuration..."
                
                # Create code-server user config directory
                mkdir -p /home/coder/.local/share/code-server/User
                
                # Install VS Code extensions if provided
                if [ -n "$VSCODE_EXTENSIONS" ]; then
                    echo "Installing VS Code extensions..."
                    IFS=',' read -ra EXTENSIONS <<< "$VSCODE_EXTENSIONS"
                    for extension in "${EXTENSIONS[@]}"; do
                        if [ -n "$extension" ]; then
                            echo "Installing VS Code extension: $extension"
                            code-server --install-extension "$extension" || echo "Failed to install VS Code extension: $extension"
                        fi
                    done
                fi
                
                # Install Cursor extensions if provided
                if [ -n "$CURSOR_EXTENSIONS" ]; then
                    echo "Installing Cursor extensions (compatible with VS Code)..."
                    IFS=',' read -ra EXTENSIONS <<< "$CURSOR_EXTENSIONS"
                    for extension in "${EXTENSIONS[@]}"; do
                        if [ -n "$extension" ]; then
                            echo "Installing Cursor extension: $extension"
                            code-server --install-extension "$extension" || echo "Failed to install Cursor extension: $extension"
                        fi
                    done
                fi
                
                # Copy VS Code settings if provided
                if [ -n "$VSCODE_SETTINGS" ]; then
                    echo "Copying VS Code settings..."
                    echo "$VSCODE_SETTINGS" > /home/coder/.local/share/code-server/User/settings.json
                fi
                
                # Copy Cursor settings if provided (merge with VS Code settings)
                if [ -n "$CURSOR_SETTINGS" ]; then
                    echo "Merging Cursor settings..."
                    if [ -f /home/coder/.local/share/code-server/User/settings.json ]; then
                        # If both settings exist, we need to merge them
                        # For now, prioritize VS Code settings and add a comment about Cursor
                        echo "// Note: Cursor settings were also detected but VS Code settings take precedence" >> /home/coder/.local/share/code-server/User/settings.json
                    else
                        # If only Cursor settings exist, use them
                        echo "$CURSOR_SETTINGS" > /home/coder/.local/share/code-server/User/settings.json
                    fi
                fi
                
                # Set proper ownership
                chown -R coder:coder /home/coder/.local/share/code-server/
                
                echo "VS Code configuration setup complete."
            }
            
            # Function to setup Git
            setup_git() {
                if [ -n "$GIT_USER_NAME" ]; then
                    git config --global user.name "$GIT_USER_NAME"
                fi
                
                if [ -n "$GIT_USER_EMAIL" ]; then
                    git config --global user.email "$GIT_USER_EMAIL"
                fi
                
                # Configure Git to trust the workspace directory
                git config --global --add safe.directory /home/coder/workspace
            }
            
            # Function to setup SSH
            setup_ssh() {
                if [ -n "$SSH_PRIVATE_KEY" ]; then
                    echo "Setting up SSH key..."
                    echo "$SSH_PRIVATE_KEY" > /home/coder/.ssh/id_rsa
                    chmod 600 /home/coder/.ssh/id_rsa
                    
                    # Start ssh-agent and add key
                    eval "$(ssh-agent -s)"
                    ssh-add /home/coder/.ssh/id_rsa
                    
                    # Add GitHub to known hosts
                    ssh-keyscan -t rsa github.com >> /home/coder/.ssh/known_hosts 2>/dev/null
                fi
            }
            
            # Function to handle Git repository
            handle_git_repo() {
                # Skip git setup if explicitly disabled
                if [ "$SKIP_GIT_SETUP" = "true" ]; then
                    echo "Skipping Git setup (no SSH key and no folder upload)"
                    return
                fi
                
                cd /home/coder/workspace
                
                # Check if GIT_REPO_URL is provided
                if [ -n "$GIT_REPO_URL" ]; then
                    echo "Cloning repository from $GIT_REPO_URL..."
                    git clone "$GIT_REPO_URL" .
                    
                    # Create new branch
                    BRANCH_NAME=$(generate_branch_name)
                    echo "Creating new branch: $BRANCH_NAME"
                    git checkout -b "$BRANCH_NAME"
                    
                elif [ -d ".git" ]; then
                    # Existing Git repository
                    echo "Existing Git repository detected"
                    
                    # Fetch latest changes
                    git fetch origin
                    
                    # Create new branch from current HEAD
                    BRANCH_NAME=$(generate_branch_name)
                    echo "Creating new branch: $BRANCH_NAME"
                    git checkout -b "$BRANCH_NAME"
                    
                else
                    # No Git repo, initialize new one
                    echo "Initializing new Git repository..."
                    git init
                    
                    # Create initial commit if there are files
                    if [ "$(ls -A)" ]; then
                        git add .
                        git commit -m "Initial commit from OpenCodeSpace"
                    fi
                    
                    # Create working branch
                    BRANCH_NAME=$(generate_branch_name)
                    echo "Creating new branch: $BRANCH_NAME"
                    git checkout -b "$BRANCH_NAME"
                fi
                
                echo "Git setup complete. Working on branch: $BRANCH_NAME"
            }
            
            # Main execution
            echo "Starting OpenCodeSpace environment setup..."
            
            # Setup SSH if key is provided
            setup_ssh
            
            # Setup Git configuration (only if not skipping git setup)
            if [ "$SKIP_GIT_SETUP" != "true" ]; then
                setup_git
            fi
            
            # Setup Gemini configuration
            setup_gemini_config
            
            # Setup VS Code configuration
            setup_vscode_config
            
            # Handle Git repository
            handle_git_repo
            
            # Start code-server
            echo "Starting code-server..."
            
            # Use password authentication if PASSWORD is set, otherwise no auth
            if [ -n "$PASSWORD" ]; then
                echo "Using password authentication for code-server..."
                exec code-server --bind-addr 0.0.0.0:8080 --auth password /home/coder/workspace
            else
                echo "Using no authentication for code-server..."
                exec code-server --bind-addr 0.0.0.0:8080 --auth none /home/coder/workspace
            fi
            """).strip()