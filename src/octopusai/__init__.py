import click

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

@click.command()
def main():
    print_banner()

if __name__ == '__main__':
    main()