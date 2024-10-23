import click

from kevinbotlib.__about__ import __version__
from kevinbotlib.cli.serve import serve
from kevinbotlib.cli.pub import pub
from kevinbotlib.cli.listen import listen


@click.group(
    context_settings={'help_option_names': ['-h', '--help'], 'max_content_width': 120}
)
@click.version_option(version=__version__, prog_name='KevinbotLib')
@click.pass_context
def cli(ctx: click.Context, interactive: bool | None):
    """
    \b
    ██╗  ██╗███████╗██╗   ██╗██╗███╗   ██╗██████╗  ██████╗ ████████╗
    ██║ ██╔╝██╔════╝██║   ██║██║████╗  ██║██╔══██╗██╔═══██╗╚══██╔══╝
    █████╔╝ █████╗  ██║   ██║██║██╔██╗ ██║██████╔╝██║   ██║   ██║   
    ██╔═██╗ ██╔══╝  ╚██╗ ██╔╝██║██║╚██╗██║██╔══██╗██║   ██║   ██║   
    ██║  ██╗███████╗ ╚████╔╝ ██║██║ ╚████║██████╔╝╚██████╔╝   ██║   
    ╚═╝  ╚═╝╚══════╝  ╚═══╝  ╚═╝╚═╝  ╚═══╝╚═════╝  ╚═════╝    ╚═╝                                                
    """


# Add commands to the main CLI group
cli.add_command(serve)
cli.add_command(listen)
cli.add_command(pub)

def main():
    cli(prog_name='kevinbot')

if __name__ == "__main__":
    main()