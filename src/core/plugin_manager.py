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

            # Scan each subdirectory/file in the category directory
            for item in category_dir.iterdir():
                if item.name.startswith("__"):
                    continue
                
                module_name = None
                if item.is_dir() and (item / "__init__.py").exists():
                    module_name = f"src.{base_dir.name}.{category_dir.name}.{item.name}"
                elif item.is_dir() and (item / "plugin.py").exists():
                    module_name = f"src.{base_dir.name}.{category_dir.name}.{item.name}.plugin"
                elif item.is_dir() and (item / "tool.py").exists():
                    module_name = f"src.{base_dir.name}.{category_dir.name}.{item.name}.tool"
                elif item.suffix == ".py":
                    module_name = f"src.{base_dir.name}.{category_dir.name}.{item.stem}"
                
                if not module_name:
                    continue

                try:
                    module = importlib.import_module(module_name)
                    
                    # Look for a class that inherits from the appropriate base class
                    target_base = BaseComponent
                    if category_dir.name == "channels":
                        target_base = BaseChannel
                    elif category_dir.name in ["tools", "plugins"]:
                        target_base = BaseTool
                    elif category_dir.name == "schedulers":
                        target_base = BaseScheduler

                    for _, obj in inspect.getmembers(module, inspect.isclass):
                        if issubclass(obj, target_base) and obj not in (BaseComponent, BaseTool, BaseChannel, BaseScheduler):
                            # For directory-based plugins, we often export the class in __init__.py
                            # We want to instantiate it once.
                            instance = obj()
                            
                            # Add to the appropriate list
                            if isinstance(instance, BaseChannel):
                                all_components["channels"].append(instance)
                            elif isinstance(instance, BaseTool):
                                all_components["tools"].append(instance)
                            elif isinstance(instance, BaseScheduler):
                                all_components["schedulers"].append(instance)
                except Exception as e:
                    # console.print(f"Error loading plugin {module_name}: {e}")
                    pass

    return all_components
