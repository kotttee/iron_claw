import importlib
import inspect
from pathlib import Path
from typing import List, Type, TypeVar

T = TypeVar("T")

def load_plugins(base_class: Type[T], plugin_type: str) -> List[Type[T]]:
    """
    Dynamically and recursively finds and imports all plugins of a specific type.

    This function scans a subdirectory under 'src/plugins/' (e.g., 'channels', 'tools'),
    imports all Python files found in its directory tree, and returns a list of classes
    that are subclasses of the provided 'base_class'.

    Args:
        base_class: The base class to filter for (e.g., BaseChannel, BaseTool).
        plugin_type: The subdirectory name under 'src/plugins/' where the plugins reside.

    Returns:
        A list of imported plugin classes that can be instantiated.
    """
    plugins: List[Type[T]] = []
    plugin_root_dir = Path("src/plugins")
    plugin_dir = plugin_root_dir / plugin_type
    
    if not plugin_dir.exists() or not plugin_dir.is_dir():
        return []

    # Use rglob to find all .py files recursively
    for file in sorted(plugin_dir.rglob("*.py")):
        if file.name.startswith("_"):
            continue

        # Construct the module name from the file path
        # e.g., src/plugins/tools/system/bash.py -> src.plugins.tools.system.bash
        relative_path = file.relative_to(plugin_root_dir).with_suffix('')
        module_name = "src.plugins." + ".".join(relative_path.parts)

        try:
            module = importlib.import_module(module_name)
            
            for _, item in inspect.getmembers(module, inspect.isclass):
                if (
                    item.__module__ == module_name
                    and issubclass(item, base_class)
                    and item is not base_class
                ):
                    plugins.append(item)
        except ImportError as e:
            print(f"Warning: Could not import plugin from '{module_name}'. Error: {e}")
            
    return plugins
