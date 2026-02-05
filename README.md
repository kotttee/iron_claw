# IronClaw

A modular, open-source AI Agent Platform with a persistent, self-correcting core.

**Repository:** [https://github.com/kotttee/iron_claw](https://github.com/kotttee/iron_claw)

## Features

*   **One-Line Install:** A single command to deploy on a fresh Debian/Ubuntu server, including dependency handling.
*   **Global CLI:** Manage your agent from anywhere with `ironclaw start`, `ironclaw settings`, etc.
*   **Persistent Identity:** The agent's persona (`ai.md`) and user profile (`user.md`) are loaded on every run.
*   **Self-Correcting Logic:** The core router can analyze tool failures and retry, allowing the agent to overcome errors.
*   **Hidden Installation:** All files are stored neatly in `$HOME/.iron_claw`.

## Quick Start: The One-Line Installer

To install and run IronClaw on a compatible system (Debian, Ubuntu), simply run the following command in your terminal. It will automatically check for dependencies (like `git` and `python3.13-venv`), install them, clone the repository to a hidden `.iron_claw` directory, and guide you through the setup.

```bash
sudo curl -sSL https://raw.githubusercontent.com/kotttee/iron_claw/main/install.sh | bash
```

## Usage

Once installed, you can manage the agent from any terminal window:

*   **Start the agent:**
    ```bash
    ironclaw start
    ```

*   **Access settings:**
    ```bash
    ironclaw settings
    ```

*   **Update to the latest version:**
    ```bash
    ironclaw update
    ```

## Manual Access

If you need to access the project files directly, they are located in the hidden directory:
```bash
cd ~/.iron_claw
```
