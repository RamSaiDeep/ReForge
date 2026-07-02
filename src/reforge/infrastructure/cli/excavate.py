import asyncio
import json
import os
import shutil
import tempfile
import typer
from rich.console import Console
from rich.panel import Panel
from rich.table import Table
from typing import Optional, Dict, Any

from reforge.domain.models import ExcavationState, ExcavationStatus
from reforge.adapters.repositories import InMemoryProjectRepository
from reforge.adapters.github_provider import GitHubProvider
from reforge.adapters.git_cloner import LocalGitCloner
from reforge.adapters.workspace_inspector import LocalWorkspaceInspector
from reforge.adapters.code_analyzer import LocalCodeAnalyzer
from reforge.adapters.restoration_executor import LocalRestorationExecutor
from reforge.adapters.code_validator import LocalCodeValidator

from reforge.usecases.scout import ScoutAgent
from reforge.usecases.heritage import HeritageEvaluator
from reforge.usecases.explorer import ExplorerAgent
from reforge.usecases.architect import ArchitectAgent
from reforge.usecases.restoration_planner import RestorationPlannerAgent
from reforge.usecases.restorer import RestorerAgent
from reforge.usecases.validation_agent import ValidationAgent
from reforge.usecases.evolution_planner import EvolutionPlannerAgent
from reforge.usecases.supervisor import SupervisorWorkflow

def serialize_pydantic(model: Any) -> Dict[str, Any]:
    if hasattr(model, "model_dump"):
        return model.model_dump()
    return {}

async def run_excavation_workflow(target: str, project_id: Optional[str], auto_approve: bool):
    console = Console()

    # Determine project ID
    if not project_id:
        project_id = target.rstrip("/").split("/")[-1].replace(".git", "")
        if not project_id or project_id in (".", ".."):
            project_id = "excavated-project"

    console.print(f"[bold cyan]Starting Excavation for project:[/bold cyan] [green]{project_id}[/green]")
    console.print(f"[bold cyan]Source location:[/bold cyan]           {target}\n")

    # Detect repo vs local
    is_remote = target.startswith(("http://", "https://", "git@", "github.com"))
    temp_dir = None
    if is_remote:
        temp_dir = tempfile.mkdtemp(prefix="reforge-")
        local_path = temp_dir
    else:
        local_path = os.path.abspath(target)

    # Initialize production singletons
    from reforge.adapters.repositories import JSONFileProjectRepository
    storage_dir = os.getenv("REFORGE_STORAGE_DIR", ".reforge_data")
    repository = JSONFileProjectRepository(storage_dir=storage_dir)
    git_provider = GitHubProvider()
    git_cloner = LocalGitCloner()
    workspace_inspector = LocalWorkspaceInspector()
    code_analyzer = LocalCodeAnalyzer()
    restoration_executor = LocalRestorationExecutor()
    code_validator = LocalCodeValidator()

    # Initialize agents
    scout_agent = ScoutAgent(git_provider=git_provider)
    heritage_evaluator = HeritageEvaluator()
    explorer_agent = ExplorerAgent(cloner=git_cloner, inspector=workspace_inspector)
    architect_agent = ArchitectAgent(analyzer=code_analyzer)
    restoration_planner = RestorationPlannerAgent()
    restorer_agent = RestorerAgent(executor=restoration_executor)
    validation_agent = ValidationAgent(validator=code_validator)
    evolution_planner = EvolutionPlannerAgent()

    # Initialize supervisor
    supervisor = SupervisorWorkflow(
        repository=repository,
        scout_agent=scout_agent,
        heritage_evaluator=heritage_evaluator,
        explorer_agent=explorer_agent,
        architect_agent=architect_agent,
        restoration_planner=restoration_planner,
        restorer_agent=restorer_agent,
        validation_agent=validation_agent,
        evolution_planner=evolution_planner
    )

    try:
        repo_url = target if is_remote else f"file:///{local_path.replace(os.sep, '/')}"
        state = await supervisor.create_project(project_id, repo_url)
        if not is_remote:
            state.local_path = local_path

        # Stages 1 to 5
        console.print("[yellow][1/8][/yellow] Discovery... ", end="")
        state.status = ExcavationStatus.DISCOVERING
        await scout_agent.run(state)
        console.print("[green]DONE[/green]")

        console.print("[yellow][2/8][/yellow] Heritage Evaluation... ", end="")
        await heritage_evaluator.run(state)
        console.print("[green]DONE[/green]")

        console.print("[yellow][3/8][/yellow] Software Understanding... ", end="")
        if is_remote:
            state.local_path = os.path.join(local_path, project_id)
            os.makedirs(state.local_path, exist_ok=True)
        await explorer_agent.run(state)
        console.print("[green]DONE[/green]")

        console.print("[yellow][4/8][/yellow] Architecture Reconstruction... ", end="")
        await architect_agent.run(state)
        console.print("[green]DONE[/green]")

        console.print("[yellow][5/8][/yellow] Restoration Planning... ", end="")
        await restoration_planner.run(state)
        console.print("[green]DONE[/green]\n")

        await repository.save(state)

        # Heritage Scorecard display
        score = state.heritage_report.overall_score if state.heritage_report else 0
        worth_preserving = state.heritage_report.worth_preserving if state.heritage_report else False
        summary_reason = state.heritage_report.explanation if state.heritage_report else "N/A"

        scorecard_table = Table(title="Heritage Assessment Scorecard", show_header=False, expand=True)
        scorecard_table.add_row("[bold]Overall Score[/bold]", f"[bold yellow]{score}/100[/bold yellow]")
        scorecard_table.add_row("[bold]Worth Preserving[/bold]", f"[bold green]YES[/bold green]" if worth_preserving else "[bold red]NO[/bold red]")
        scorecard_table.add_row("[bold]Summary[/bold]", summary_reason)
        console.print(Panel(scorecard_table, border_style="cyan"))

        # Restoration plan display
        issues = state.restoration_plan.issues if state.restoration_plan else []
        estimated_hours = state.restoration_plan.estimated_effort_hours if state.restoration_plan else 0.0
        steps = state.restoration_plan.steps if state.restoration_plan else []

        plan_table = Table(title="Restoration Strategy & Actions", show_header=True, expand=True)
        plan_table.add_column("Property", style="bold magenta", width=25)
        plan_table.add_column("Details", style="white")

        if not issues:
            plan_table.add_row("Issues", "No major issues identified. Codebase is clean.")
        else:
            plan_table.add_row("Estimated Effort", f"{estimated_hours} engineering hours")
            issues_str = "\n".join([f"- [{iss.severity}] {iss.issue_type}: {iss.description}" for iss in issues])
            plan_table.add_row("Discovered Issues", issues_str)
            
        steps_str = "\n".join([f"{i+1}. {step}" for i, step in enumerate(steps)])
        plan_table.add_row("Recommended Setup Steps", steps_str or "None")
        console.print(Panel(plan_table, border_style="magenta"))

        # User approval
        approved = auto_approve
        if not approved:
            choice = typer.confirm("\nProceed with restoration execution and code repair?", default=False)
            approved = choice

        if not approved:
            console.print("\n[yellow]Excavation stopped by user request. Project remains in AWAITING_APPROVAL state.[/yellow]")
            write_reports(project_id, state)
            return

        # Stages 6 to 8
        console.print("\n[yellow][6/8][/yellow] Restoration Execution... ", end="")
        state.status = ExcavationStatus.AWAITING_APPROVAL
        await repository.save(state)
        state = await supervisor.approve_and_restore(project_id)

        if state.status == ExcavationStatus.COMPLETED:
            console.print("[green]DONE[/green]")
            console.print("[yellow][7/8][/yellow] Code Validation... [green]PASSED[/green]")
            console.print("[yellow][8/8][/yellow] Evolution Planning... [green]DONE[/green]")
        elif state.status == ExcavationStatus.VALIDATED:
            console.print("[green]DONE[/green]")
            console.print("[yellow][7/8][/yellow] Code Validation... [green]PASSED[/green]")
            console.print("[yellow][8/8][/yellow] Evolution Planning... [red]FAILED[/red]")
        elif state.status == ExcavationStatus.RESTORED:
            console.print("[green]DONE[/green]")
            console.print("[yellow][7/8][/yellow] Code Validation... [red]FAILED[/red]")
            console.print("[yellow][8/8][/yellow] Evolution Planning... [dim]SKIPPED[/dim]")
        else:
            console.print("[red]FAILED[/red]")
            console.print("[yellow][7/8][/yellow] Code Validation... [dim]SKIPPED[/dim]")
            console.print("[yellow][8/8][/yellow] Evolution Planning... [dim]SKIPPED[/dim]")

        # Evolution suggestions display
        if state.evolution_report and state.evolution_report.suggestions:
            sug_table = Table(title="Evolution Suggestions", show_header=True, expand=True)
            sug_table.add_column("Category/Type", style="bold yellow", width=25)
            sug_table.add_column("Recommendation Detail", style="white")

            for sug in state.evolution_report.suggestions:
                sug_table.add_row(sug.suggestion_type, f"[bold]{sug.title}[/bold]\n{sug.description}")
            
            console.print("\n")
            console.print(Panel(sug_table, border_style="yellow"))

        # Write reports
        report_dir = write_reports(project_id, state)
        console.print(f"\n[bold green]Excavation Completed Successfully![/bold green]")
        console.print(f"Archaeological report artifacts written to: [bold underline]{report_dir}[/bold underline]\n")

    except Exception as err:
        console.print(f"\n[bold red][ERROR] Excavation failed:[/bold red] {err}")
    finally:
        if temp_dir and os.path.exists(temp_dir):
            try:
                shutil.rmtree(temp_dir)
            except Exception:
                pass

def write_reports(project_id: str, state: ExcavationState) -> str:
    report_dir = os.path.abspath(os.path.join("reports", project_id))
    os.makedirs(report_dir, exist_ok=True)

    with open(os.path.join(report_dir, "repository_profile.json"), "w", encoding="utf-8") as f:
        json.dump(serialize_pydantic(state.profile), f, indent=2, default=str)

    with open(os.path.join(report_dir, "heritage_report.json"), "w", encoding="utf-8") as f:
        json.dump(serialize_pydantic(state.heritage_report), f, indent=2, default=str)

    with open(os.path.join(report_dir, "architecture_report.json"), "w", encoding="utf-8") as f:
        json.dump(serialize_pydantic(state.architecture_report), f, indent=2, default=str)

    with open(os.path.join(report_dir, "restoration_plan.json"), "w", encoding="utf-8") as f:
        json.dump(serialize_pydantic(state.restoration_plan), f, indent=2, default=str)

    validation_status = "PASSED" if state.status in (ExcavationStatus.VALIDATED, ExcavationStatus.COMPLETED) else "FAILED/UNRUN"
    val_data = {
        "status": validation_status,
        "logs": [
            serialize_pydantic(log) 
            for log in state.audit_logs 
            if log.action_type in ("VALIDATION_SUCCESS", "VALIDATION_FAILED", "VALIDATION_ERROR")
        ]
    }
    with open(os.path.join(report_dir, "validation_report.json"), "w", encoding="utf-8") as f:
        json.dump(val_data, f, indent=2, default=str)

    with open(os.path.join(report_dir, "evolution_report.json"), "w", encoding="utf-8") as f:
        json.dump(serialize_pydantic(state.evolution_report), f, indent=2, default=str)

    # Compile Summary markdown
    from datetime import datetime
    score = state.heritage_report.overall_score if state.heritage_report else 0
    preserving = "YES" if state.heritage_report and state.heritage_report.worth_preserving else "NO"
    reason = state.heritage_report.explanation if state.heritage_report else "N/A"
    
    issues_count = len(state.restoration_plan.issues) if state.restoration_plan else 0
    effort_hours = state.restoration_plan.estimated_effort_hours if state.restoration_plan else 0.0
    sug_count = len(state.evolution_report.suggestions) if state.evolution_report else 0

    md_content = f"""# ReForge Excavation Summary: {project_id}

Project ID: `{project_id}`
Repository URL: {state.repository_url}
Excavation Date: {datetime.utcnow().strftime("%Y-%m-%d %H:%M:%S UTC")}
Final Status: **{state.status.value}**

---

## 1. Heritage Assessment
* **Heritage Score:** {score}/100
* **Worth Preserving:** **{preserving}**
* **Assessment Summary:** {reason}

---

## 2. Software Overview
* **Primary Language:** {state.profile.primary_language if state.profile else "Unknown"}
* **Detected Frameworks:** {", ".join(state.software_overview.frameworks) if state.software_overview and state.software_overview.frameworks else "None"}
* **Detected Dependencies:** {", ".join(state.software_overview.dependencies) if state.software_overview and state.software_overview.dependencies else "None"}
* **Build System:** {state.software_overview.build_system if state.software_overview else "None"}

---

## 3. Architecture Report
* **Component Layers:** {", ".join(state.architecture_report.components) if state.architecture_report and state.architecture_report.components else "None"}
* **Coupling Boundaries:**
"""
    if state.architecture_report and state.architecture_report.relationships:
        for rel in state.architecture_report.relationships:
            md_content += f"  - `{rel}`\n"
    else:
        md_content += "  - None\n"

    md_content += f"""
---

## 4. Restoration Plan
* **Identified Issues:** {issues_count}
* **Estimated Restoration Effort:** {effort_hours} hours
"""
    if state.restoration_plan and state.restoration_plan.issues:
        md_content += "\n### Discovered Issues:\n"
        for issue in state.restoration_plan.issues:
            md_content += f"- **[{issue.severity}]** {issue.issue_type}: {issue.description}\n"

    md_content += f"""
---

## 5. Code Validation
* **Status:** **{validation_status}**

---

## 6. Evolution Suggestions
* **Total Recommendations:** {sug_count}
"""
    if state.evolution_report and state.evolution_report.suggestions:
        md_content += "\n### Recommendations:\n"
        for sug in state.evolution_report.suggestions:
            md_content += f"- **[{sug.suggestion_type}]** *{sug.title}*\n  {sug.description}\n"

    md_content += f"""
---
*Generated automatically by ReForge Software Archaeology.*
"""
    with open(os.path.join(report_dir, "summary.md"), "w", encoding="utf-8") as f:
        f.write(md_content)

    return report_dir

def excavate(
    target: str = typer.Argument(..., help="GitHub repository HTTPS URL or local directory path."),
    project_id: Optional[str] = typer.Option(None, "--project-id", "-p", help="Custom name for the project workspace directory."),
    auto_approve: bool = typer.Option(False, "--auto-approve", "-a", help="Skip restoration planning review confirmation.")
):
    """Execute the full 8-stage software excavation pipeline."""
    asyncio.run(run_excavation_workflow(target, project_id, auto_approve))
