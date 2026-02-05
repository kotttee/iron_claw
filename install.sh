#!/bin/bash

# --- IronClaw Global Installer ---
set -e # Stop on first error

# --- Color Codes ---
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

echo -e "${BLUE}--- Starting IronClaw Installation ---${NC}"

# --- 1. Environment Setup ---
echo -e "\n${YELLOW}Step 1: Setting up Python environment...${NC}"
if ! command -v python3.13 &> /dev/null && ! (command -v python3 &> /dev/null && [[ $(python3 -c 'import sys; print(sys.version_info >= (3,13))') == "True" ]]); then
    echo -e "${RED}Error: Python 3.13+ is required.${NC}"
    exit 1
fi
PYTHON_CMD=$(command -v python3.13 || command -v python3)

VENV_DIR="venv"
if [ ! -d "$VENV_DIR" ]; then
    $PYTHON_CMD -m venv $VENV_DIR
    echo "Virtual environment created."
fi

source "$VENV_DIR/bin/activate"
pip install --upgrade pip
pip install -r requirements.txt
echo -e "${GREEN}✔ Dependencies installed successfully.${NC}"

# --- 2. Wrapper Script Creation ---
echo -e "\n${YELLOW}Step 2: Creating the runner script...${NC}"
PROJECT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" &> /dev/null && pwd )"
RUNNER_SCRIPT="$PROJECT_DIR/ironclaw_runner.sh"

cat > "$RUNNER_SCRIPT" <<- EOL
#!/bin/bash
# This script ensures that the IronClaw application runs from the correct directory with the correct environment.
set -e
DIR="\$( cd "\$( dirname "\${BASH_SOURCE[0]}" )" &> /dev/null && pwd )"
source "\$DIR/venv/bin/activate"
cd "\$DIR" # Change CWD to the project root
python "\$DIR/main.py" "\$@"
EOL

chmod +x "$RUNNER_SCRIPT"
echo -e "${GREEN}✔ Runner script created at '$RUNNER_SCRIPT'.${NC}"

# --- 3. Global Installation ---
echo -e "\n${YELLOW}Step 3: Global Command Installation...${NC}"
if [[ $EUID -eq 0 ]]; then
   SUDO_CMD=""
else
   SUDO_CMD="sudo"
fi

read -p "Do you want to install 'ironclaw' as a global system command? (y/n) " -n 1 -r
echo
if [[ $REPLY =~ ^[Yy]$ ]]; then
    INSTALL_PATH="/usr/local/bin/ironclaw"
    echo "Attempting to create a symbolic link at '$INSTALL_PATH'."
    echo "This may require administrator privileges."

    if $SUDO_CMD ln -sf "$RUNNER_SCRIPT" "$INSTALL_PATH"; then
        echo -e "\n${GREEN}✔ Success! IronClaw is now installed globally.${NC}"
        echo -e "You can now run commands like ${BLUE}'ironclaw start'${NC} or ${BLUE}'ironclaw settings'${NC} from any folder."
    else
        echo -e "\n${RED}Global installation failed.${NC}"
        echo "You can still run the agent by executing the local runner script:"
        echo -e "${BLUE}./ironclaw_runner.sh start${NC}"
    fi
else
    echo -e "\nSkipping global installation."
    echo "To run the agent, use the local runner script:"
    echo -e "${BLUE}./ironclaw_runner.sh start${NC}"
fi

# --- 4. Final Setup ---
echo -e "\n${YELLOW}Step 4: Final Configuration...${NC}"
CONFIG_FILE="$PROJECT_DIR/data/config.json"
if [ ! -f "$CONFIG_FILE" ]; then
    echo "Configuration file not found. Running initial setup wizard..."
    ./ironclaw_runner.sh setup
else
    echo -e "${GREEN}✔ Existing configuration found.${NC}"
fi

echo -e "\n${BLUE}--- Installation Complete ---${NC}"
echo "To get started, try running: ${GREEN}ironclaw start${NC}"
