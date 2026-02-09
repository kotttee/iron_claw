import importlib
import inspect
import pkgutil
from pathlib import Path
from typing import Dict, List, Any, TYPE_CHECKING
from src.core.interfaces import BaseComponent, BaseTool, BaseChannel, BaseScheduler

if TYPE_CHECKING:
    from src.core.ai.router import Router

PLUGIN_BASE_DIRS = [
    Path(__file__).parent.parent / "plugins",
    Path(__file__).parent.parent / "custom",
]

def get_all_plugins(router: "Router" = None) -> Dict[str, List[Any]]:
    """
    Scans plugin directories and returns instantiated components.
    Categories: channels, tools, schedulers.
    """
    all_components: Dict[str, List[Any]] = {
        "channels": [],
        "tools": [],
        "schedulers": []
    }
    
    for base_dir in PLUGIN_BASE_DIRS:
        if not base_dir.exists():
            continue
        
        for category_dir in base_dir.iterdir():
            if not category_dir.is_dir():
                continue
            
            category = category_dir.name
            if category not in all_components:
                if category == "plugins":
                    category = "tools"
                else:
                    continue

            prefix = f"src.{base_dir.name}.{category_dir.name}."
            # We want to walk through all modules and packages
            for _, name, ispkg in pkgutil.walk_packages([str(category_dir)], prefix=prefix):
                try:
                    module = importlib.import_module(name)
                    for _, obj in inspect.getmembers(module, inspect.isclass):
                        # Check if it's a subclass of BaseComponent and not one of the base classes themselves
                        if issubclass(obj, BaseComponent) and obj not in (BaseComponent, BaseTool, BaseChannel, BaseScheduler):
                            # Ensure the class is defined in the module we just imported (avoid duplicates from imports)
                            if obj.__module__ == name:
                                instance = obj()
                                # Only add if enabled
                                if not instance.config.enabled:
                                    continue
                                    
                                if category_dir.name == "channels":
                                    all_components["channels"].append(instance)
                                elif category_dir.name == "tools" or category_dir.name == "plugins":
                                    all_components["tools"].append(instance)
                                elif category_dir.name == "schedulers":
                                    all_components["schedulers"].append(instance)
                except Exception:
                    pass

    return all_components
