import typer
from rich.console import Console

app = typer.Typer(
    name="reforge",
    help="ReForge Software Archaeology Platform: Discover, evaluate, understand, and restore legacy codebases."
)

ASCII_ART = r"""
 ___  ___  ___  ___  ___  ___  ___
| _ \| __|| __|/   \| _ \|  _|| __|
|   /| _| | _| | | ||   /| |_ | _|
|_|_\|___||_|  \___/|_|_\|___||___|
"""

# Import subcommands
from reforge.infrastructure.cli.excavate import excavate
from reforge.infrastructure.cli.list import list_projects
from reforge.infrastructure.cli.report import report
from reforge.infrastructure.cli.status import status
from reforge.infrastructure.cli.doctor import doctor
from reforge.infrastructure.cli.history import history
from reforge.infrastructure.cli.diff import diff
from reforge.infrastructure.cli.benchmark import benchmark

# Register implemented subcommands
app.command(name="excavate", help="Clones, analyzes, restores, and proposes evolutions for a target project.")(excavate)
app.command(name="list", help="Lists all currently stored archaeology projects and their status.")(list_projects)
app.command(name="report", help="Displays summaries or detailed reports of an excavated project.")(report)
app.command(name="status", help="Traces pipeline state status progress and audit log updates for a project.")(status)
app.command(name="doctor", help="Inspects system environment pre-requisites (Git, Python version, connection).")(doctor)
app.command(name="history", help="Retrieve the chronological execution runs and historical snapshot database.")(history)
app.command(name="diff", help="Compare two excavation runs to identify architectural drift, heritage trend, and restoration.")(diff)
app.command(name="benchmark", help="Run regression tests across a golden suite of repositories.")(benchmark)

# Future-proof placeholder command stubs
@app.command(name="validate", help="[Future] Run test validations on a restored project.", hidden=True)
def validate_stub():
    pass

@app.command(name="restore", help="[Future] Manually run restoration steps on a project.", hidden=True)
def restore_stub():
    pass

@app.command(name="evolve", help="[Future] Apply recommended evolution proposals to a codebase.", hidden=True)
def evolve_stub():
    pass

@app.command(name="config", help="[Future] View or modify ReForge global configuration profiles.", hidden=True)
def config_stub():
    pass

@app.command(name="version", help="Displays the current version of ReForge.")
def version():
    """Display product version information."""
    console = Console()
    console.print("ReForge Software Archaeology Platform [bold green]v0.4.0[/bold green]")

@app.callback(invoke_without_command=True)
def main_callback(ctx: typer.Context):
    """Callback executed before any subcommand or when no command is provided."""
    if ctx.invoked_subcommand is None:
        console = Console()
        console.print(f"[bold cyan]{ASCII_ART}[/bold cyan]")
        console.print("[bold white]ReForge Software Archaeology Platform [green]v0.4.0[/green][/bold white]\n")
        console.print("[bold yellow]Commands:[/bold yellow]")
        console.print("  [bold green]excavate[/bold green]   Clones, analyzes, restores, and evolves codebases.")
        console.print("  [bold green]list[/bold green]       Lists all excavated archaeology projects.")
        console.print("  [bold green]status[/bold green]     Traces pipeline execution status and audit logs.")
        console.print("  [bold green]report[/bold green]     Retrieves JSON/Markdown reports for a project.")
        console.print("  [bold green]doctor[/bold green]     Runs pre-requisite diagnostic checks on environment.")
        console.print("  [bold green]history[/bold green]    Retrieve execution runs and historical snapshots.")
        console.print("  [bold green]diff[/bold green]       Compare two runs to identify architectural drift.")
        console.print("  [bold green]benchmark[/bold green]  Run regression tests across golden repositories.\n")
        console.print("[dim]Use 'reforge --help' to view detailed options and descriptions.[/dim]\n")

def main():
    app()

if __name__ == "__main__":
    main()
