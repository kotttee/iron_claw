#!/bin/bash

# --- IronClaw Bulletproof Bootstrap Installer ---
# Installs to a hidden directory ($HOME/.iron_claw) and handles system dependencies.
set -e # Stop on first error

# --- Helpers & Constants ---
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
BLUE='\033[0;34m'
NC='\033[0m'
PROJECT_DIR="$HOME/.iron_claw"

info() { echo -e "${BLUE}$1${NC}"; }
success() { echo -e "${GREEN}$1${NC}"; }
warn() { echo -e "${YELLOW}$1${NC}"; }
error() { echo -e "${RED}$1${NC}"; exit 1; }

# --- 1. System & Dependency Checks ---
info "--- Step 1: Checking System Dependencies ---"

# OS Detection & Sudo Check
if [ -f /etc/os-release ]; then
    . /etc/os-release
    OS=$ID
else
    error "Cannot detect operating system."
fi

SUDO_CMD=""
if [[ $EUID -ne 0 ]]; then
    SUDO_CMD="sudo"
    if ! command -v sudo &> /dev/null; then
        error "This script requires 'sudo' for non-root users. Please install it first."
    fi
fi

# Git Check & Auto-Install
if ! command -v git &> /dev/null; then
    warn "Git not found. Attempting to install..."
    case $OS in
        ubuntu|debian) $SUDO_CMD apt-get update && $SUDO_CMD apt-get install -y git ;;
        *) error "Unsupported OS for automatic Git installation. Please install Git manually." ;;
    esac
    if ! command -v git &> /dev/null; then
        error "Git installation failed. Please install it manually and re-run."
    fi
fi
success "✔ Git is installed."

# Python & Venv Check with Auto-Fix for Debian/Ubuntu
PYTHON_CMD=""
if command -v python3.13 &> /dev/null && python3.13 -m venv --help &> /dev/null; then
    PYTHON_CMD="python3.13"
elif command -v python3 &> /dev/null && [[ $(python3 -c 'import sys; print(sys.version_info >= (3,13))') == "True" ]] && python3 -m venv --help &> /dev/null; then
    PYTHON_CMD="python3"
fi

if [ -z "$PYTHON_CMD" ]; then
    warn "Python 3.13+ with the 'venv' module is not found or is incomplete."
    if [[ "$OS" == "ubuntu" || "$OS" == "debian" ]]; then
        warn "Attempting to install Python 3.13 and required modules via apt..."
        $SUDO_CMD apt-get update
        $SUDO_CMD apt-get install -y python3.13-full python3.13-venv python3.13-dev
        if command -v python3.13 &> /dev/null && python3.13 -m venv --help &> /dev/null; then
            PYTHON_CMD="python3.13"
        else
            error "Python 3.13 installation failed. Please install it manually."
        fi
    else
        error "Please install Python 3.13+ and its 'venv' module for your OS."
    fi
fi
success "✔ Python 3.13+ with venv module is ready."

# --- 2. Clone or Update Repository ---
info "\n--- Step 2: Cloning/Updating Repository in '$PROJECT_DIR' ---"
if [ -d "$PROJECT_DIR" ]; then
    info "Existing installation found. Pulling latest changes..."
    cd "$PROJECT_DIR"
    git pull
else
    info "Cloning repository..."
    git clone https://github.com/kotttee/iron_claw.git "$PROJECT_DIR"
    cd "$PROJECT_DIR"
fi
success "✔ Repository is up to date."

# --- 3. Project Setup ---
info "\n--- Step 3: Setting up Python Virtual Environment ---"
$PYTHON_CMD -m venv venv
source venv/bin/activate
pip install --upgrade pip
pip install -r requirements.txt
success "✔ Python dependencies installed."

# --- 4. Wrapper & Global Command ---
info "\n--- Step 4: Installing Global 'ironclaw' Command ---"
RUNNER_SCRIPT="$PROJECT_DIR/ironclaw_runner.sh"
cat > "$RUNNER_SCRIPT" <<- EOL
#!/bin/bash
set -e
DIR="\$HOME/.iron_claw"
source "\$DIR/venv/bin/activate"
cd "\$DIR"
python "\$DIR/main.py" "\$@"
EOL
chmod +x "$RUNNER_SCRIPT"

INSTALL_PATH="/usr/local/bin/ironclaw"
warn "Attempting to create a symbolic link at '$INSTALL_PATH'. This may require sudo."
if $SUDO_CMD ln -sf "$RUNNER_SCRIPT" "$INSTALL_PATH"; then
    success "✔ IronClaw installed globally."
else
    error "Global installation failed. You can run the agent via '$RUNNER_SCRIPT'"
fi

# --- 5. Final Configuration ---
info "\n--- Step 5: Final Configuration Check ---"
if [ ! -f "$PROJECT_DIR/data/config.json" ]; then
    warn "No configuration found. Running initial setup wizard..."
    $RUNNER_SCRIPT setup
else
    success "✔ Existing configuration found."
fi

# --- Completion ---
echo
success "-------------------------------------------"
success "  IronClaw Installation Complete!          "
success "-------------------------------------------"
info "You can now run the agent from any folder using:"
info "  ironclaw start"
info "  ironclaw settings"
info "  ironclaw update"
echo
