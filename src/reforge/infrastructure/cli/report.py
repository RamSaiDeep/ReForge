import asyncio
import json
import os
import sys
import typer
from rich.console import Console
from rich.markdown import Markdown

from reforge.adapters.repositories import JSONFileProjectRepository

async def run_report(project_id: str, as_json: bool, as_markdown: bool, open_report: bool):
    console = Console()
    
    storage_dir = os.getenv("REFORGE_STORAGE_DIR", ".reforge_data")
    repository = JSONFileProjectRepository(storage_dir=storage_dir)
    state = await repository.get_by_id(project_id)
    
    if not state:
        console.print(f"[bold red]Error:[/bold red] Project with ID '{project_id}' not found in database.")
        sys.exit(1)

    report_dir = os.path.join("reports", project_id)
    summary_path = os.path.join(report_dir, "summary.md")

    if open_report:
        if not os.path.exists(summary_path):
            console.print(f"[bold red]Error:[/bold red] Markdown report summary file does not exist at: {summary_path}")
            sys.exit(1)
        console.print(f"[bold cyan]Opening summary report in default viewer:[/bold cyan] {summary_path}")
        try:
            os.startfile(summary_path)
        except Exception as err:
            console.print(f"[bold red]Failed to open file:[/bold red] {err}")
        return

    if as_json:
        # Print dump of entire project state Pydantic structure
        if hasattr(state, "model_dump"):
            console.print_json(data=state.model_dump(mode="json"))
        return

    if as_markdown or not os.path.exists(summary_path):
        # Print raw markdown summary
        if os.path.exists(summary_path):
            with open(summary_path, "r", encoding="utf-8") as f:
                console.print(f.read(), markup=False)
        else:
            # Fallback print if summary.md has not been generated yet
            console.print(f"[bold yellow]Project {project_id} Status: {state.status.value}[/bold yellow]")
            console.print("[dim]No generated summary.md found. Run excavate to complete pipeline and write reports.[/dim]")
        return

    # Default formatted Rich rendering of summary.md
    with open(summary_path, "r", encoding="utf-8") as f:
        md = Markdown(f.read())
        console.print(md)

def report(
    project_id: str = typer.Argument(..., help="The target project identifier."),
    as_json: bool = typer.Option(False, "--json", "-j", help="Print complete project state JSON to stdout."),
    as_markdown: bool = typer.Option(False, "--markdown", "-m", help="Print raw Markdown content to stdout."),
    open_report: bool = typer.Option(False, "--open", "-o", help="Open the summary report in your default system handler.")
):
    """Retrieve and display the archaeological reports for an excavated project."""
    asyncio.run(run_report(project_id, as_json, as_markdown, open_report))
