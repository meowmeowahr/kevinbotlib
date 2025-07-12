from contextlib import contextmanager

from rich.console import Console


@contextmanager
def rich_spinner(console: Console, message: str, success_message: str | None = None):
    with console.status(f"[bold green]{message}...", spinner="dots") as spinner:
        try:
            yield spinner
        finally:
            if success_message:
                console.print(f"[bold green]\u2714 {success_message}")
