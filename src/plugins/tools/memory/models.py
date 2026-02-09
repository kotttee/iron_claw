from pydantic import BaseModel, Field

class AddFactArgs(BaseModel):
    fact: str = Field(..., description="A long-term fact about the user or the world to remember.")

class ClearHistoryArgs(BaseModel):
    pass
