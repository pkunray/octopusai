from crewai import Flow, Agent, Task, Crew, Process, LLM
from crewai.tasks.conditional_task import ConditionalTask
from crewai.tasks.task_output import TaskOutput
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
    bug_present: bool = False

gpt3_5 = LLM(
    model="openai/gpt-3.5-turbo",
    temperature=0.0,
)

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

    @listen(clone_repository)
    def checkout_pr(self):
        print(f"Checking out PR branch: {self.state.pr_local_branch}")
        git = git_tool.Checkout()
        git._run(repo_dir=self.state.repo_dir, branch_name=self.state.pr_local_branch)
        print(f"Checked out to branch: {self.state.pr_local_branch}")
        return self.state.pr_local_branch
    
    def _on_review_task_complete(self, output: TaskOutput):
        """Callback function to process task completion"""
        try:
            result = json.loads(output.raw)
            if "hypotheses" in result and len(result["hypotheses"]) > 0:
                self.state.bug_present = True
                print("Bugs detected and bug_present set to True")
            else:
                self.state.bug_present = False
                print("No bugs detected, bug_present remains False")
        except json.JSONDecodeError:
            print("Failed to parse code review output, by default bug_present is False")

    @listen(get_pr_diff)
    def bug_detection(self):

        reviewer_tools = [
            DirectoryReadTool(),
            FileReadTool(), 
        ]
        #if self.get_prd_tool:
            #reviewer_tools.append(self.get_prd_tool)
    
        # Agents
        code_reviewer = Agent(
            role="Senior Code Reviewer",
            goal="""
            - Review pull requests to detect bugs. 
            - Acting as the last line of defense against bugs, other issues like code style, code quality, naming, lacking documentation, lacking tests etc. are not your concerns, 
            only focus on the core logic of the functionality.
            """,
            backstory="""
            You are a senior code reviewer with more than 10 years of experience in identifying bugs.
            Your specialty is white-box testing, you are also proficient in Python.
            """,
            tools=reviewer_tools,
            verbose=True,
            llm=gpt3_5,
            cache=True, #Cache for tool usage,
            allow_delegation=True, 
        )

        python_developer = Agent(
            role="Senior Python Developer",
            goal=""" Fix bugs reported in the code review for the codebase. """,
            backstory="""
            You are a senior Python developer with more than 10 years of experience in Python development.
            """,
            tools=[
                DirectoryReadTool(),
                FileReadTool(),
                FileWriterTool(),
            ],
            verbose=True,
            llm=gpt3_5,
            allow_code_execution=True,
            code_execution_mode="safe",
            cache=False,
            max_retry_limit=3,
            allow_delegation=True, 
        )

        qa_engineer = Agent(
            role="Senior QA Engineer",
            goal="""
            - Ensure the quality of the codebase by writing and executing tests.
            - Identify and report bugs found during testing.
            """,
            backstory="""
            You are a QA engineer with more than 5 years of experience in software testing.
            Your specialty is automated testing, and you are proficient in Python.
            """,
            tools=[
                DirectoryReadTool(),
                FileReadTool(),
            ],
            verbose=True,
            llm=gpt3_5,
            allow_code_execution=True,
            code_execution_mode="safe",
            max_retry_limit=3,
            allow_delegation=True, 
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
                git_tool.Commit(),
                git_tool.Push(),
                langchain_gh.CreatePullRequest(),
            ],
            verbose=True,
            cache=False,
            max_iter=5,
            allow_delegation=False, 
        )
        # Tasks
        code_review = Task(
            description=f"""Review the pull request #{self.state.pr_number} in the repository 
            located in {self.state.repo_dir}, propose specific bug hypotheses.\n
            The PR diff is as follows:\n{self.state.pr_diff}\n
            """,
            expected_output='{"hypotheses":[{"file":"a/foo.py","problematic_code":"...","why":"..."}]}',
            agent=code_reviewer,
            callback=self._on_review_task_complete
        )


        code_fix_generation = ConditionalTask(
            description=f"""Based on the code review results, generate fixes for the identified bugs.
            When writing the code to the file, preserve the original file structure and only modify the lines that need fixing, 
            especially be careful with indentation and line breaks in Python.
            """,
            expected_output='{"files_modified":["a/foo.py"],"note":"what changed and why"}',
            agent=python_developer,
            context=[code_review],
            condition=lambda x: self.state.bug_present  # Only run if bugs are present
        )
        commit_message_generation = ConditionalTask(
            description=f"""Generate a commit message for the code fix.
            Ensure that the commit message follows the conventional commit format with 'fix: ' prefix, and describes the changes made, other than just "fixes bugs".
            """,
            expected_output="A pure commit message in conventional commit format.",
            agent=python_developer,
            context=[code_fix_generation],
            condition=lambda x: self.state.bug_present,
        )
        commit_and_push = ConditionalTask(
            description=f"""Commit the changes in the repository located in {self.state.repo_dir} with the generated commit message.
            Ensure that the commit is made to branch of {self.state.pr_local_branch} and pushed to the remote repository.
            """,
            expected_output='{"commit_and_push_status":"success/false"}',
            agent=git_specialist,
            context=[commit_message_generation],
            condition=lambda x: self.state.bug_present,
        )

        pull_request_query_generation = ConditionalTask(
            description=f"""Generate a pull request query including title, body according to the changes made in the repository located in {self.state.repo_dir}.
            Refer to the code changes made in the code fix and the commit message for context.
            """,
            expected_output="Fix: ...\n" \
            "The PR addresses the following issues:\n" \
            "1. ...\n" \
            "2. ...\n",
            agent=python_developer,
            context=[code_fix_generation, commit_message_generation],
            human_input=True,
            condition=lambda x: self.state.bug_present,
        )

        crew = Crew(
            agents=[code_reviewer, python_developer, qa_engineer, git_specialist],
            tasks=[code_review, 
                   code_fix_generation, 
                   commit_message_generation, 
                   commit_and_push, 
                   pull_request_query_generation],
            process=Process.sequential, # For hierarchical, a manager agent or manager llm must be specified
            #manager_llm="gpt-4o",
            verbose=True,
            cache=False,
            share_crew=True,
            #planning=True
        )
        result = crew.kickoff()
        if pull_request_query_generation.output:
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

if __name__ == "__main__":
    with MCPServerAdapter(BugDetectionFlow.mcp_server_params) as mcp_tools:
        main(mcp_tools=mcp_tools)       