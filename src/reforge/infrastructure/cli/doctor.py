import asyncio
import os
import shutil
import subprocess
import sys
import httpx
from rich.console import Console
from rich.table import Table

async def run_doctor():
    console = Console()
    console.print("[bold cyan]ReForge CLI Doctor - Environment Diagnostics[/bold cyan]\n")

    table = Table(show_header=True, header_style="bold green")
    table.add_column("Diagnostic Check", style="white", width=35)
    table.add_column("Result Status", no_wrap=True)
    table.add_column("Details", style="dim")

    # 1. Check Python Version
    py_version = f"{sys.version_info.major}.{sys.version_info.minor}.{sys.version_info.micro}"
    if sys.version_info >= (3, 10):
        table.add_row("Python version >= 3.10", "[green]PASSED[/green]", f"Version {py_version} detected")
    else:
        table.add_row("Python version >= 3.10", "[red]FAILED[/red]", f"Version {py_version} is unsupported (needs >= 3.10)")

    # 2. Check Git Executable
    git_path = shutil.which("git")
    if git_path:
        try:
            git_ver = subprocess.check_output(["git", "--version"]).decode().strip()
            table.add_row("Git Executable available", "[green]PASSED[/green]", git_ver)
        except Exception:
            table.add_row("Git Executable available", "[yellow]! Warning[/yellow]", "Found git binary but failed to execute version query.")
    else:
        table.add_row("Git Executable available", "[red]FAILED[/red]", "Git binary not found on PATH. Excavation explorer will fail.")

    # 3. Check GitHub API connection & Token
    has_token = "GITHUB_TOKEN" in os.environ
    token_detail = "Found GITHUB_TOKEN" if has_token else "GITHUB_TOKEN not defined (unauthenticated rate limits apply)"
    
    try:
        async with httpx.AsyncClient(timeout=3.0) as client:
            headers = {"User-Agent": "ReForge-Doctor"}
            if has_token:
                headers["Authorization"] = f"token {os.environ['GITHUB_TOKEN']}"
            res = await client.get("https://api.github.com/", headers=headers)
            if res.status_code == 200:
                table.add_row("GitHub API connection", "[green]PASSED[/green]", f"Connected. {token_detail}")
            else:
                table.add_row("GitHub API connection", "[yellow]! Warning[/yellow]", f"GitHub returned HTTP status {res.status_code}. {token_detail}")
    except Exception as err:
        table.add_row("GitHub API connection", "[red]FAILED[/red]", f"Connection failed: {type(err).__name__}")

    # 4. Check Storage Directory Writable
    storage_dir = os.getenv("REFORGE_STORAGE_DIR", ".reforge_data")
    try:
        os.makedirs(storage_dir, exist_ok=True)
        # Verify writing a test file
        test_file = os.path.join(storage_dir, ".doctor_write_test")
        with open(test_file, "w") as f:
            f.write("OK")
        os.remove(test_file)
        table.add_row("Storage database writable", "[green]PASSED[/green]", f"Directory: {storage_dir}")
    except Exception as err:
        table.add_row("Storage database writable", "[red]FAILED[/red]", f"Failed: {err}")

    # 5. Check Reports Directory Writable
    reports_dir = "reports"
    try:
        os.makedirs(reports_dir, exist_ok=True)
        test_file = os.path.join(reports_dir, ".doctor_write_test")
        with open(test_file, "w") as f:
            f.write("OK")
        os.remove(test_file)
        table.add_row("Reports directory writable", "[green]PASSED[/green]", f"Directory: {reports_dir}")
    except Exception as err:
        table.add_row("Reports directory writable", "[red]FAILED[/red]", f"Failed: {err}")

    console.print(table)
    console.print("\n[dim]Doctor checks completed. ReForge is ready for software archaeology excavation.[/dim]")

def doctor():
    """Verify system prerequisites (Git, python version, and writable database)."""
    asyncio.run(run_doctor())
