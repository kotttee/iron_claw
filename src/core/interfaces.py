import json
import sqlite3
import asyncio
from abc import ABC, abstractmethod
from pathlib import Path
from typing import Generic, TypeVar, Type, Any, Optional, Union
import questionary
from pydantic import BaseModel, Field
from rich.console import Console
from src.core.paths import DATA_ROOT, PLUGINS_DIR

console = Console()

class ComponentConfig(BaseModel):
    enabled: bool = Field(True, description="Whether the component is active and should be loaded.")

TConfig = TypeVar("TConfig", bound=ComponentConfig)

class CronConfig(ComponentConfig):
    cron: str = Field(..., description="Cron expression for scheduling (e.g., '0 8 * * *' for daily at 8 AM).")

class IntervalConfig(ComponentConfig):
    interval_seconds: int = Field(..., description="Fixed interval in seconds between executions.")

class BaseComponent(ABC, Generic[TConfig]):
    """
    Base class for all plugins and channels.
    Manages configuration via Pydantic and provides a SQLite connection.
    """
    name: str
    config_class: Type[TConfig]
    component_type: str = "plugin"  # "plugin", "channel", or "scheduler"

    def __init__(self):
        # Use the last part of the name for the data directory (e.g., 'system/read_file' -> 'read_file')
        # This ensures that components in subdirectories store data in a flat structure under data/plugins/
        folder_name = self.name.split('/')[-1]
        self.data_dir = DATA_ROOT / "plugins" / folder_name
            
        self.config_path = self.data_dir / "config.json"
        self.db_path = self.data_dir / "storage.db"
        self._db_conn: Optional[sqlite3.Connection] = None
        self.config = self.load_config()

    @property
    def db(self) -> sqlite3.Connection:
        """Returns a sqlite3 connection to storage.db in the component's data folder."""
        if self._db_conn is None:
            self.data_dir.mkdir(parents=True, exist_ok=True)
            self._db_conn = sqlite3.connect(self.db_path)
            self._db_conn.row_factory = sqlite3.Row
        return self._db_conn

    def load_config(self) -> TConfig:
        """Loads configuration from config.json or returns default config."""
        if self.config_path.exists():
            try:
                data = json.loads(self.config_path.read_text(encoding="utf-8"))
                return self.config_class(**data)
            except Exception as e:
                console.print(f"[bold red]Error loading config for {self.name}: {e}. Falling back to defaults.[/bold red]")
                return self.config_class()
        
        # If config doesn't exist, save the default one
        default_config = self.config_class()
        self.save_config_instance(default_config)
        return default_config

    def save_config(self):
        """Saves current configuration to config.json."""
        self.save_config_instance(self.config)

    def save_config_instance(self, config_inst: TConfig):
        """Saves a specific configuration instance to config.json."""
        self.data_dir.mkdir(parents=True, exist_ok=True)
        self.config_path.write_text(config_inst.model_dump_json(indent=4), encoding="utf-8")

    def update_config(self, new_data: dict):
        """Updates configuration with new data and saves it."""
        self.config = self.config_class(**{**self.config.model_dump(), **new_data})
        self.save_config()

    def run_setup_wizard(self):
        """Automatically generates an interactive setup wizard based on the config Pydantic model."""
        console.print(f"\n[bold cyan]Settings for {self.name}:[/bold cyan]")
        new_values = {}
        
        for field_name, field_info in self.config_class.model_fields.items():
            # Skip internal fields if any start with underscore
            if field_name.startswith('_'): continue
            
            description = field_info.description or field_name
            current_val = getattr(self.config, field_name)
            
            if isinstance(current_val, bool):
                val = questionary.confirm(f"{description}?", default=current_val).ask()
            elif isinstance(current_val, int):
                val = questionary.text(f"{description}:", default=str(current_val), 
                                       validate=lambda text: text.isdigit() or "Must be an integer").ask()
                if val is not None: val = int(val)
            else:
                val = questionary.text(f"{description}:", default=str(current_val)).ask()
            
            if val is not None:
                new_values[field_name] = val

        if new_values:
            self.update_config(new_values)
            console.print(f"[green]✔ {self.name} configuration updated.[/green]")

    def shutdown(self):
        """Gracefully close resources."""
        if self._db_conn:
            self._db_conn.close()
            self._db_conn = None

    @abstractmethod
    async def healthcheck(self) -> tuple[bool, str]:
        """Performs a health check of the component."""
        pass

class BaseChannel(BaseComponent[TConfig]):
    component_type = "channel"

    @abstractmethod
    async def start(self, router: Any):
        """Starts the channel's main loop."""
        pass

    @abstractmethod
    async def send_message(self, text: str, target: Any = None):
        """Sends a message through the channel."""
        pass

class BaseTool(BaseComponent[TConfig]):
    component_type = "plugin"

    @abstractmethod
    async def execute(self, **kwargs) -> Any:
        """Executes the tool's logic."""
        pass

    def format_output(self, result: Any) -> str:
        """Formats the tool's result for the user."""
        return str(result)

class BaseScheduler(BaseComponent[TConfig]):
    component_type = "scheduler"

    @abstractmethod
    async def run_iteration(self, router: Any):
        """Runs a single iteration of the scheduled task."""
        pass
