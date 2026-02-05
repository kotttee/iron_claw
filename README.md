# IronClaw

A modular, open-source AI Agent Platform powered by LLMs.

**Repository:** [https://github.com/kotttee/iron_claw](https://github.com/kotttee/iron_claw)

## Core Philosophy

1.  **"Everything is a Plugin":** Channels, Tools, and Memory systems are all designed to be modular plugins.
2.  **"No-Code Setup":** A user-friendly interactive CLI wizard (`setup.py`) handles all configuration, eliminating the need for manual JSON/YAML editing.
3.  **"Markdown Native":** All agent memory and logs are stored in human-readable Markdown format.
4.  **"English Only":** The entire codebase, UI, and documentation are in English.

## Quickstart

To get started, simply run the installer script. It handles everything from dependency checking to launching the application.

```bash
bash install.sh
```

This script will:
1.  Verify that Python 3.13+ is installed.
2.  Create a local Python virtual environment in the `venv/` directory.
3.  Install all required dependencies from `requirements.txt`.
4.  Launch an interactive setup wizard to configure API keys and select/configure channels (like Console or Telegram).
5.  Start the agent.

After the first run, you can start the agent directly with:
```bash
source venv/bin/activate
python main.py
```
