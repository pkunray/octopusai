import click
import octopusai.crews.bug_detection_flow as bug_detection_flow
from crewai_tools import MCPServerAdapter
import octopusai.crews.bug_detection_flow as bug_detection_flow

@click.command("bug")
@click.argument("repo")
@click.argument("pr_number")
@click.argument("active_branch")
@click.option("--requirement_id", "-r", help="Requirement ID for the Pull Request (PR)")
@click.pass_context
def bug_detection(ctx: click.Context, repo: str, pr_number: str, active_branch: str, requirement_id: str):
    """Run the bug detection workflow."""
    click.echo("Running Bug Detection Workflow...")
    inputs={
        "repo": repo,
        "pr_number": pr_number,
        "active_branch": active_branch,
        "requirement_id": requirement_id,
    }
    click.echo(f"Inputs: {inputs}")
    with MCPServerAdapter(bug_detection_flow.BugDetectionFlow.mcp_server_params) as mcp_tools:
        bug_detection_flow.main(inputs=inputs, mcp_tools=mcp_tools)