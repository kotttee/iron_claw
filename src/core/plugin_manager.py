import importlib.util
import inspect
import pkgutil
from pathlib import Path
from types import ModuleType
from typing import Dict, List, Any, TYPE_CHECKING

from src.interfaces.tool import BaseTool

if TYPE_CHECKING:
    from src.core.ai.router import Router

# Define the base directories for plugins
PLUGIN_BASE_DIRS = [
    Path(__file__).parent.parent / "plugins",
    Path(__file__).parent.parent / "custom",
]

# --- Plugin Discovery and Loading ---

def load_plugin_from_module(module: ModuleType, module_name: str, category: str, router: "Router") -> Any:
    """
    Attempts to load a plugin from a given module.
    It can be a class-based plugin or a functional one.
    """
    # Check for class-based plugins first
    for name, obj in inspect.getmembers(module, inspect.isclass):
        if issubclass(obj, BaseTool) and obj is not BaseTool:
            try:
                # Check if the constructor requires a 'router' argument
                sig = inspect.signature(obj.__init__)
                if 'router' in sig.parameters:
                    return obj(router=router)
                else:
                    return obj()
            except Exception:
                # Could fail if __init__ has other required args
                # Optional: log this error
                # print(f"Could not instantiate class-based plugin '{name}': {e}")
                pass

    # Check for functional plugins (a module with a 'run' function)
    if hasattr(module, 'run') and callable(module.run):
        # Create a simple object to represent the functional plugin
        plugin_obj = type(f"{module_name}_plugin", (), {
            'name': module_name,
            'description': inspect.getdoc(module.run) or "No description provided.",
            'category': category,
            'is_enabled': lambda: True, # Functional tools are enabled by default
            'run': module.run
        })()
        return plugin_obj
    
    return None

def get_all_plugins(router: "Router") -> Dict[str, List[Any]]:
    """
    Scans predefined plugin directories, dynamically imports modules,
    and discovers all valid plugins (both class-based and functional).
    """
    all_plugins: Dict[str, List[Any]] = {"channels": [], "tools": []}
    
    for base_dir in PLUGIN_BASE_DIRS:
        if not base_dir.exists():
            continue
        
        # Iterate through subdirectories like 'channels' and 'tools'
        for category_dir in base_dir.iterdir():
            if not category_dir.is_dir():
                continue
            
            category = category_dir.name
            if category not in all_plugins:
                continue

            for module_loader, name, ispkg in pkgutil.walk_packages([str(category_dir)]):
                if ispkg:
                    continue

                try:
                    spec = module_loader.find_spec(name)
                    if not spec or not spec.loader:
                        continue
                    
                    module = importlib.util.module_from_spec(spec)
                    spec.loader.exec_module(module)
                    
                    module_short_name = name.split('.')[-1]
                    plugin = load_plugin_from_module(module, module_short_name, category, router)
                    if plugin:
                        all_plugins[category].append(plugin)
                        
                except Exception:
                    # Optional: log errors for debugging plugin loading issues
                    # print(f"Could not load plugin '{name}' from '{category}': {e}")
                    pass

    # Sort plugins by name for consistent ordering
    for category in all_plugins:
        all_plugins[category].sort(key=lambda p: p.name)

    return all_plugins

def find_plugin(name: str, plugin_type: str, router: "Router") -> Any | None:
    """
    Finds a specific plugin by name within a given type (category).
    """
    all_plugins = get_all_plugins(router)
    if plugin_type not in all_plugins:
        return None

    for plugin in all_plugins[plugin_type]:
        if plugin.name == name:
            return plugin

    return None
