from pathlib import Path

class KnowledgeManager:
    """
    Manages the reading and writing of Markdown files in the knowledge base.

    This class centralizes all file system operations for the 'data/knowledge'
    directory, providing a clean interface for tools to interact with stored notes.
    """
    def __init__(self, base_dir: str = "data/knowledge"):
        self.base_path = Path(base_dir)
        self.base_path.mkdir(exist_ok=True, parents=True)

    def _get_safe_path(self, filename: str) -> Path | None:
        """
        Validates a filename and resolves it to a safe path within the base directory.

        Prevents directory traversal attacks by ensuring the resolved path is
        strictly within the intended knowledge base directory.

        Args:
            filename: The base name of the file (without extension).

        Returns:
            A Path object if the path is safe, otherwise None.
        """
        # Sanitize filename to prevent malicious characters
        safe_filename = "".join(c for c in filename if c.isalnum() or c in ('_', '-'))
        
        if not safe_filename:
            return None

        # Construct the full path and resolve any '..' or '.' parts.
        file_path = (self.base_path / f"{safe_filename}.md").resolve()

        # Check if the resolved path is a child of the base path.
        if self.base_path.resolve() in file_path.parents:
            return file_path
        
        return None

    def write_note(self, filename: str, content: str) -> str:
        """
        Writes or overwrites a note in the knowledge base.

        Args:
            filename: The name of the note to write.
            content: The Markdown content to save.

        Returns:
            A status message indicating success or failure.
        """
        file_path = self._get_safe_path(filename)
        if not file_path:
            return f"Error: Invalid filename '{filename}'. Use alphanumeric characters, hyphens, or underscores."

        try:
            file_path.write_text(content, encoding="utf-8")
            return f"Successfully wrote note to '{file_path.name}'."
        except IOError as e:
            return f"Error writing note: {e}"

    def read_note(self, filename: str) -> str:
        """
        Reads a note from the knowledge base.

        Args:
            filename: The name of the note to read.

        Returns:
            The content of the note if found, otherwise an error message.
        """
        file_path = self._get_safe_path(filename)
        if not file_path:
            return f"Error: Invalid filename '{filename}'."

        if not file_path.exists():
            return f"Error: Note '{file_path.name}' not found."

        try:
            return file_path.read_text(encoding="utf-8")
        except IOError as e:
            return f"Error reading note: {e}"

    def list_notes(self) -> list[str]:
        """
        Lists all available notes in the knowledge base.

        Returns:
            A list of note filenames (without the .md extension).
        """
        return [p.stem for p in self.base_path.glob("*.md")]
