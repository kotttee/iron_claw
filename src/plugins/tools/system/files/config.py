from src.core.interfaces import ComponentConfig

class FileToolConfig(ComponentConfig):
    max_file_size_mb: int = 5
    allow_delete: bool = False
