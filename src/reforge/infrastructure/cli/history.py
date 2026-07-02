import typer
import asyncio
from rich.console import Console
from rich.table import Table
from reforge.adapters.repositories import JSONFileProjectRepository

def history(
    project_id: str = typer.Argument(..., help="Unique identifier of the project to retrieve history for"),
    storage_dir: str = typer.Option(".reforge_data", help="Directory where project state files are stored")
):
    """Retrieve the chronological execution runs and historical snapshot database of excavations."""
    console = Console()
    repo = JSONFileProjectRepository(storage_dir=storage_dir)
    
    run_list = asyncio.run(repo.get_project_history(project_id))
    
    if not run_list:
        console.print(f"[bold red]Error:[/bold red] No excavation history found for project ID '{project_id}'.")
        raise typer.Exit(1)
        
    console.print(f"\n[bold green]Excavation History for project:[/bold green] [bold white]{project_id}[/bold white]")
    console.print(f"Total runs tracked: [cyan]{len(run_list)}[/cyan]\n")
    
    table = Table(show_header=True, header_style="bold magenta")
    table.add_column("Run ID (Timestamp)", style="dim", width=22)
    table.add_column("Status", style="bold")
    table.add_column("Heritage Score", justify="center")
    table.add_column("Worth Preserving", justify="center")
    table.add_column("Validation", justify="center")
    table.add_column("Effort (Hrs)", justify="right")
    
    for state in run_list:
        timestamp_str = state.updated_at.strftime("%Y-%m-%d %H:%M:%S")
        status_str = f"[cyan]{state.status.value}[/cyan]"
        if state.status.value == "completed":
            status_str = "[green]completed[/green]"
        elif state.status.value == "failed":
            status_str = "[red]failed[/red]"
            
        heritage_score = "N/A"
        worth_preserving = "N/A"
        if state.heritage_report:
            heritage_score = f"{state.heritage_report.overall_score}/100"
            worth_preserving = "[green]YES[/green]" if state.heritage_report.worth_preserving else "[red]NO[/red]"
            
        validation_status = "N/A"
        if state.validation_report:
            val_stat = state.validation_report.overall_status
            if val_stat == "PASSED":
                validation_status = "[green]PASSED[/green]"
            elif val_stat == "FAILED":
                validation_status = "[red]FAILED[/red]"
            else:
                validation_status = f"[yellow]{val_stat}[/yellow]"
                
        effort = "N/A"
        if state.restoration_plan:
            effort = f"{state.restoration_plan.estimated_effort_hours:.1f}"
            
        table.add_row(
            timestamp_str,
            status_str,
            heritage_score,
            worth_preserving,
            validation_status,
            effort
        )
        
    console.print(table)
