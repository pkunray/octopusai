from crewai import Flow, Agent, Task, Crew, Process
from crewai.flow.flow import start, listen
from crewai_tools import DirectoryReadTool, FileReadTool
from pydantic import BaseModel
import json
import octopusai.tools.langchain_github as langchain_gh
import octopusai.tools.git_tool as git_tool

class FlowState(BaseModel):
    """State model"""
    repo: str = ""
    pr_number: int = 0
    requirement_id: str | None = None
    repo_url: str | None = None
    repo_dir: str | None = None
    pr_details: dict | None = None
    pr_diff: str | None = None
    pr_branch: str | None = None
    code_review_results: str | None = None


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
    def get_pr_details(self):
        pr = langchain_gh.GetPullRequest()
        pr_details = pr._run(repo=self.state.repo, pr_number=self.state.pr_number)
        pr_branch = f"pr-{self.state.pr_number}"
        print(f"Pull Request Details: {pr_details}")
        self.state.pr_details = pr_details
        self.state.pr_branch = pr_branch
        return pr_details

    @listen(get_pr_details)
    def clone_repository(self):
        print(f"Cloning repository: {self.state.repo_url}")
        git = git_tool.Clone(self.state.repo_url)
        repo_dir = git._run()
        print("Repository cloned successfully to:", repo_dir)
        self.state.repo_dir = repo_dir
        return repo_dir 

    @listen(clone_repository)
    def get_pr_diff(self):
        print(f"Getting diff for PR: {self.state.pr_number}")
        git = git_tool.Diff()
        diff = git._run(repo_dir=self.state.repo_dir, pr_number=self.state.pr_number, pr_branch=self.state.pr_branch, incremental=True)
        print(f"{'>' * 30 } Diff {'>' * 30 }")
        print(diff)
        print(f"{'<' * 30 } Diff {'<' * 30 }")
        self.state.pr_diff = diff
        return diff
    
    #### @listen(clone_repository)
    #### def get_repo_languages(self):

    @listen(clone_repository)
    def checkout_pr_branch(self):
        print(f"Checking out PR branch: {self.state.pr_branch}")
        git = git_tool.Checkout()
        git._run(repo_dir=self.state.repo_dir, branch_name=self.state.pr_branch)
        print(f"Checked out to branch: {self.state.pr_branch}")
        return self.state.pr_branch
    
    @listen(get_pr_diff)
    def bug_detection(self):

        code_reviewer = Agent(
            role="Senior Code Reviewer",
            goal="""
            - Review pull requests for logic errors, edge cases, and code quality issues.
            """,
            backstory="""
            You are a senior code reviewer with more than 10 years of experience in identifying bugs and improving code quality.
            Your specialty is white-box testing, you are also proficient in Python.
            Your mission is to ensure the highest quality standards in the codebase.
            """,
            tools=[
                DirectoryReadTool(),
                FileReadTool(),
            ],
            verbose=True,
            llm="gpt-4o",
            allow_code_execution=True,
            code_execution_mode="safe", # Use Docker
            cache=False,
        )

        # Create tasks
        code_review = Task(
            description=f"""Review the pull request #{self.state.pr_number} in the repository 
            located in {self.state.repo_dir} for bugs and code quality issues.
            The PR diff is as follows:\n{self.state.pr_diff}\nDeep dive into the diff and only check the code changes made in this PR.
            Run the code in a safe environment to make sure your findings are accurate.
            Provide a detailed report of the findings, including explanations for each identified issue.
            """,
            expected_output="A list of identified bugs and code quality issues with explanations in markdown format.",
            agent=code_reviewer
        )

        research_crew = Crew(
            agents=[code_reviewer],
            tasks=[code_review],
            process=Process.sequential,
            verbose=True
        )
        result = research_crew.kickoff()
        print(result.token_usage)
        self.state.code_review_results = result.raw
        return result.raw

def main(inputs=None):
    flow = BugDetectionFlow()
    # Inputs will be assigned to the flow state by CrewAI
    flow.kickoff(inputs=inputs)
    #flow.plot("bug_detection_flow")
    #print("Flow visualization saved to bug_detection_flow.html")

if __name__ == "__main__":
    main()