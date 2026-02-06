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

def load_plugin_from_module(module: ModuleType, module_name: str, category: str, router: "Router" = None) -> Any:
    """
    Attempts to load a plugin from a given module.
    It can be a class-based plugin or a functional one.
    """
    found_plugins = []
    
    # Check for class-based plugins first
    for name, obj in inspect.getmembers(module, inspect.isclass):
        # We check for BaseTool for tools, but channels might use a different base class or just be classes
        if category == "tools":
            if issubclass(obj, BaseTool) and obj is not BaseTool:
                try:
                    # Check if the constructor requires specific arguments
                    sig = inspect.signature(obj.__init__)
                    kwargs = {}
                    if 'router' in sig.parameters and router:
                        kwargs['router'] = router
                    if 'scheduler' in sig.parameters and router and hasattr(router, 'scheduler_manager'):
                        kwargs['scheduler'] = router.scheduler_manager
                    
                    found_plugins.append(obj(**kwargs))
                except Exception:
                    pass
        elif category == "channels":
            # For channels, we just want the class itself so it can be instantiated later by the Kernel
            from src.interfaces.channel import BaseChannel
            if issubclass(obj, BaseChannel) and obj is not BaseChannel:
                found_plugins.append(obj)

    if found_plugins:
        return found_plugins if len(found_plugins) > 1 else found_plugins[0]

    # Check for functional plugins (a module with a 'run' function) - only for tools
    if category == "tools" and hasattr(module, 'run') and callable(module.run):
        # Create a simple object to represent the functional plugin
        plugin_obj = type(f"{module_name}_plugin", (), {
            'name': module_name,
            'description': inspect.getdoc(module.run) or "No description provided.",
            'category': category,
            'is_enabled': lambda: True, # Functional tools are enabled by default
            'run': module.run,
            'execute': lambda self, **kwargs: module.run(**kwargs)
        })()
        return plugin_obj
    
    return None

def get_all_plugins(router: "Router" = None) -> Dict[str, List[Any]]:
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

            # We use walk_packages to find all modules in the category directory
            # We need to set the prefix to ensure correct relative imports if any
            prefix = f"src.plugins.{category}."
            if base_dir.name == "custom":
                prefix = f"src.custom.{category}."
                
            for module_loader, name, ispkg in pkgutil.walk_packages([str(category_dir)], prefix=prefix):
                if ispkg:
                    continue

                try:
                    # name is e.g. "src.plugins.tools.memory.notebook"
                    module = importlib.import_module(name)
                    
                    module_short_name = name.split('.')[-1]
                    plugin = load_plugin_from_module(module, module_short_name, category, router)
                    if plugin:
                        if isinstance(plugin, list):
                            all_plugins[category].extend(plugin)
                        else:
                            all_plugins[category].append(plugin)
                        
                except Exception as e:
                    # Optional: log errors for debugging plugin loading issues
                    # print(f"Error loading {name}: {e}")
                    pass

    # Sort plugins by name for consistent ordering
    for category in all_plugins:
        all_plugins[category].sort(key=lambda p: getattr(p, 'name', getattr(p, '__name__', str(p))))

    return all_plugins

def find_plugin(name: str, plugin_type: str, router: "Router" = None) -> Any | None:
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
