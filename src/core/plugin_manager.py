import importlib
import inspect
from pathlib import Path
from typing import Dict, List, Any, TYPE_CHECKING
from src.core.interfaces import BaseComponent, BaseTool, BaseChannel

if TYPE_CHECKING:
    from src.core.ai.router import Router

PLUGIN_BASE_DIRS = [
    Path(__file__).parent.parent,
]

def get_all_plugins(router: "Router" = None) -> Dict[str, List[Any]]:
    """
    Scans plugin directories and returns instantiated components.
    Categories: channels, tools, schedulers.
    """
    all_components: Dict[str, List[Any]] = {
        "channels": [],
        "tools": [],
    }
    
    for base_dir in PLUGIN_BASE_DIRS:
        if not base_dir.exists():
            continue
        
        # Ищем компоненты в папках 'plugins' и 'custom' внутри 'src'
        for folder_name in ["plugins", "custom"]:
            category_path = base_dir / folder_name
            if not category_path.exists() or not category_path.is_dir():
                continue

            # Рекурсивно ищем все .py файлы во всех подпапках
            for py_file in category_path.rglob("*.py"):
                if py_file.name.startswith("__") or py_file.name == "config.py":
                    continue

                # Формируем полный путь импорта, начиная с 'src'
                # base_dir.parent — это корень проекта (над папкой src)
                relative_path = py_file.relative_to(base_dir.parent)
                module_name = ".".join(relative_path.with_suffix("").parts)

                try:
                    module = importlib.import_module(module_name)
                    
                    for _, obj in inspect.getmembers(module, inspect.isclass):
                        # Проверяем, что класс определен именно в этом модуле, а не импортирован
                        if obj.__module__ != module.__name__:
                            continue

                        if issubclass(obj, BaseTool) and obj is not BaseTool:
                            all_components["tools"].append(obj())
                        elif issubclass(obj, BaseChannel) and obj is not BaseChannel:
                            all_components["channels"].append(obj())

                except Exception:
                    pass

    return all_components
