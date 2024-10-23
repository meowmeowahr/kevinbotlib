import click


@click.group(
    context_settings={'help_option_names': ['-h', '--help'], 'max_content_width': 120}
)
def cli():
    """Kevinbotlib command-line interface"""
    pass

@click.command()
def serve():
    """Start the Kevinbot MQTT inferface"""
    click.echo("In the future...")

@click.command()
def listen():
    """Listen to MQTT topic(s)"""
    click.echo("In the future...")

@click.command()
@click.argument('topic')
@click.argument('message')
def pub(_, __):
    """Publish a message to a specific MQTT topic"""
    click.echo("In the future...")

# Add commands to the main CLI group
cli.add_command(serve)
cli.add_command(listen)
cli.add_command(pub)

if __name__ == "__main__":
    cli()
