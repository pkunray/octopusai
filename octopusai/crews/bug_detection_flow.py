from crewai import Flow, Agent, Task, Crew, Process
from crewai.flow.flow import start, listen
from crewai_tools import DirectoryReadTool, FileReadTool, FileWriterTool
from pydantic import BaseModel
import json
import octopusai.tools.langchain_github as langchain_gh
import octopusai.tools.git_tool as git_tool
from crewai_tools import MCPServerAdapter

class FlowState(BaseModel):
    """State model"""
    repo: str = "",
    pr_number: int = 0
    active_branch: str = "test",
    requirement_id: str | None = None
    repo_url: str | None = None
    repo_dir: str | None = None
    pr_details: dict | None = None
    pr_diff: str | None = None
    pr_local_branch: str | None = None
    pull_request_query: str | None = None
    #code_fix_patch: str | None = None


class BugDetectionFlow(Flow[FlowState]):
    """
    A Predifined Workflow utilizing CrewAI's Flow with Crew.
    Which can be integrated into CI/CD pipelines built with commonly adopted tools like Jenkins or GitHub Actions.
    """

    mcp_server_params = {
        "url": "http://localhost:8000/mcp", 
        "transport": "streamable-http"
    }
    get_prd_tool = None

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
        pr_local_branch = f"pr-{self.state.pr_number}"
        print(f"Pull Request Details: {pr_details}")
        self.state.pr_details = pr_details
        self.state.pr_local_branch = pr_local_branch
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
        diff = git._run(repo_dir=self.state.repo_dir, pr_number=self.state.pr_number, pr_local_branch=self.state.pr_local_branch, incremental=True)
        print(f"{'>' * 30 } Diff {'>' * 30 }")
        print(diff)
        print(f"{'<' * 30 } Diff {'<' * 30 }")
        self.state.pr_diff = diff
        return diff
    
    #### @listen(clone_repository)
    #### def get_repo_languages(self):

    @listen(clone_repository)
    def checkout_pr(self):
        print(f"Checking out PR branch: {self.state.pr_local_branch}")
        git = git_tool.Checkout()
        git._run(repo_dir=self.state.repo_dir, branch_name=self.state.pr_local_branch)
        print(f"Checked out to branch: {self.state.pr_local_branch}")
        return self.state.pr_local_branch
    
    @listen(get_pr_diff)
    def bug_detection(self):

        reviewer_tools = [
            DirectoryReadTool(),
            FileReadTool(), 
        ]
        if self.get_prd_tool:
            reviewer_tools.append(self.get_prd_tool)

        print("Reviewer tools:", reviewer_tools)
    
        # Agents
        code_reviewer = Agent(
            role="Senior Code Reviewer",
            goal="""
            - Review pull requests for logic errors, edge cases, and code quality issues.
            """,
            backstory="""
            You are a senior code reviewer with more than 10 years of experience in identifying bugs and improving code quality.
            Your specialty is white-box testing, you are also proficient in Python.
            Your are good at understanding the product requirement documents and how the code should work.
            Your mission is to ensure the highest quality standards in the codebase.
            """,
            tools=reviewer_tools,
            verbose=True,
            llm="gpt-3.5-turbo",
            allow_code_execution=True,
            code_execution_mode="safe", # Use Docker
            cache=False,
        )

        python_developer = Agent(
            role="Senior Python Developer",
            goal="""
            - Develop high-quality Python code and fix bugs reported in the code review for the codebase.
            - Compile proper commit messages, pull request queries and other necessary information for the code changes.
            """,
            backstory="""
            You are a senior Python developer with more than 8 years of experience in building scalable applications.
            Your specialty is backend development, and you are proficient in Python and related frameworks.
            Your mission is to deliver high-quality code that meets the project's requirements.
            """,
            tools=[
                DirectoryReadTool(),
                FileReadTool(),
                FileWriterTool(),
            ],
            verbose=True,
            llm="gpt-4o",
            allow_code_execution=True,
            code_execution_mode="safe", # Use Docker
            cache=False,
            max_retry_limit=3,
            #allow_delegation=True, 
        )
        git_specialist = Agent(
            role="Git Specialist",
            goal="""
            - Execute Git commands and operations to manage the repository effectively.
            """,
            backstory="""
            You are a Git specialist with extensive experience in managing Git repositories.
            Your mission is to ensure smooth Git operations and assist the team in managing code changes effectively.
            """,
            tools=[
                git_tool.PatchApply(),
                git_tool.Commit(),
                git_tool.Push(),
                langchain_gh.CreatePullRequest(),
            ],
            verbose=True,
            cache=False,
            max_iter=10,
            allow_code_execution=True,
            code_execution_mode="safe", 
            #allow_delegation=True, 
        )

        # Tasks
        code_review = Task(
            description=f"""Review the pull request #{self.state.pr_number} in the repository 
            located in {self.state.repo_dir} for bugs and code quality issues.
            Your should refer to the product requirement document if available, to make sure the code changes are aligned with the requirements.
            The product requirement document is available in the tool {self.get_prd_tool.name}, you should understand that the only required field of this tool is requirement_id {self.state.requirement_id}.
            The PR diff is as follows:\n{self.state.pr_diff}\nDeep dive into the diff and only check the code changes made in this PR.
            Run the code in a safe environment to make sure your findings are accurate.
            Provide a detailed report of the findings, including explanations for each identified issue.
            """,
            expected_output="A list of identified bugs and code quality issues with explanations in markdown format.",
            agent=code_reviewer,
            human_input=True,
        )

        code_fix_generation = Task(
            description=f"""Based on the code review results, generate fixes for the identified bugs and code quality issues.
            Implement the fixes in the repository located in {self.state.repo_dir}.
            Ensure that the fixes are well-tested and maintain the code quality standards.
            When you write the code to the file, you should preserve the original file structure and only modify the lines that need fixing, 
            especially be careful with indentation and line breaks.
            """,
            expected_output="A unified diff patch with the fixes applied to the codebase.",
            agent=python_developer,
            context=[code_review],
            human_input=True
        )
        code_fix_patch = Task(
            description=f"""Apply the generated patch to the repository located in {self.state.repo_dir}.
            Ensure that the patch is applied correctly and does not introduce any new issues.
            """, # If the patch is not applicable, you should inform python_developer agent to regenerate the patch.
            expected_output="Patch applied successfully.",
            agent=git_specialist,
            context=[code_fix_generation],

        )
        commit_message_generation = Task(
            description=f"""Generate a commit message for the applied patch.
            Ensure that the commit message follows the conventional commit format with 'fix: ' prefix, and describes the changes made, other than just "fixes bugs".
            """,
            expected_output="A pure commit message in conventional commit format.",
            agent=python_developer,
            context=[code_fix_generation],
            human_input=True
        )
        commit_and_push = Task(
            description=f"""Commit the changes in the repository located in {self.state.repo_dir} with the generated commit message.
            Ensure that the commit is made to branch of {self.state.pr_local_branch} and pushed to the remote repository.
            """,
            expected_output="Changes committed and pushed successfully.",
            agent=git_specialist,

            context=[commit_message_generation],
        )

        pull_request_query_generation = Task(
            description=f"""Generate a pull request query including title, body according to the changes made in the repository located in {self.state.repo_dir}.
            Refer to the code changes made in the patch and the commit message for context.
            """,
            expected_output="A pull request query string including title, body and other necessary information. " \
            "The title and body is separated by a newline character." \
            "Don't explicitly mentiong which part is title and which part is body, just output the query string.",
            agent=python_developer,
            context=[code_fix_patch, commit_and_push, commit_message_generation],
            human_input=True
        )

        crew = Crew(
            agents=[code_reviewer, python_developer, git_specialist],
            tasks=[code_review, 
                   code_fix_generation, 
                    #code_fix_patch, 
                   commit_message_generation, 
                   commit_and_push, 
                   pull_request_query_generation],
            process=Process.sequential,
            verbose=True,
            cache=False,
        )
        result = crew.kickoff()
        self.state.pull_request_query = pull_request_query_generation.output.raw
        print(result.token_usage)
        return result.raw
    
    @listen(bug_detection)
    def create_pull_request(self):
        print(f"Creating pull request with query: {self.state.pull_request_query}")
        pr = langchain_gh.CreatePullRequest()
        pr_response = pr._run(repo=self.state.repo, 
                              pr_query=self.state.pull_request_query, 
                              src_branch=self.state.pr_local_branch, 
                              dest_branch=self.state.active_branch)
        print(f"Pull Request created successfully: {pr_response}")
        print(f"State: {json.dumps(self.state.model_dump(), indent=2)}")
        return pr_response

def main(inputs=None, mcp_tools=None):
    flow = BugDetectionFlow()
    print("mcp_tools:", mcp_tools)
    if mcp_tools:
        flow.get_prd_tool = mcp_tools["get_prd"]
    # Inputs will be assigned to the flow state by CrewAI
    flow.kickoff(inputs=inputs)
    flow.plot("bug_detection_flow")
    print("Flow visualization saved to bug_detection_flow.html")

if __name__ == "__main__":
    with MCPServerAdapter(BugDetectionFlow.mcp_server_params) as mcp_tools:
        main(mcp_tools=mcp_tools)       