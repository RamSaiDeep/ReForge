import typer
import time
import asyncio
from rich.console import Console
from rich.table import Table
from rich.panel import Panel
from reforge.infrastructure.cli.excavate import run_excavation_workflow

def benchmark(
    storage_dir: str = typer.Option(".reforge_data", help="Directory where project state files are stored"),
    auto_approve: bool = typer.Option(True, help="Auto-approve all excavation steps during benchmark")
):
    """Run regression tests across a golden suite of repositories to evaluate pipeline accuracy and execution time."""
    console = Console()
    console.print(Panel("[bold cyan]ReForge Archaeological Benchmark Harness[/bold cyan]\nRunning validation suite across golden standard repositories...", expand=False))

    # Define golden benchmark targets
    golden_suite = [
        {
            "name": "reforge-local",
            "target": ".", # local reforge repo
            "expected_paradigm": "Clean Architecture",
            "expected_build": "poetry/pip",
            "expected_min_files": 15
        },
        {
            "name": "click-local",
            "target": "https://github.com/pallets/click",
            "expected_paradigm": "Command-Line Interface Utility",
            "expected_build": "poetry/pip",
            "expected_min_files": 30
        }
    ]

    table = Table(show_header=True, header_style="bold magenta")
    table.add_column("Repository", style="bold white")
    table.add_column("Runtime (s)", justify="right")
    table.add_column("Files Found", justify="right")
    table.add_column("Expected Paradigm", style="dim")
    table.add_column("Actual Paradigm")
    table.add_column("Match Status", justify="center")

    total_start = time.time()
    matches = 0
    total_repos = len(golden_suite)
    results = []

    for item in golden_suite:
        name = item["name"]
        target = item["target"]
        expected_paradigm = item["expected_paradigm"]
        
        console.print(f"\n[bold yellow]>>> Running Benchmark Target: {name} ({target})[/bold yellow]\n")
        
        start_time = time.time()
        try:
            # Set environment variable to customize storage dir
            import os
            os.environ["REFORGE_STORAGE_DIR"] = storage_dir
            
            # Execute excavation pipeline using excavate module's main entry point
            state = asyncio.run(run_excavation_workflow(
                target=target,
                project_id=name,
                auto_approve=auto_approve
            ))
            duration = time.time() - start_time
            
            # Extract actual values
            actual_paradigm = getattr(state.software_overview, "architecture_paradigm", "Unknown") if state.software_overview else "Unknown"
            files_count = len(state.architecture_report.modules) if state.architecture_report else 0
            
            # Check match (allow substring match)
            is_match = (expected_paradigm.lower() in actual_paradigm.lower() or 
                        actual_paradigm.lower() in expected_paradigm.lower())
            
            match_status = "[green]PASS[/green]" if is_match else "[red]FAIL[/red]"
            if is_match:
                matches += 1
                
            table.add_row(
                name,
                f"{duration:.2f}s",
                str(files_count),
                expected_paradigm,
                actual_paradigm,
                match_status
            )
            results.append({
                "name": name,
                "runtime": f"{duration:.2f}s",
                "expected": expected_paradigm,
                "actual": actual_paradigm,
                "status": "PASS" if is_match else "FAIL"
            })
        except Exception as e:
            duration = time.time() - start_time
            table.add_row(
                name,
                f"{duration:.2f}s",
                "0",
                expected_paradigm,
                f"[red]Error: {str(e)}[/red]",
                "[red]FAIL[/red]"
            )
            results.append({
                "name": name,
                "runtime": f"{duration:.2f}s",
                "expected": expected_paradigm,
                "actual": f"Error: {str(e)}",
                "status": "FAIL"
            })

    total_duration = time.time() - total_start
    accuracy = (matches / total_repos) * 100

    console.print("\n" + "=" * 80)
    console.print("[bold green]Benchmark Completed Summary Scorecard![/bold green]")
    console.print("=" * 80 + "\n")
    console.print(table)
    
    console.print(f"\nTotal Suite Execution Time: [cyan]{total_duration:.2f}s[/cyan]")
    accuracy_style = "green" if accuracy >= 100 else "yellow" if accuracy >= 50 else "red"
    console.print(f"Architecture Paradigm Accuracy: [{accuracy_style}]{accuracy:.1f}%[/{accuracy_style}]\n")

    # Write report file
    import os
    os.makedirs("reports", exist_ok=True)
    report_path = "reports/benchmark_report.md"
    with open(report_path, "w", encoding="utf-8") as f:
        f.write(f"# ReForge Automated Benchmark Suite Report\n\n")
        f.write(f"- **Date**: {time.strftime('%Y-%m-%d %H:%M:%S UTC', time.gmtime())}\n")
        f.write(f"- **Accuracy Rate**: {accuracy:.1f}%\n")
        f.write(f"- **Total Suite Runtime**: {total_duration:.2f}s\n\n")
        f.write(f"| Repository | Runtime | Paradigm Target | Paradigm Actual | Match |\n")
        f.write(f"|---|---|---|---|---|\n")
        
        for res in results:
            f.write(f"| {res['name']} | {res['runtime']} | {res['expected']} | {res['actual']} | {res['status']} |\n")
            
    console.print(f"Benchmark results written to: [bold white]{report_path}[/bold white]\n")
