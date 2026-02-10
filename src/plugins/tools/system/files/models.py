from pydantic import BaseModel, Field

class ReadFileArgs(BaseModel):
    path: str = Field(..., description="The path to the file. You have access to the entire file system. Prefer paths starting with /IRONCLAW.")

class WriteFileArgs(BaseModel):
    path: str = Field(..., description="The path to the file. You have access to the entire file system. Prefer creating files within the /IRONCLAW directory.")
    content: str = Field(..., description="The content to write to the file.")

class ListFilesArgs(BaseModel):
    path: str = Field(..., description="The path to the directory. You have access to the entire file system. Prefer paths starting with /IRONCLAW.")
