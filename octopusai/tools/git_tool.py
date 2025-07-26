import tempfile
import git
from crewai.tools import BaseTool

class Clone(BaseTool):
    name: str = "Git Clone Tool"
    description: str = "Clones a GitHub repository with the given URL to a temporary directory."
    repository_url: str = ""

    def __init__(self, repository_url: str):
        super().__init__()
        self.repository_url = repository_url

    def _run(self) -> str:
        """
        Clone a GitHub repository to a temporary directory.
        """
        try:
            temp_dir = tempfile.mkdtemp(prefix="octopusai_")
            git.Repo.clone_from(self.repository_url, temp_dir)
            return temp_dir
        except Exception as e:
            return f"Error cloning repository: {str(e)}"

class Diff(BaseTool):
    name: str = "Git Diff Tool"
    description: str = "Generates a diff of the changes in the cloned repository."

    def _run(self, repo_dir: str, pr_number: int, base_branch: str = "main", incremental: bool = False) -> str:
        """
        Generate a diff of the changes in the cloned repository.

        """
        pr_branch = f"pr-{pr_number}"
        remote_name = "origin"
        try:
            # Go to repo
            repo = git.Repo(repo_dir)
            assert not repo.bare, "Repository is invalid"
            # Fetch the PR from GitHub
            fetch_ref = f"pull/{pr_number}/head:{pr_branch}"
            repo.git.fetch(remote_name, fetch_ref)
            # Generate the diff
            if incremental:
                diff = repo.git.diff(f"{base_branch}...{pr_branch}")
            else:
                 diff = repo.git.diff(f"{base_branch}..{pr_branch}")
            return diff
        except Exception as e:
            return f"Error generating diff: {str(e)}"