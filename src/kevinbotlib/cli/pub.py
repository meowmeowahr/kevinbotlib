import click

@click.command()
@click.argument('topic')
@click.argument('message')
def pub(_, __):
    """Publish a message to a specific MQTT topic"""
    click.echo("In the future...")