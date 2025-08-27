import os
from typing import Any, Optional, Type, List

from crewai.tools import BaseTool
from pydantic import BaseModel, Field


class FixedDirectoryReadToolSchema(BaseModel):
    """Input for DirectoryReadTool."""


class DirectoryReadToolSchema(FixedDirectoryReadToolSchema):
    """Input for DirectoryReadTool."""

    directory: str = Field(..., description="Mandatory directory to list content")
    ignored: Optional[List[str]] = Field(
        default_factory=list,
        description="List of directories to ignore (e.g. ['.git', '__pycache__'])"
    )


class DirectoryReadTool(BaseTool):
    name: str = "List files in directory"
    description: str = (
        "A tool that can be used to recursively list a directory's content."
    )
    args_schema: Type[BaseModel] = DirectoryReadToolSchema
    directory: Optional[str] = None
    ignored: List[str] = []

    def __init__(self, directory: Optional[str] = None, ignored: Optional[List[str]] = None, **kwargs):
        super().__init__(**kwargs)
        if directory is not None:
            self.directory = directory
            self.description = f"A tool that can be used to list {directory}'s content."
            self.args_schema = FixedDirectoryReadToolSchema
            self._generate_description()
        if ignored:
            self.ignored = ignored

    def _run(
        self,
        **kwargs: Any,
    ) -> Any:
        directory = kwargs.get("directory", self.directory)
        ignored = kwargs.get("ignored", self.ignored) or []

        if directory[-1] == "/":
            directory = directory[:-1]

        files_list = []
        for root, dirs, files in os.walk(directory):
            dirs[:] = [d for d in dirs if d not in ignored]

            for filename in files:
                rel_path = os.path.join(root, filename).replace(directory, "").lstrip(os.path.sep)
                files_list.append(f"{directory}/{rel_path}")

        files = "\n- ".join(files_list)
        return f"File paths: \n-{files}"
