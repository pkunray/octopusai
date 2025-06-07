import tempfile
import git
from crewai.tools import tool

@tool("Clone GitHub Repository")
def git_clone_tool(repository_url: str) -> str:
    """
    Clone a GitHub repository to a temporary directory.
    
    Args:
        repository_url: The GitHub repository URL to clone
        
    Returns:
        The path to the cloned repository
    """
    try:
        temp_dir = tempfile.mkdtemp(prefix="bug_scan_")
        
        git.Repo.clone_from(repository_url, temp_dir)
        
        return f"Repository cloned successfully to: {temp_dir}"
    except Exception as e:
        return f"Error cloning repository: {str(e)}"