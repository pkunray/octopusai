from crewai import Flow
from crewai.flow.flow import start, listen
from pydantic import BaseModel
from typing import List

class State(BaseModel):
    """State model"""
    github_url: str = ""
    languages: List[str] = []
    local_path: str = ""
    
class BugDetectionFlow(Flow[State]):
    """
    A Predifined Workflow utilizing CrewAI's Flow with Crew.
    Which can be integrated into CI/CD pipelines built with commonly adopted tools like Jenkins or GitHub Actions.
    """
    @start()
    def initialize(self):
        print(self.state)

    
    @listen(initialize)
    def test(self):
        print(self.state.github_url)
        

def main(inputs=None):
    flow = BugDetectionFlow()
    # Inputs will be assigned to the flow state by CrewAI
    flow.kickoff(inputs=inputs)

if __name__ == "__main__":
    main()