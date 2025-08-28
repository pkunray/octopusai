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
            temp_dir = tempfile.mkdtemp(prefix="apr_", dir="/Users/kun/tmp/octopusai")
            git.Repo.clone_from(self.repository_url, temp_dir)
            return temp_dir
        except Exception as e:
            return f"Error cloning repository: {str(e)}"

class Diff(BaseTool):
    name: str = "Git Diff Tool"
    description: str = "Generates a diff of the changes in the cloned repository."

    def _run(self, repo_dir: str, pr_number: int, pr_local_branch: str, base_branch: str = "main", incremental: bool = False) -> str:
        """
        Generate a diff of the changes in the cloned repository.

        """
        remote_name = "origin"
        try:
            # Go to repo
            repo = git.Repo(repo_dir)
            assert not repo.bare, "Repository is invalid"
            # Fetch the PR from GitHub
            fetch_ref = f"pull/{pr_number}/head:{pr_local_branch}"
            repo.git.fetch(remote_name, fetch_ref)
            # Generate the diff
            if incremental:
                diff = repo.git.diff(f"{base_branch}...{pr_local_branch}")
            else:
                 diff = repo.git.diff(f"{base_branch}..{pr_local_branch}")
            return diff
        except Exception as e:
            return f"Error generating diff: {str(e)}"

class Checkout(BaseTool):
    name: str = "Git Checkout Tool"
    description: str = "Checks out a specific branch in the cloned repository."

    def _run(self, repo_dir: str, branch_name: str) -> str:
        """
        Check out a specific branch in the cloned repository.
        """
        try:
            repo = git.Repo(repo_dir)
            repo.git.checkout(branch_name)
            return f"Checked out to branch: {branch_name}"
        except Exception as e:
            return f"Error checking out branch: {str(e)}"

class PatchApply(BaseTool):
    name: str = "Git Patch Apply Tool"
    description: str = "Applies a patch to the current working directory."

    def _run(self, repo_dir: str, patch_content: str) -> str:
        """
        Apply a patch to the current working directory.
        """
        try:
            repo = git.Repo(repo_dir)
            patch_file = tempfile.NamedTemporaryFile(delete=False, suffix=".patch")
            patch_file.write(patch_content.encode())
            patch_file.close()
            repo.git.apply(patch_file.name)
            return f"Patch applied successfully."
        except Exception as e:
            return f"Error applying patch: {str(e)}"

class Commit(BaseTool):
    name: str = "Git Commit Tool"
    description: str = "Commits changes in the current working directory with a specified message."

    def _run(self, repo_dir: str, commit_message: str) -> str:
        """
        Commit changes in the current working directory with a specified message.
        """
        try:
            repo = git.Repo(repo_dir)
            repo.git.add(A=True)  # Stage all changes
            repo.index.commit(commit_message)
            return f"Changes committed with message: {commit_message}"
        except Exception as e:
            return f"Error committing changes: {str(e)}"

class Push(BaseTool):
    name: str = "Git Push Tool"
    description: str = "Pushes changes to the remote repository."

    def _run(self, repo_dir: str, branch_name: str) -> str:
        """
        Push changes to the remote repository.
        """
        try:
            repo = git.Repo(repo_dir)
            origin = repo.remote(name='origin')
            origin.push(branch_name)
            return f"Changes pushed to branch: {branch_name}"
        except Exception as e:
            return f"Error pushing changes: {str(e)}"