from pydantic import Field
from src.core.interfaces import ComponentConfig

class FileToolConfig(ComponentConfig):
    enabled: bool = Field(True, description="Whether the file management tool is active.")
    max_file_size_mb: int = Field(5, description="Maximum file size (in MB) that the tool can read/write.")
    allow_delete: bool = Field(False, description="Whether the tool is allowed to delete files.")
