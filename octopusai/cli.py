import click
import octopusai.commands.bug_detection_command as bug_detection_command

def print_banner():
    """
    Banner: Octopus AI
    Slogan: "The intelligent tentacles of AI"
    """
    banner = """
     ██████   ██████ ████████  ██████  ██████  ██    ██ ███████      █████  ██ 
    ██    ██ ██         ██    ██    ██ ██   ██ ██    ██ ██          ██   ██ ██ 
    ██    ██ ██         ██    ██    ██ ██████  ██    ██ ███████     ███████ ██ 
    ██    ██ ██         ██    ██    ██ ██      ██    ██      ██     ██   ██ ██ 
     ██████   ██████    ██     ██████  ██       ██████  ███████     ██   ██ ██ 
                                                                              
    The intelligent tentacles of AI
    """

    click.echo(click.style(banner, fg='bright_yellow', bold=True))

@click.group()
def main():
    """OctopusAI CLI"""
    pass

@click.group()
def run():
    """Run agents."""
    print_banner()

main.add_command(run)
run.add_command(bug_detection_command.bug_detection)

if __name__ == '__main__':
    main()