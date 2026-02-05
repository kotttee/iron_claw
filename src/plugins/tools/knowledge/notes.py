from typing import Type

from pydantic import BaseModel, Field

from src.core.knowledge import KnowledgeManager
from src.interfaces.tool import BaseTool

# Instantiate the manager once to be used by all tool instances.
knowledge_manager = KnowledgeManager()

# --- Write Note Tool ---

class WriteNoteArgs(BaseModel):
    filename: str = Field(..., description="The name of the note file (e.g., 'meeting_summary'). Alphanumeric, hyphens, and underscores only.")
    content: str = Field(..., description="The Markdown content to write into the note.")

class WriteNoteTool(BaseTool):
    """A tool to write or overwrite a Markdown note in the knowledge base."""
    @property
    def name(self) -> str:
        return "knowledge/write_note"

    @property
    def description(self) -> str:
        return "Creates or overwrites a Markdown note in the user's knowledge base. Use this to remember information."

    @property
    def args_schema(self) -> Type[BaseModel]:
        return WriteNoteArgs

    def execute(self, filename: str, content: str) -> str:
        """Delegates the writing operation to the KnowledgeManager."""
        return knowledge_manager.write_note(filename, content)

# --- Read Note Tool ---

class ReadNoteArgs(BaseModel):
    filename: str = Field(..., description="The name of the note file to read from the knowledge base.")

class ReadNoteTool(BaseTool):
    """A tool to read a Markdown note from the knowledge base."""
    @property
    def name(self) -> str:
        return "knowledge/read_note"

    @property
    def description(self) -> str:
        return "Reads a Markdown note from the knowledge base."

    @property
    def args_schema(self) -> Type[BaseModel]:
        return ReadNoteArgs

    def execute(self, filename: str) -> str:
        """Delegates the reading operation to the KnowledgeManager."""
        return knowledge_manager.read_note(filename)

# --- List Notes Tool ---

class ListNotesArgs(BaseModel):
    pass  # No arguments needed

class ListNotesTool(BaseTool):
    """A tool to list all available notes in the knowledge base."""
    @property
    def name(self) -> str:
        return "knowledge/list_notes"

    @property
    def description(self) -> str:
        return "Lists all available notes in the knowledge base, returning a list of filenames."

    @property
    def args_schema(self) -> Type[BaseModel]:
        return ListNotesArgs

    def execute(self) -> str:
        """Delegates the listing operation to the KnowledgeManager."""
        notes = knowledge_manager.list_notes()
        if not notes:
            return "No notes found in the knowledge base."
        return "Available notes:\n- " + "\n- ".join(notes)
