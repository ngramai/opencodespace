# 🛰️ OpenCodeSpace

Launch disposable VS Code development environments for YOLO mode development with AI tools like Claude Code and Gemini. Either locally with Docker or remotely on Fly.io (AWS, GCE, Digital Ocean coming soon). Like Code Spaces, but fully self hosted and open source.

[![PyPI version](https://badge.fury.io/py/opencodespace.svg)](https://badge.fury.io/py/opencodespace)
[![Python 3.7+](https://img.shields.io/badge/python-3.7+-blue.svg)](https://www.python.org/downloads/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)

---

## ✨ Features

- **🐳 Local Development**: Run environments locally using Docker (Remote Docker coming soon)
- **☁️ Cloud Deployment**: Deploy to Fly.io's global platform (AWS, GCE, Digital Ocean coming soon).  
- **🤖 AI-Ready**: Pre-configured with Claude Code and Gemini CLI, plus easy API key setup for Anthropic, Gemini, and OpenAI
- **💻 Editor Sync**: Automatically detect and copy VS Code/Cursor settings & extensions
- **🔐 Secure**: SSH key support for private Git repositories with auto-generated VS Code passwords
- **⚡ Fast Setup**: One command deployment with smart defaults and guided setup wizard
- **🌟 Interactive & Automated**: Full CLI with `-y` flag for CI/CD
- **📁 Flexible**: Upload folders or work with empty environments
- **🔧 Cross-Platform**: Works on macOS, Windows, and Linux (Untested on Linux and Windows)

---

## 🚀 Quick Start

### 📦 Installation

```bash
pip install opencodespace
```

### 🎯 Deploy Your First Environment

```bash
# Interactive setup with editor detection (recommended)
opencodespace

# Non-interactive with defaults (skips editor config)
opencodespace -y

# Deploy specific directory
opencodespace deploy /path/to/project

# Deploy with specific platform
opencodespace deploy --platform fly
```

### 🛑 Managing Environments

```bash
# Stop environment
opencodespace stop

# Remove environment completely  
opencodespace remove

# List available providers
opencodespace --list-providers
```

---

## 💻 CLI Reference

### Commands

| Command | Description |
|---------|-------------|
| `opencodespace` | Deploy current directory with interactive setup |
| `opencodespace deploy [path]` | Deploy specific directory |
| `opencodespace stop [path]` | Stop the environment |
| `opencodespace remove [path]` | Remove the environment |

### Global Options

| Option | Description |
|--------|-------------|
| `-y, --yes` | Skip interactive prompts, use defaults (no editor config) |
| `--list-providers` | Show available deployment providers |
| `-v, --version` | Show version information |

### Examples

```bash
# Full interactive setup with editor detection
opencodespace

# Quick deployment with defaults (no editor sync)
opencodespace -y

# Deploy to specific platform
opencodespace deploy --platform local

# Deploy with editor configuration for specific directory
opencodespace deploy /path/to/my-project
```

---

## ⚙️ Configuration

Note: Run the interactive setup wizard to generate `.opencodespace/config.toml`

### Configuration Options

| Option | Default | Description |
|--------|---------|-------------|
| `name` | Auto-generated | Environment name |
| `platform` | `"local"` | Deployment platform (`local` or `fly`) |
| `upload_folder` | `true` | Upload current directory to container |
| `git_branching` | `true` | Enable Git branch management |
| `dockerfile` | `"Dockerfile"` | Custom Dockerfile name |
| `vscode_password` | Auto-generated | VS Code/Coder access password |
| `api_keys` | `[]` | Legacy environment variables list (use `ai_api_keys` instead) |
| `ai_api_keys.ANTHROPIC_API_KEY` | `""` | Anthropic (Claude) API key |
| `ai_api_keys.GEMINI_API_KEY` | `""` | Google Gemini API key |
| `ai_api_keys.OPENAI_API_KEY` | `""` | OpenAI (ChatGPT) API key |

### Editor Configuration Options

| Option | Default | Description |
|--------|---------|-------------|
| `vscode_config.copy_settings` | `false` | Copy editor settings to remote |
| `vscode_config.copy_extensions` | `false` | Install extensions in remote |
| `vscode_config.detected_editors` | `[]` | List of detected editors |
| `vscode_config.*_settings_path` | `null` | Path to local settings file |
| `vscode_config.*_extensions_list` | `[]` | List of extensions to install |

---

## 🛠 Requirements

### For Local Development
- **Python 3.7+**
- **Docker** - [Install Docker Desktop](https://www.docker.com/get-started)

### For Fly.io Deployment  
- **Python 3.7+**
- **flyctl** - [Install flyctl](https://fly.io/docs/hands-on/install-flyctl/)

### For Editor Configuration Sync
- **VS Code** and/or **Cursor** installed locally (optional)
- Extensions accessible via `code --list-extensions` or `cursor --list-extensions`

---

## 🎯 Usage Scenarios

### 🏠 Local Development with Editor Sync

Perfect for testing with your complete development setup:

```bash
# Interactive setup with editor detection
opencodespace

# Manual configuration for local platform
opencodespace deploy --platform local
```

Your remote environment will have:
- ✅ All your installed extensions  
- ✅ Your settings.json configuration
- ✅ Your themes and preferences
- ✅ Language-specific settings

### ☁️ Cloud Development with Full Setup

Deploy to Fly.io with your complete editor configuration:

```bash
# Interactive setup for cloud deployment
opencodespace

# Configure platform during setup
> Select platform: fly.io

# Access your fully configured environment
# at https://your-app.fly.dev
```

### 🤖 AI Development Environment

Pre-configured with AI tools, automatic password generation, and your editor setup:

```bash
# Full setup with AI tools and editor config
opencodespace

# During interactive setup, you'll configure:
# - Secure auto-generated VS Code password
# - VS Code/Cursor settings & extensions  
# - AI API keys (Anthropic, Gemini, OpenAI)
# - Git repository access
# - SSH keys for private repos
```

Your environment will include:
- ✅ **Secure Access**: Auto-generated password for VS Code/Coder
- ✅ **AI Integration**: API keys available as environment variables
- ✅ **Complete Setup**: Your editor preferences and extensions

### 🔒 Private Repositories with Editor Sync

Secure access to private repos with your development environment:

```bash
# Interactive setup handles everything
opencodespace

# Setup wizard will:
# 1. Detect your editors
# 2. Offer to copy settings/extensions
# 3. Configure SSH keys for Git access
# 4. Set up repository cloning
```

### 🚀 Team Development Environments

Share consistent development environments:

```bash
# Each team member gets the same setup
opencodespace

# Everyone can optionally overlay their own:
# - Editor preferences  
# - Extension sets
# - Personal settings
```

---

## ⚠️ Important Notes

### Secure Access

- **Auto-Generated Passwords**: VS Code/Coder passwords are automatically generated during setup
- **Password Storage**: Passwords are saved in your `.opencodespace/config.toml` for reference
- **Password Display**: The password is displayed prominently during setup and after deployment

### AI API Keys Configuration

- **Structured Setup**: AI API keys are now configured in the dedicated `[ai_api_keys]` section
- **Environment Variables**: Keys are automatically available as environment variables in your container
- **Supported Services**: Anthropic (Claude), Google Gemini, and OpenAI (ChatGPT)
- **Optional Configuration**: All AI API keys are optional and can be configured later

### Editor Configuration

- **Interactive Mode**: Editor detection and configuration only happens during interactive setup
- **Non-Interactive Mode**: Use `opencodespace -y` to skip editor configuration for CI/CD
- **Multiple Editors**: If both VS Code and Cursor are detected, you can choose to copy from both
- **Extension Compatibility**: Cursor extensions are compatible with VS Code and will be installed

### Empty Workspace Warning

When both SSH key and folder upload are disabled:

```bash
⚠️  Warning: No SSH key provided and folder upload disabled.
   The container will start with an empty workspace and no git access.
   Consider enabling folder upload or providing an SSH key for git operations.
```

### Container Names

- **Local**: `opencodespace-{name}`
- **Fly.io**: Uses the app name directly

---

## 🔧 Development

### Package Structure

```
opencodespace/
├── src/opencodespace/           # Modern src layout
│   ├── main.py                  # CLI with editor detection
│   ├── providers/               # Platform providers
│   └── .opencodespace/         # Docker templates with editor setup
├── setup.py                    # Package configuration
└── README.md                   # This file
```

### AI API Keys Configuration

During interactive setup, you can configure AI API keys for popular services:

- **Anthropic (Claude)**: For Claude AI development assistance
- **Google Gemini**: For Google's Gemini AI models
- **OpenAI (ChatGPT)**: For OpenAI's GPT models

These keys are securely stored in your config and available as environment variables in your development environment, making it easy to use AI tools directly in your code.

## 🔨 Development & Building

This project includes a comprehensive build system with multiple interfaces for development tasks.

### Quick Development Setup

```bash
git clone https://github.com/ngramai/opencodespace.git
cd opencodespace

# Install dependencies and package in development mode
make install
# or: python dev-build.py install
# or: ./build.sh install

# Run quick tests during development
make test-quick
# or: python dev-build.py test --quick
# or: ./build.sh test-quick
```

### Build System Overview

Three equivalent interfaces for development tasks:

- **`python dev-build.py [command]`** - Feature-rich Python script (cross-platform)
- **`make [target]`** - Traditional Makefile interface (Unix/Linux)
- **`./build.sh [command]`** - Simple shell script wrapper

### Available Commands

| Command | Description |
|---------|-------------|
| `install` | Install dependencies and package in development mode |
| `test` | Run the complete test suite |
| `test-quick` | Run quick tests (recommended for development) |
| `clean` | Clean build artifacts and cache files |
| `build` | Build package for distribution |
| `lint` | Run code quality checks |
| `all` | Run complete build pipeline |

### Examples

```bash
# Development workflow
make install          # Set up development environment
make test-quick      # Test your changes
make all            # Full build pipeline before PR

# Building for distribution
make clean
make build

# Get help
python dev-dev-build.py help
make help
./build.sh help
```

For detailed documentation, see [BUILD.md](BUILD.md).

---

## 🤝 Contributing

1. Fork the repository
2. Create a feature branch (`git checkout -b feature/amazing-feature`)
3. Commit your changes (`git commit -m 'Add amazing feature'`)
4. Push to the branch (`git push origin feature/amazing-feature`)
5. Open a Pull Request

---

## 📄 License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

---

**❤️ from [ngram](https://ngram.com)**

