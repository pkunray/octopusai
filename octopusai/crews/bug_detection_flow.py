from crewai import Flow
from crewai.flow.flow import start, listen
from pydantic import BaseModel
import json
import octopusai.tools.langchain_github as langchain_gh
import octopusai.tools.git_clone as git_clone

class FlowState(BaseModel):
    """State model"""
    repo: str = ""
    pr_number: int = 0
    requirement_id: str | None = None
    repo_url: str | None = None


class BugDetectionFlow(Flow[FlowState]):
    """
    A Predifined Workflow utilizing CrewAI's Flow with Crew.
    Which can be integrated into CI/CD pipelines built with commonly adopted tools like Jenkins or GitHub Actions.
    """
    @start()
    def initialize(self):
        print("Initializing Bug Detection Flow...")
        print(json.dumps(self.state.model_dump(), indent=2))
        self.state.repo_url = f"https://github.com/{self.state.repo}"
        return self.state

    
    @listen(initialize)
    def get_pull_request(self):
        pull_request = langchain_gh.GetPullRequest()
        result = pull_request._run(repo=self.state.repo, pr_number=self.state.pr_number)
        print(f"Pull Request Details: {result}")

    @listen(initialize)
    def clone_repository(self):
        print(f"Cloning repository: {self.state.repo_url}")
        path = git_clone.git_clone_tool(repository_url=self.state.repo_url)
        print("Repository cloned successfully to:", path)


def main(inputs=None):
    flow = BugDetectionFlow()
    # Inputs will be assigned to the flow state by CrewAI
    flow.kickoff(inputs=inputs)
    #flow.plot("bug_detection_flow")
    #print("Flow visualization saved to bug_detection_flow.html")

if __name__ == "__main__":
    main()