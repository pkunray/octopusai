import click
import octopusai.crews.bug_detection_flow as bug_detection_flow

@click.command("bug")
@click.argument("github_url")
@click.option("--requirement", "-r", help="Requirement ID for the Pull Request (PR)")
@click.pass_context
def bug_detection(ctx: click.Context, github_url: str, requirement: str):
    """Run the bug detection workflow."""
    click.echo("Running Bug Detection Workflow...")
    inputs={
        "github_url": github_url,
        "requirement": requirement,
    }
    click.echo(f"Inputs: {inputs}")
    bug_detection_flow.main(inputs=inputs)