import inspect
from types import ModuleType
from rich.console import Console

from src.core.providers.base import BaseProvider

console = Console()

def validate_tool(module: ModuleType) -> bool:
    """
    Validates a custom tool module.

    A valid tool must:
    1. Have a callable function named 'run'.
    2. The 'run' function must have a non-empty docstring (__doc__).

    Args:
        module: The imported tool module to validate.

    Returns:
        True if the tool is valid, False otherwise.
    """
    if not hasattr(module, 'run') or not callable(getattr(module, 'run')):
        console.print(f"[yellow]Warning:[/yellow] Custom tool '{module.__name__}' is invalid: Missing a callable 'run' function.")
        return False

    run_func = getattr(module, 'run')
    if not run_func.__doc__ or not run_func.__doc__.strip():
        console.print(f"[yellow]Warning:[/yellow] Custom tool '{module.__name__}' is invalid: The 'run' function is missing a docstring, which is required for the LLM to understand its purpose.")
        return False
    
    return True

def validate_provider(module: ModuleType) -> bool:
    """
    Validates a custom provider module.

    A valid provider must:
    1. Contain a class that inherits from BaseProvider.
    2. This class must implement the abstract methods 'list_models' and 'chat'.

    Args:
        module: The imported provider module to validate.

    Returns:
        True if the provider is valid, False otherwise.
    """
    found_valid_provider = False
    for name, obj in inspect.getmembers(module, inspect.isclass):
        if issubclass(obj, BaseProvider) and obj is not BaseProvider:
            # Check if abstract methods are implemented.
            # An instantiated object will throw a TypeError if they are not.
            try:
                # We don't need a real API key for this check, just need to see if it instantiates.
                # The __init__ of BaseProvider will handle the check.
                obj(api_key="validation_check")
                found_valid_provider = True
                break 
            except (TypeError, ValueError):
                # TypeError if abstract methods not implemented, ValueError if __init__ is wrong.
                continue

    if not found_valid_provider:
        console.print(f"[yellow]Warning:[/yellow] Custom provider '{module.__name__}' is invalid: It must contain a class that inherits from 'BaseProvider' and implements all its abstract methods.")
        return False

    return True
