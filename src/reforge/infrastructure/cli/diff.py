import typer
import asyncio
from rich.console import Console
from reforge.adapters.repositories import JSONFileProjectRepository

def diff(
    project_id: str = typer.Argument(..., help="Unique identifier of the project to compare"),
    run_a: str = typer.Option(None, help="First run timestamp or index to compare (default: second-to-last)"),
    run_b: str = typer.Option(None, help="Second run timestamp or index to compare (default: latest)"),
    storage_dir: str = typer.Option(".reforge_data", help="Directory where project state files are stored")
):
    """Compare two excavation runs to identify architectural drift, heritage trend, and restoration progress."""
    console = Console()
    repo = JSONFileProjectRepository(storage_dir=storage_dir)
    
    run_list = asyncio.run(repo.get_project_history(project_id))
    
    if not run_list:
        console.print(f"[bold red]Error:[/bold red] No excavation history found for project ID '{project_id}'.")
        raise typer.Exit(1)
        
    if len(run_list) < 2:
        console.print("[bold yellow]Warning:[/bold yellow] Only 1 execution run is stored. Cannot calculate differences. Please run `reforge excavate` again to create a second snapshot.")
        raise typer.Exit(0)
        
    def get_state_by_ref(ref: str, default_idx: int):
        if ref is None:
            return run_list[default_idx]
        if ref.isdigit():
            idx = int(ref)
            if 0 <= idx < len(run_list):
                return run_list[idx]
        for state in run_list:
            t_str = state.updated_at.strftime("%Y%m%d%H%M%S")
            if ref in t_str or ref in state.updated_at.strftime("%Y-%m-%d %H:%M:%S"):
                return state
        console.print(f"[bold red]Error:[/bold red] Could not find run matching reference '{ref}'. Use `reforge history {project_id}` to see valid runs.")
        raise typer.Exit(1)
        
    state_a = get_state_by_ref(run_a, len(run_list) - 2)
    state_b = get_state_by_ref(run_b, len(run_list) - 1)
    
    ta_str = state_a.updated_at.strftime("%Y-%m-%d %H:%M:%S")
    tb_str = state_b.updated_at.strftime("%Y-%m-%d %H:%M:%S")
    
    console.print(f"\n[bold green]Comparing Excavation Runs for project:[/bold green] [bold white]{project_id}[/bold white]")
    console.print(f"Run A (Before): [cyan]{ta_str}[/cyan] (status: {state_a.status.value})")
    console.print(f"Run B (After):  [cyan]{tb_str}[/cyan] (status: {state_b.status.value})\n")
    
    # 1. Compare Heritage Scores
    score_a = state_a.heritage_report.overall_score if state_a.heritage_report else 0
    score_b = state_b.heritage_report.overall_score if state_b.heritage_report else 0
    diff_score = score_b - score_a
    sign = "+" if diff_score >= 0 else ""
    console.print(f"[bold yellow]1. Heritage Score Trend:[/bold yellow] {score_a} -> {score_b} ({sign}{diff_score})")
    
    # 2. Compare Architecture Paradigm
    paradigm_a = getattr(state_a.software_overview, "architecture_paradigm", "Unknown") if state_a.software_overview else "Unknown"
    paradigm_b = getattr(state_b.software_overview, "architecture_paradigm", "Unknown") if state_b.software_overview else "Unknown"
    if paradigm_a != paradigm_b:
        console.print(f"[bold yellow]2. Architecture Paradigm Drift:[/bold yellow] [red]{paradigm_a}[/red] -> [green]{paradigm_b}[/green]")
    else:
        console.print(f"[bold yellow]2. Architecture Paradigm:[/bold yellow] [green]{paradigm_b}[/green] (no change)")
        
    # 3. Compare Components (Folders)
    comp_a = set(state_a.architecture_report.components) if state_a.architecture_report else set()
    comp_b = set(state_b.architecture_report.components) if state_b.architecture_report else set()
    added_comps = comp_b - comp_a
    removed_comps = comp_a - comp_b
    if added_comps or removed_comps:
        console.print("[bold yellow]3. Architecture Component Drift:[/bold yellow]")
        if added_comps:
            console.print(f"  [green]+ Added layers:[/green] {', '.join(added_comps)}")
        if removed_comps:
            console.print(f"  [red]- Removed layers:[/red] {', '.join(removed_comps)}")
    else:
        console.print(f"[bold yellow]3. Architecture Layers:[/bold yellow] {len(comp_b)} components (no change)")
        
    # 4. Compare Coupling Relationships
    rel_a = set(state_a.architecture_report.relationships) if state_a.architecture_report else set()
    rel_b = set(state_b.architecture_report.relationships) if state_b.architecture_report else set()
    added_rels = rel_b - rel_a
    removed_rels = rel_a - rel_b
    if added_rels or removed_rels:
        console.print("[bold yellow]4. Architectural Coupling Drift:[/bold yellow]")
        if added_rels:
            console.print(f"  [green]+ Added dependency boundaries:[/green]")
            for r in added_rels:
                console.print(f"    * {r}")
        if removed_rels:
            console.print(f"  [red]- Removed dependency boundaries:[/red]")
            for r in removed_rels:
                console.print(f"    * {r}")
    else:
        console.print(f"[bold yellow]4. Component Coupling Boundaries:[/bold yellow] {len(rel_b)} connections (no change)")

    # 5. Compare Restoration Issues
    issues_a = {i.description: i.severity for i in state_a.restoration_plan.issues} if state_a.restoration_plan else {}
    issues_b = {i.description: i.severity for i in state_b.restoration_plan.issues} if state_b.restoration_plan else {}
    resolved_issues = set(issues_a.keys()) - set(issues_b.keys())
    new_issues = set(issues_b.keys()) - set(issues_a.keys())
    if resolved_issues or new_issues:
        console.print("[bold yellow]5. Restoration Issues Changes:[/bold yellow]")
        if resolved_issues:
            console.print(f"  [green]✓ Resolved Issues:[/green]")
            for iss in resolved_issues:
                console.print(f"    * {iss} ({issues_a[iss]} severity)")
        if new_issues:
            console.print(f"  [red]✗ New Issues Detected:[/red]")
            for iss in new_issues:
                console.print(f"    * {iss} ({issues_b[iss]} severity)")
    else:
        console.print(f"[bold yellow]5. Restoration Issues:[/bold yellow] {len(issues_b)} unresolved (no change)")

    # 6. Compare Validation Test Results
    tests_a = state_a.validation_report.tests_passed if state_a.validation_report else 0
    tests_b = state_b.validation_report.tests_passed if state_b.validation_report else 0
    diff_tests = tests_b - tests_a
    if diff_tests != 0:
        sign = "+" if diff_tests > 0 else ""
        console.print(f"[bold yellow]6. Test Execution Trend:[/bold yellow] {tests_a} -> {tests_b} passed tests ({sign}{diff_tests})")
    else:
        console.print(f"[bold yellow]6. Test Execution Status:[/bold yellow] {tests_b} passing tests (no change)\n")
