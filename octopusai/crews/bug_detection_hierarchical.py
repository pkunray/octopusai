import os, sys
from datetime import datetime
import time
import re, subprocess
import json
from typing import Optional, Any, Dict, List
from crewai import Flow, Agent, Task, Crew, Process, LLM
from crewai.flow.flow import start, listen, router
from crewai_tools import FileReadTool, FileWriterTool,SerplyWebSearchTool
from pydantic import BaseModel, Field
import octopusai.tools.langchain_github as langchain_gh
import octopusai.tools.git_tool as git_tool
from octopusai.tools.directory_read import DirectoryReadTool
from octopusai.tools.code_interpreter_with_timeout import CodeInterpreterTool
from crewai_tools import MCPServerAdapter

def _strip_code_fence(s: str) -> str:
    s = s.strip()
    if s.startswith("```"):
        s = re.sub(r"^```[a-zA-Z]*\n?", "", s).strip()
        s = re.sub(r"\n?```$", "", s).strip()
    return s

def _parse_json_strict(raw: str) -> dict:
    text = _strip_code_fence(raw)
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        m = re.search(r"\{.*\}", text, flags=re.DOTALL)
        if not m:
            raise
        return json.loads(m.group(0))

def _repo_has_changes(repo_dir: str) -> bool:
    res = subprocess.run(
        ["git", "-C", repo_dir, "status", "--porcelain"],
        capture_output=True, text=True
    )
    return res.stdout.strip() != ""

def _commit_and_push(repo_dir: str, branch: str, message: str) -> Optional[str]:
    commit = git_tool.Commit()
    push = git_tool.Push()
    commit._run(repo_dir=repo_dir, commit_message=message)
    push._run(repo_dir=repo_dir, branch_name=branch)
    h = subprocess.run(
        ["git", "-C", repo_dir, "rev-parse", "HEAD"],
        capture_output=True, text=True
    )
    return h.stdout.strip() or None

class CrewResultModel(BaseModel):
    bugs_found: bool
    review_results: Optional[Dict[str, Any]] = None
    fixes_applied: List[Dict[str, Any]] = Field(default_factory=list)
    commit_message: Optional[str] = None
    commit_hash: Optional[str] = None
    pull_request_summary: Optional[str] = None
    involved_agents: List[str] = Field(default_factory=list)
    workflow_steps_completed: List[str] = Field(default_factory=list)

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
    pull_request_summary: str | None = None
    bug_present: bool = False
    fixed_files: List[str] = Field(default_factory=list)

llm_default = LLM(
    #model="openai/gpt-3.5-turbo",
    model="openai/gpt-4o",
    temperature=0.0,
    top_p=1.0,
)

llm_planning = LLM(
    model="openai/gpt-4o",
)

llm_manager = LLM(
    model="openai/o3-mini",
)

llm_bug_detection_and_repair = LLM(
    model="openai/gpt-4o",
    temperature=0.1,
)

llm_qa= LLM(
    model="openai/gpt-4o",
    temperature=0.1,
)

llm_git_summary = LLM(
    model="openai/gpt-4o",
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
        pr_local_branch = f"pr-{self.state.pr_number}-fix-{datetime.now().strftime('%y%m%d%H%M%S')}"
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

    @listen(get_pr_diff)
    def checkout_pr(self):
        print(f"Checking out PR branch: {self.state.pr_local_branch}")
        git = git_tool.Checkout()
        git._run(repo_dir=self.state.repo_dir, branch_name=self.state.pr_local_branch)
        print(f"Checked out to branch: {self.state.pr_local_branch}")
        return self.state.pr_local_branch
    
    @router(checkout_pr)
    def bug_detection(self):

        reviewer_tools = [
            DirectoryReadTool(directory=self.state.repo_dir, ignored=[".git", "__pycache__", "json_testcases", "python_testcases"]),
            FileReadTool(), 
            SerplyWebSearchTool()
        ]
        #if self.get_prd_tool:
            #reviewer_tools.append(self.get_prd_tool)
    
        # Manager Agent
        manager = Agent(
            role="Engineering Team Lead",
            goal="""
            Coordinate the bug detection and fixing process by managing the team of specialists.
            Ensure proper workflow execution and quality standards.
            """,
            backstory="""
            You are an experienced engineering team lead with 15+ years of experience managing 
            development teams and ensuring code quality. You understand the full software 
            development lifecycle and can effectively coordinate between code reviewers, 
            developers, QA engineers, and Git specialists.
            """,
            verbose=True,
            llm=llm_manager,
            allow_delegation=True,
            max_retry_limit=4,
            cache=False,
        )

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
            llm=llm_bug_detection_and_repair,
            cache=False, #Cache for tool usage
            allow_delegation=False,
            max_retry_limit=4,
        )

        python_developer = Agent(
            role="Senior Python Developer",
            goal=""" Fix bugs reported in the code review for the codebase. """,
            backstory="""
            You are a senior Python developer with more than 10 years of experience in Python development.
            """,
            tools=[
                DirectoryReadTool(directory=self.state.repo_dir, ignored=[".git", "__pycache__", "json_testcases", "python_testcases"]),
                FileReadTool(),
                FileWriterTool(),
            ],
            verbose=True,
            llm=llm_bug_detection_and_repair,
            #allow_code_execution=True,
            #code_execution_mode="safe",
            cache=False,
            max_retry_limit=4,
            allow_delegation=False, 
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
                DirectoryReadTool(directory=self.state.repo_dir, ignored=[".git", "__pycache__", "json_testcases", "python_testcases"]),
                FileReadTool(),
                CodeInterpreterTool(unsafe_mode=False)
            ],
            verbose=True,
            llm=llm_qa,
            max_retry_limit=4,
            allow_delegation=False, 
            cache=False,
        )

        git_specialist = Agent(
            role="Git Specialist",
            goal="""
            Generate commit messages and pull request descriptions based on code changes.
            """,
            backstory="""
            You are a Git specialist with extensive experience in managing Git repositories.
            """,
            verbose=True,
            cache=False,
            max_iter=3,
            allow_delegation=False, 
            llm=llm_git_summary,
        )

        bug_detection_and_fix_task = Task(
            description=f"""

            Lead the complete bug detection and fixing process for pull request #{self.state.pr_number},
            the PR details is {json.dumps(self.state.pr_details, indent=2)}\n

            The PR diff is:
            {self.state.pr_diff}

            **IMPORTANT PATH INFORMATION:**
            - Repository root directory: {self.state.repo_dir}
            - Current working branch: {self.state.pr_local_branch}
            - DirectoryReadTool is configured with repository base directory
            
            **FILE ACCESS INSTRUCTIONS:**
            - When using DirectoryReadTool, use relative paths from repository root (e.g., "src/", "tests/", or "." for root)
            - When using FileReadTool, you MUST use ABSOLUTE paths: {self.state.repo_dir}/relative_path and read the whole file
            - When using FileWriterTool, you MUST use ABSOLUTE paths: {self.state.repo_dir}/relative_path
            - If you see a file path like "a/file.py" in the diff, the actual file is at {self.state.repo_dir}/a/file.py

            **MANDATORY JOB:**
            -  **Code Review**: Delegate to Senior Code Reviewer to analyze the PR diff for bugs, focusing on functional issues only, and leave the files that don't appear in the diff untouched.
            -  **Quality Assurance**: If bugs found, have Senior QA Engineer verify fixes with writing and executing tests (do not save test files), If bugs not found, think about if tests are needed to confim the functionality works as intended.
            -  **Bug Fixing**: Based on the feedback from QA, decide whether to delegate to Senior Python Developer to fix bugs using correct absolute file paths, if no bugs found, no need to fix anything, otherwise this is a MUST.
            -  **Git Operations**: If bugs are found and any fixes were applied, delegate to Senior Git Specialist to generate a concise, conventional commit message summarizing the changes, and prepare a pull request description.

            **QA AND TESTING INSTRUCTIONS:**
            - The quality of tests is crucial. ALWAYS think about edge cases and potential failure points, like empty inputs, boundary values, etc.
            - Everytime you run a code snippet, you MUST analyze the output and report any errors or issues found.
            - You never change the codebase directly, **ALWAYS** ask your manager to delegate the writing code task to the Python Developer.
            - Never save test cases to the repository, ALWAYS run them in the safe code interpreter environment, therefore you cannot import modules from the repository, you must include all necessary code in the code snippet you run.
            - Never make up test results, ALWAYS run the tests and give feedback along with the code you have changed based on the actual results.
            - When all the tests pass, you need to distinguish the code is the original code or the fixed code.

            **Python Coding Guidelines:**
            - When writing code to the filesystem, **ALWAYS** use the code that has been tested by the QA Engineer.
            - You have the right to disagree with the Code Reviewer or QA Engineer, but you **must** in the end have the qa engineer approve the code changes.

            **OUTPUT FORMAT (STRICT)**:
            Return **STRICT JSON ONLY**, no extra text or code fences:
            {{
                "bugs_found": true/false,
                "review_results": {{}},
                "fixes_applied": [{{"file": "...", "summary": "..."}}] or [],
                "commit_message": "commit_message_if_available or null",
                "pull_request_summary": "fix: <title>,\n\n <body>" or null,
                "involved_agents": ["..."],
                "workflow_steps_completed": ["review","fix","qa","git"]
            }}

            **Exist Conditions:**
            1. Keep going until the user’s query is completely resolved, before ending your turn and yielding back to the user. Only terminate your turn when you are sure that the problem is solved.
            2. If QA verifies that no bugs are found, you can end the task early by reporting "bugs_found": false and skipping the bug fixing step.
            3. Whereas if bugs are found, you must ensure that the bugs are fixed and verified by QA before ending the task.
            """,
            expected_output="""
            STRICT JSON ONLY (no code fences, no prose). See fields above.
            """,
        )

        crew = Crew(
            agents=[code_reviewer, python_developer, qa_engineer, git_specialist],
            tasks=[bug_detection_and_fix_task],
            process=Process.hierarchical,
            manager_agent=manager,
            manager_llm=llm_manager,
            share_crew=True,
            verbose=True,
            cache=False,
            planning=True,
            planning_llm=llm_planning,
            output_log_file="bug_detection_crew_output.json",
        )
        start = time.perf_counter() 
        result = crew.kickoff()
        end = time.perf_counter()

        elapsed_ms = (end - start) * 1000
        print(f"Crew executed time: {elapsed_ms:.3f} ms")
        
        parsed: Dict[str, Any]
        parsed = _parse_json_strict(result.raw)

        model = CrewResultModel(**parsed)
        print("Crew Result Model:", model.model_dump_json(indent=2))

        if _repo_has_changes(self.state.repo_dir):
            msg = model.commit_message or "fix: apply bug fixes detected by automated review"
            commit_hash = _commit_and_push(self.state.repo_dir, self.state.pr_local_branch, msg)
            model.commit_hash = commit_hash
            
            if not model.pull_request_summary:
                title = "fix: apply minimal bug fixes" if model.bugs_found else "chore: no functional bugs found"
                body_lines = [
                    f"**Bugs found:** {model.bugs_found}",
                    f"**Commit:** `{model.commit_hash}`" if model.commit_hash else "",
                    "### Fixes:",
                    *[f"- {x.get('file','(unknown)')} — {x.get('summary','updated')}" for x in (model.fixes_applied or [])]
                ]
                prq = title + "\n\n" + "\n".join([l for l in body_lines if l])
                model.pull_request_summary = prq

        self.state.pull_request_summary = model.pull_request_summary
        self.state.bug_present = bool(model.bugs_found)
        self.state.fixed_files = [x.get("file") for x in (model.fixes_applied or []) if x.get("file")]
        print("Final State:", json.dumps(self.state.model_dump(), indent=2))
        print("Crew Raw Output:", result.raw)
        print("Crew Result Model:", json.dumps(model.model_dump(), indent=2))

        print(f"{'*' * 30 } Crew Token Usage {'*' * 30 }")
        print(result.token_usage)

        print(f"{'>' * 30 } Important Statistics {'>' * 30 }")
        print(f"Code Fix Branch: {self.state.pr_local_branch}")
        print(f"Crew Elapsed Time (ms): {elapsed_ms:.3f}")
        print(f"Total Tokens: {result.token_usage.total_tokens}")
        print(f"Input Tokens: {result.token_usage.prompt_tokens}")
        print(f"Cached Tokens: {result.token_usage.cached_prompt_tokens}")
        print(f"Output Tokens: {result.token_usage.completion_tokens}")
        print(f"Successful Requests: {result.token_usage.successful_requests}")
        print(f"{'<' * 30 } Important Statistics {'<' * 30 }")

        if model.bugs_found:
            return "Bugs found"
        return "No bugs found"

    @listen("Bugs found")
    def create_pull_request(self):
        print(f"Creating pull request with summary: {self.state.pull_request_summary}")
        pr = langchain_gh.CreatePullRequest()
        pr_response = pr._run(repo=self.state.repo, 
                              pr_query=self.state.pull_request_summary, 
                              src_branch=self.state.pr_local_branch, 
                              dest_branch=self.state.active_branch)
        print(f"Pull Request created result: {pr_response}")
        return pr_response
    
    @listen("No Bugs found")
    def end_flow_without_creating_pr(self):
        print("No bugs found, skipping pull request creation.")
        return None
    
    @listen(create_pull_request)
    def evaluation(self):
        print("Evaluating the results of the bug detection flow...")
        if self.state.bug_present and self.state.fixed_files:
            run_pytest_result = run_pytest(self.state.repo_dir, self.state.fixed_files, timeout_s=60)
            print("Pytest Result:", json.dumps(run_pytest_result, indent=2))
            if run_pytest_result.get("tests_pass"):
                print("All tests passed.")
            else:
                print("Some tests failed.")
        else:
            print("No bugs found or fixed files.")


def to_test_path(path: str) -> str:
    directory, filename = os.path.split(path)
    base_dir = os.path.dirname(directory)
    test_dir = os.path.join(base_dir, "python_testcases")
    return os.path.join(test_dir, f"test_{filename}")

def run_pytest(work_dir: str, files: List[str], timeout_s: int = 60) -> Dict[str, Any]:
    env = os.environ.copy()
    env["PYTHONDONTWRITEBYTECODE"] = "1"

    total_failed = 0
    total_passed = 0
    raw_outputs = []

    for f in files:
        test_path = to_test_path(f)
        cmd = ["pytest", test_path]

        try:
            proc = subprocess.run(
                cmd,
                cwd=work_dir,
                env=env,
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                timeout=timeout_s,
                text=True,
            )
            out = proc.stdout
            raw_outputs.append(f"=== {test_path} ===\n{out}")

            m_fail = re.search(r"(\d+)\s+failed", out)
            m_pass = re.search(r"(\d+)\s+passed", out)
            failed = int(m_fail.group(1)) if m_fail else 0
            passed = int(m_pass.group(1)) if m_pass else 0

            total_failed += failed
            total_passed += passed

        except subprocess.TimeoutExpired:
            raw_outputs.append(f"=== {test_path} ===\nTIMEOUT after {timeout_s}s")
            return {
                "tests_total": 0,
                "tests_failed": 0,
                "tests_pass": False,
                "timeout": True,
                "raw": "\n".join(raw_outputs),
            }

    total = total_failed + total_passed
    return {
        "tests_total": total,
        "tests_failed": total_failed,
        "tests_pass": (total_failed == 0 and total > 0),
        "raw": "\n".join(raw_outputs),
    }


def main(inputs=None, mcp_tools=None):
    flow = BugDetectionFlow()
    #print("mcp_tools:", mcp_tools)
    if mcp_tools:
        flow.get_prd_tool = mcp_tools["get_prd"]
    # Inputs will be assigned to the flow state by CrewAI
    flow.kickoff(inputs=inputs)

if __name__ == "__main__":
    with MCPServerAdapter(BugDetectionFlow.mcp_server_params) as mcp_tools:
        main(mcp_tools=mcp_tools)