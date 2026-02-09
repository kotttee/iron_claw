from pydantic import BaseModel, Field

class ReadFileArgs(BaseModel):
    path: str = Field(..., description="The relative path to the file within the workspace.")

class WriteFileArgs(BaseModel):
    path: str = Field(..., description="The relative path to the file within the workspace.")
    content: str = Field(..., description="The content to write to the file.")

class ListFilesArgs(BaseModel):
    path: str = Field(..., description="The relative path to the directory within the workspace.")
