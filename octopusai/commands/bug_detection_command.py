import click
import octopusai.crews.bug_detection_flow as sequential
import octopusai.crews.bug_detection_hierarchical as hierarchical
from crewai_tools import MCPServerAdapter


@click.command("bug")
@click.argument("repo")
@click.argument("pr_number")
@click.argument("active_branch")
@click.option("--requirement_id", "-r", help="Requirement ID for the Pull Request (PR)")
@click.option("--mode", "-m", type=click.Choice(["sequential", "hierarchical"]), default="sequential", help="Choose the bug detection mode")
@click.pass_context
def bug_detection(ctx: click.Context, repo: str, pr_number: str, active_branch: str, requirement_id: str, mode: str):
    """Run the bug detection workflow."""
    click.echo("Running Bug Detection Workflow...")
    inputs={
        "repo": repo,
        "pr_number": pr_number,
        "active_branch": active_branch,
        "requirement_id": requirement_id,
    }
    click.echo(f"Inputs: {inputs}")

    if mode == "sequential":
        with MCPServerAdapter(sequential.BugDetectionFlow.mcp_server_params) as mcp_tools:
            sequential.main(inputs=inputs, mcp_tools=mcp_tools)
    else:
        with MCPServerAdapter(hierarchical.BugDetectionFlow.mcp_server_params) as mcp_tools:
            hierarchical.main(inputs=inputs, mcp_tools=mcp_tools)
