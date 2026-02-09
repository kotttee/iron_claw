from pydantic import BaseModel, Field

class UpdateIdentityArgs(BaseModel):
    bio: str = Field(..., description="The complete updated identity and settings in Markdown format.")
