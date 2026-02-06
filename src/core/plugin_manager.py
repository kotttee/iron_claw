import importlib.util
import inspect
import pkgutil
from pathlib import Path
from typing import Dict, List, Type

from src.core.interfaces import ConfigurablePlugin

# Define the directories where plugins are located
# Assuming a structure like src/plugins/channels and src/plugins/tools
PLUGIN_DIRS = [
    Path(__file__).parent.parent / "plugins" / "channels",
    Path(__file__).parent.parent / "plugins" / "tools",
    Path(__file__).parent.parent / "custom" / "tools",
]

def get_all_plugins() -> Dict[str, List[ConfigurablePlugin]]:
    """
    Scans predefined plugin directories, dynamically imports modules,
    and discovers all classes that inherit from ConfigurablePlugin.

    Returns:
        A dictionary categorizing instantiated plugins into 'channels' and 'tools'.
    """
    all_plugins: Dict[str, List[ConfigurablePlugin]] = {"channels": [], "tools": []}
    
    for directory in PLUGIN_DIRS:
        if not directory.exists() or not directory.is_dir():
            continue

        for finder, name, ispkg in pkgutil.iter_modules([str(directory)]):
            if ispkg:
                continue # Skip packages for now, look for modules

            try:
                spec = finder.find_spec(name)
                if not spec or not spec.loader:
                    continue
                
                module = importlib.util.module_from_spec(spec)
                spec.loader.exec_module(module)

                # Find all classes in the module that are subclasses of ConfigurablePlugin
                for _, obj in inspect.getmembers(module, inspect.isclass):
                    if issubclass(obj, ConfigurablePlugin) and obj is not ConfigurablePlugin:
                        # Instantiate the plugin
                        instance = obj()
                        
                        # Categorize it
                        if instance.category == "channel":
                            all_plugins["channels"].append(instance)
                        elif instance.category == "tool":
                            all_plugins["tools"].append(instance)
                            
            except Exception:
                # Silently fail for now, or add logging for debugging
                # print(f"Could not load plugin '{name}': {e}")
                pass

    # Sort plugins by name for consistent ordering
    for category in all_plugins:
        all_plugins[category].sort(key=lambda p: p.name)

    return all_plugins
