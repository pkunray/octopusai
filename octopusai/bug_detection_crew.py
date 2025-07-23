from crewai import Agent, Crew, Process, Task
from crewai.project import CrewBase, agent, crew, task
from crewai_tools import DirectoryReadTool, FileReadTool
from tools.git_clone import git_clone_tool
from datetime import datetime

@CrewBase
class BugDetectionCrew:
    """Bug Detection Crew"""
    
    agents_config = "config/agents.yaml"
    tasks_config = "config/tasks.yaml"
    
    @agent
    def bug_detective(self) -> Agent:
        return Agent(
            config=self.agents_config['bug_detective'],
            tools=[
                DirectoryReadTool(),
                FileReadTool(),
                git_clone_tool,
            ],
            verbose=True
        )
    
    @agent  
    def report_compiler(self) -> Agent:
        return Agent(
            config=self.agents_config['report_compiler'],
            verbose=True
        )
    
    @task
    def analyze_code_for_bugs(self) -> Task:
        return Task(
            config=self.tasks_config['analyze_code_for_bugs'],
            agent=self.bug_detective()
        )
    
    @task
    def compile_bug_report(self) -> Task:
        return Task(
            config=self.tasks_config['compile_bug_report'],
            agent=self.report_compiler(),
            output_file=f"""bug_report_{datetime.now().strftime("%Y%m%d_%H%M%S")}.md"""
        )
    
    @crew
    def crew(self) -> Crew:
        """Creates the Bug Detection crew"""
        return Crew(
            agents=self.agents, 
            tasks=self.tasks,
            process=Process.sequential,
            verbose=True
        ) 
    

def main():
    repository_url = input("Enter GitHub repository URL: ").strip()
    
    if not repository_url:
        raise ValueError("Repository URL is required")
    
    print(f"Starting bug analysis for: {repository_url}")
    print("=" * 60)
    
    bug_crew = BugDetectionCrew()
    inputs = {"repository_url": repository_url}
    
    try:
        bug_crew.crew().kickoff(inputs=inputs)
        print("Bug analysis completed!")
        
    except Exception as e:
        print(f"Error during analysis: {e}")


if __name__ == "__main__":
    main() 