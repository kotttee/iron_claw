#!/bin/bash

# --- IronClaw Bulletproof Bootstrap Installer (v3) ---
# Implements an aggressive dependency fix for Debian/Ubuntu systems.
# Installs to a hidden directory ($HOME/.iron_claw).
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
info "--- Step 1: Checking System & Dependencies ---"

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

# Aggressive Dependency Fix for Debian/Ubuntu
if [[ "$OS" == "ubuntu" || "$OS" == "debian" ]]; then
    info "Debian/Ubuntu detected. Running preemptive dependency installation..."
    $SUDO_CMD apt-get update
    # Install the full suite of tools needed for Python, Git, and compiling packages.
    $SUDO_CMD apt-get install -y python3.13-full python3.13-venv python3.13-dev git build-essential
    success "✔ Core system dependencies ensured."
fi

# Verify Python and Venv are now working
PYTHON_CMD="python3.13"
if ! command -v $PYTHON_CMD &> /dev/null; then
    error "Python 3.13 could not be found or installed. Please install it manually."
fi

info "Verifying Python virtual environment functionality..."
if ! $PYTHON_CMD -m venv test_env_check --without-pip &> /dev/null; then
    error "CRITICAL ERROR: The 'venv' module for Python 3.13 is still missing or broken. Please fix your Python installation."
fi
rm -rf test_env_check
success "✔ Python environment is healthy."

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
