import asyncio
import os
import sys
import typer
from rich.console import Console
from rich.panel import Panel
from rich.table import Table

from reforge.domain.models import ExcavationStatus
from reforge.adapters.repositories import JSONFileProjectRepository

async def run_status(project_id: str):
    console = Console()
    
    storage_dir = os.getenv("REFORGE_STORAGE_DIR", ".reforge_data")
    repository = JSONFileProjectRepository(storage_dir=storage_dir)
    state = await repository.get_by_id(project_id)
    
    if not state:
        console.print(f"[bold red]Error:[/bold red] Project with ID '{project_id}' not found in database.")
        sys.exit(1)

    console.print(f"[bold cyan]Project Status Card: {project_id}[/bold cyan]")
    console.print(f"[bold]Source/Repository URL:[/bold] {state.repository_url}")
    console.print(f"[bold]Current Pipeline Status:[/bold] [bold yellow]{state.status.value}[/bold yellow]\n")

    # Helper to check if a stage is completed
    # Stage status boundaries mapping
    status_order = [
        ExcavationStatus.PENDING,
        ExcavationStatus.DISCOVERING,
        ExcavationStatus.DISCOVERED,
        ExcavationStatus.EVALUATING,
        ExcavationStatus.EVALUATED,
        ExcavationStatus.UNDERSTANDING,
        ExcavationStatus.UNDERSTOOD,
        ExcavationStatus.RECONSTRUCTING,
        ExcavationStatus.RECONSTRUCTED,
        ExcavationStatus.RESTORATION_PLANNING,
        ExcavationStatus.AWAITING_APPROVAL,
        ExcavationStatus.RESTORING,
        ExcavationStatus.RESTORED,
        ExcavationStatus.VALIDATING,
        ExcavationStatus.VALIDATED,
        ExcavationStatus.EVOLVING,
        ExcavationStatus.COMPLETED
    ]
    
    def is_reached(target_status: ExcavationStatus) -> bool:
        if state.status == ExcavationStatus.FAILED:
            # Check properties to determine how far it went
            if target_status == ExcavationStatus.DISCOVERED:
                return state.profile is not None
            if target_status == ExcavationStatus.EVALUATED:
                return state.heritage_report is not None
            if target_status == ExcavationStatus.UNDERSTOOD:
                return state.software_overview is not None
            if target_status == ExcavationStatus.RECONSTRUCTED:
                return state.architecture_report is not None
            if target_status == ExcavationStatus.AWAITING_APPROVAL:
                return state.restoration_plan is not None
            if target_status == ExcavationStatus.RESTORED:
                return any(log.action_type == "RESTORE_SUCCESS" for log in state.audit_logs)
            if target_status == ExcavationStatus.VALIDATED:
                return any(log.action_type == "VALIDATION_SUCCESS" for log in state.audit_logs)
            return False
            
        try:
            return status_order.index(state.status) >= status_order.index(target_status)
        except ValueError:
            return False

    pipeline_table = Table(title="Pipeline Stage Execution Status", show_header=True)
    pipeline_table.add_column("Stage", style="bold white", width=30)
    pipeline_table.add_column("Status", no_wrap=True)

    stages = [
        ("1. Discovery", ExcavationStatus.DISCOVERED),
        ("2. Heritage Evaluation", ExcavationStatus.EVALUATED),
        ("3. Software Understanding", ExcavationStatus.UNDERSTOOD),
        ("4. Architecture Reconstruction", ExcavationStatus.RECONSTRUCTED),
        ("5. Restoration Planning", ExcavationStatus.AWAITING_APPROVAL),
        ("6. Restoration", ExcavationStatus.RESTORED),
        ("7. Code Validation", ExcavationStatus.VALIDATED),
        ("8. Evolution Planning", ExcavationStatus.COMPLETED)
    ]

    for name, status_boundary in stages:
        if is_reached(status_boundary):
            status_symbol = "[green]PASSED[/green]"
        elif state.status == ExcavationStatus.FAILED and not is_reached(status_boundary):
            # If failed at this exact boundary
            # Check if previous passed
            prev_index = stages.index((name, status_boundary)) - 1
            if prev_index >= 0 and is_reached(stages[prev_index][1]):
                status_symbol = "[red]FAILED[/red]"
            else:
                status_symbol = "[dim]STOPPED[/dim]"
        else:
            status_symbol = "[dim]PENDING[/dim]"
            
        pipeline_table.add_row(name, status_symbol)

    console.print(Panel(pipeline_table, border_style="cyan"))

    # Heritage report quick metrics
    if state.heritage_report:
        console.print(f"[bold yellow]Heritage Score:[/bold yellow] [bold green]{state.heritage_report.overall_score}/100[/bold green]")
        console.print(f"[bold yellow]Worth Preserving:[/bold yellow] [bold]{'YES' if state.heritage_report.worth_preserving else 'NO'}[/bold]\n")

    # Validation Scorecard display
    if state.validation_report:
        val = state.validation_report
        val_table = Table(title="Validation Scorecard", show_header=True, expand=True)
        val_table.add_column("Check", style="bold cyan")
        val_table.add_column("Status", style="bold")
        val_table.add_column("Metrics / Details")
        
        def style_status(status_val: str) -> str:
            if status_val == "PASSED":
                return "[green]PASSED[/green]"
            elif status_val == "FAILED":
                return "[red]FAILED[/red]"
            else:
                return f"[yellow]{status_val}[/yellow]"
        
        val_table.add_row("Syntax", style_status(val.syntax_status), f"{val.files_compiled} files compiled successfully")
        val_table.add_row("Imports", style_status(val.imports_status), "No broken imports" if val.imports_status == "PASSED" else "Unresolved imports detected")
        
        test_metrics = "No tests discovered"
        if val.pytest_discovered:
            test_metrics = f"{val.tests_passed} passed, {val.tests_failed} failed"
        val_table.add_row("Tests", style_status(val.tests_status), test_metrics)
        
        val_table.add_row("Build", style_status(val.build_status), "Manifest files present" if val.build_status == "PASSED" else "No manifests found")
        val_table.add_row("Lint", style_status(val.lint_status), "Code style clean" if val.lint_status == "PASSED" else "Lints or style issues identified")
        
        console.print(Panel(val_table, border_style="green" if val.overall_status == "PASSED" else "red"))
        console.print()

    # Recent logs list
    if state.audit_logs:
        log_table = Table(title="Recent Audit Logs (Timeline)", show_header=True)
        log_table.add_column("Timestamp", style="dim", width=20)
        log_table.add_column("Agent", style="bold yellow")
        log_table.add_column("Action Type", style="bold cyan")
        log_table.add_column("Outcome Description", style="white")

        for log in sorted(state.audit_logs, key=lambda l: l.timestamp, reverse=True)[:5]:
            timestamp_str = log.timestamp.strftime("%Y-%m-%d %H:%M:%S UTC")
            log_table.add_row(
                timestamp_str,
                log.agent_name,
                log.action_type,
                log.explanation
            )
        console.print(log_table)
    else:
        console.print("[dim]No audit log records stored yet.[/dim]")

def status(
    project_id: str = typer.Argument(..., help="The target project identifier.")
):
    """View detailed pipeline progression status and recent audit logs."""
    asyncio.run(run_status(project_id))
