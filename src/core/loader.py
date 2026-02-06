import importlib.util
from pathlib import Path
from typing import Dict, Any, Callable, Type

from rich.console import Console

from src.core.validator import validate_tool, validate_provider
from src.core.providers.base import BaseProvider

console = Console()

# Define the base path for custom modules
CUSTOM_DIR = Path(__file__).parent.parent / "custom"

def _load_modules_from_path(path: Path) -> Dict[str, Any]:
    """Helper to load all valid python modules from a given directory path."""
    if not path.is_dir():
        return {}

    modules = {}
    for file in sorted(path.glob("*.py")):
        if file.name.startswith("__"):
            continue
        
        module_name = file.stem
        try:
            spec = importlib.util.spec_from_file_location(module_name, file)
            if spec and spec.loader:
                module = importlib.util.module_from_spec(spec)
                spec.loader.exec_module(module)
                modules[module_name] = module
            else:
                console.print(f"[red]Error:[/red] Could not create module spec for {file.name}")
        except Exception as e:
            console.print(f"[red]Error loading custom module '{file.name}': {e}[/red]")
    
    return modules

def load_custom_tools() -> Dict[str, Callable]:
    """
    Scans `src/custom/tools`, validates, and returns a dictionary of tool functions.
    
    Returns:
        A dictionary mapping the tool's name (filename) to its 'run' function.
    """
    console.print("[bold blue]Loading custom tools...[/bold blue]")
    tools_path = CUSTOM_DIR / "tools"
    raw_modules = _load_modules_from_path(tools_path)
    
    valid_tools = {}
    for name, module in raw_modules.items():
        if validate_tool(module):
            valid_tools[name] = getattr(module, 'run')
            console.print(f"  [green]✔[/green] Loaded custom tool: '{name}'")
            
    return valid_tools

def load_custom_providers() -> Dict[str, Type[BaseProvider]]:
    """
    Scans `src/custom/providers`, validates, and returns a dictionary of provider classes.

    Returns:
        A dictionary mapping the provider's name (filename) to its provider class.
    """
    console.print("[bold blue]Loading custom providers...[/bold blue]")
    providers_path = CUSTOM_DIR / "providers"
    raw_modules = _load_modules_from_path(providers_path)
    
    valid_providers = {}
    for name, module in raw_modules.items():
        if validate_provider(module):
            # Find the class that inherits from BaseProvider within the module
            for item_name, obj in module.__dict__.items():
                if isinstance(obj, type) and issubclass(obj, BaseProvider) and obj is not BaseProvider:
                    valid_providers[name] = obj
                    console.print(f"  [green]✔[/green] Loaded custom provider: '{name}'")
                    break # Assume one provider per file
                    
    return valid_providers
