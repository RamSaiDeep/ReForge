import asyncio
import os
import typer
from rich.console import Console
from rich.table import Table

from reforge.adapters.repositories import JSONFileProjectRepository

async def list_projects_async():
    console = Console()
    
    storage_dir = os.getenv("REFORGE_STORAGE_DIR", ".reforge_data")
    if not os.path.exists(storage_dir):
        console.print("[yellow]No projects found in storage database.[/yellow]")
        return
        
    repository = JSONFileProjectRepository(storage_dir=storage_dir)
    projects = await repository.list_projects()
    
    if not projects:
        console.print("[yellow]No projects found in storage database.[/yellow]")
        return

    table = Table(title="ReForge Archaeology Projects", show_header=True, header_style="bold cyan")
    table.add_column("Project ID", style="green", no_wrap=True)
    table.add_column("Source/Repo URL", style="white")
    table.add_column("Status", style="bold yellow")
    table.add_column("Heritage Score", style="bold yellow")
    table.add_column("Last Updated", style="dim")

    for state in projects:
        score_str = "N/A"
        if state.heritage_report:
            score_str = f"{state.heritage_report.overall_score}/100"
            
        updated_str = state.updated_at.strftime("%Y-%m-%d %H:%M UTC") if state.updated_at else "N/A"
        
        table.add_row(
            state.project_id,
            state.repository_url,
            state.status.value,
            score_str,
            updated_str
        )

    console.print(table)

def list_projects():
    """List all excavated projects stored in the local database."""
    asyncio.run(list_projects_async())
