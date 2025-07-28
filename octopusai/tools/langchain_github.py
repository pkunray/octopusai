from typing import Type
from langchain_community.utilities.github import GitHubAPIWrapper
from crewai.tools import BaseTool
from pydantic import Field, BaseModel

class RepoInput(BaseModel):
    repo: str = Field(..., description="owner/repo string")

class ListOpenPullRequests(BaseTool):
    name: str = "List Open Pull Requests"
    description: str = "Retrieve a list of open pull requests from a GitHub repository."
    args_schema: Type[BaseModel] = RepoInput

    def _run(self, repo: str) -> str:
        gh = GitHubAPIWrapper(github_repository=repo)
        return gh.list_open_pull_requests()


class PullRequestInput(BaseModel):
    repo: str = Field(..., description="owner/repo string")
    pr_number: int = Field(..., description="Pull request number")

class GetPullRequest(BaseTool):
    name: str = "Get Pull Request"
    description: str = "Retrieve title, body, comments and commits of a specific pull request from a GitHub repository."
    args_schema: Type[BaseModel] = PullRequestInput

    def _run(self, repo: str, pr_number: int) -> str:
        gh = GitHubAPIWrapper(github_repository=repo)
        return gh.get_pull_request(pr_number)

class ListPullRequestFiles(BaseTool):
    name: str = "List Pull Request Files"
    description: str = "List files changed in a specific pull request."
    args_schema: Type[BaseModel] = PullRequestInput

    def _run(self, repo: str, pr_number: int) -> str:
        gh = GitHubAPIWrapper(github_repository=repo)
        return gh.list_pull_request_files(pr_number)

class CreatePullRequestInput(BaseModel):
    repo: str = Field(..., description="owner/repo string")
    pr_query: str = Field(..., description="Pull request query")
    src_branch: str = Field(..., description="Source branch for the pull request")
    dest_branch: str = Field(..., description="Destination branch for the pull request")

class CreatePullRequest(BaseTool):
    name: str = "Create Pull Request"
    description: str = "Create a pull request in a GitHub repository."
    args_schema: Type[BaseModel] = CreatePullRequestInput

    def _run(self, repo: str, pr_query: str, src_branch: str, dest_branch: str) -> str:
        gh = GitHubAPIWrapper(github_repository=repo, active_branch=src_branch, github_base_branch=dest_branch)
        return gh.create_pull_request(pr_query=pr_query)