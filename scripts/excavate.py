import argparse
import asyncio
import json
import os
import shutil
import sys
import tempfile
from typing import Dict, Any

# Ensure reforge is in sys.path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))

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
    """Safely serialize Pydantic model or return dict representation."""
    if hasattr(model, "model_dump"):
        return model.model_dump()
    return {}

def print_separator(char: str = "=", length: int = 50):
    print(char * length)

async def main_async():
    parser = argparse.ArgumentParser(
        description="ReForge Software Archaeology CLI: Excavate, restore, and evolve legacy repositories."
    )
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument("--repo", help="HTTPS URL of the remote GitHub repository to clone and excavate.")
    group.add_argument("--local", help="Path to a local repository/directory to excavate.")
    
    parser.add_argument("--project-id", help="Customized project identifier. Defaults to the repository name.")
    parser.add_argument(
        "--auto-approve",
        action="store_true",
        help="Auto-approve the restoration plan and continue without interactive prompt."
    )
    
    args = parser.parse_args()

    # Determine project ID
    if args.project_id:
        project_id = args.project_id
    else:
        # Infer name from URL or local path
        target = args.repo or args.local
        project_id = target.rstrip("/").split("/")[-1].replace(".git", "")
        if not project_id:
            project_id = "excavated-project"

    print_separator()
    print("ReForge Software Archaeology CLI")
    print_separator()
    
    target_source = args.repo or args.local
    print(f"Target Project ID: {project_id}")
    print(f"Source:            {target_source}")
    print_separator("-")

    # Setup temporary directory for cloning if remote repository
    temp_dir = None
    if args.repo:
        temp_dir = tempfile.mkdtemp(prefix="reforge-")
        local_path = temp_dir
    else:
        local_path = os.path.abspath(args.local)

    # Initialize production singletons
    repository = InMemoryProjectRepository()
    git_provider = GitHubProvider()
    git_cloner = LocalGitCloner()
    workspace_inspector = LocalWorkspaceInspector()
    code_analyzer = LocalCodeAnalyzer()
    restoration_executor = LocalRestorationExecutor()
    code_validator = LocalCodeValidator()

    # Initialize agents
    scout_agent = ScoutAgent(git_provider=git_provider)
    heritage_evaluator = HeritageEvaluator()
    # Explorer clones/copies. For --local, explorer can copy the folder to a staging workspace or inspect directly.
    # Since ExplorerAgent expects to copy from a source repo URL, let's configure the URL appropriately:
    # If args.local, the cloner will run copy locally. Our LocalGitCloner supports file:/// or local folder copying.
    explorer_agent = ExplorerAgent(cloner=git_cloner, inspector=workspace_inspector)
    architect_agent = ArchitectAgent(analyzer=code_analyzer)
    restoration_planner = RestorationPlannerAgent()
    restorer_agent = RestorerAgent(executor=restoration_executor)
    validation_agent = ValidationAgent(validator=code_validator)
    evolution_planner = EvolutionPlannerAgent()

    # Initialize workflow supervisor
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
        # Create excavation project
        repo_url = args.repo or f"file:///{local_path.replace(os.sep, '/')}"
        state = await supervisor.create_project(project_id, repo_url)
        # If --local is specified, we can bypass the cloner source and manually populate local_path beforehand
        # to point to the user's directory directly
        if args.local:
            state.local_path = local_path

        # ----------------------------------------------------
        # Stages 1 to 5: Analysis & Planning
        # ----------------------------------------------------
        
        # Scout
        print("[1/8] Discovery... ", end="", flush=True)
        state.status = ExcavationStatus.DISCOVERING
        await scout_agent.run(state)
        print("DONE")

        # Heritage
        print("[2/8] Heritage Evaluation... ", end="", flush=True)
        await heritage_evaluator.run(state)
        print("DONE")

        # Explorer (Clone/Copy if needed)
        print("[3/8] Software Understanding... ", end="", flush=True)
        # Setup local path if it was cloned
        if args.repo:
            state.local_path = os.path.join(local_path, project_id)
            # Ensure folder exists
            os.makedirs(state.local_path, exist_ok=True)
            # Use explorer cloner to copy/clone
            await explorer_agent.run(state)
        else:
            await explorer_agent.run(state)
        print("DONE")

        # Architect
        print("[4/8] Architecture Reconstruction... ", end="", flush=True)
        await architect_agent.run(state)
        print("DONE")

        # Restoration Planning
        print("[5/8] Restoration Planning... ", end="", flush=True)
        await restoration_planner.run(state)
        print("DONE")
        print_separator("-")

        # Save current state to database
        await repository.save(state)

        # ----------------------------------------------------
        # Display Scorecard & Plan
        # ----------------------------------------------------
        print("HERITAGE SCORECARD")
        print_separator("-")
        
        score = 0
        worth_preserving = False
        summary_reason = "No details"
        if state.heritage_report:
            score = state.heritage_report.overall_score
            worth_preserving = state.heritage_report.worth_preserving
            summary_reason = state.heritage_report.explanation
            
        print(f"Overall Heritage Score: {score}/100")
        print(f"Worth Preserving:       {'YES' if worth_preserving else 'NO'}")
        print(f"Assessment Reason:      {summary_reason}")
        
        print_separator("-")
        print("RESTORATION PLAN")
        print_separator("-")
        
        issues = []
        estimated_hours = 0.0
        steps = []
        if state.restoration_plan:
            issues = state.restoration_plan.issues
            estimated_hours = state.restoration_plan.estimated_effort_hours
            steps = state.restoration_plan.steps
            
        if not issues:
            print("No major issues detected. Restoration not required.")
        else:
            print(f"Estimated effort: {estimated_hours} hours")
            print(f"Identified {len(issues)} issues:")
            for issue in issues:
                print(f" - [{issue.severity}] {issue.issue_type}: {issue.description}")
            print("\nRecommended setup steps:")
            for step in steps:
                print(f" - {step}")
                
        print_separator("-")

        # ----------------------------------------------------
        # Prompt / Confirmation
        # ----------------------------------------------------
        approved = args.auto_approve
        if not approved:
            choice = input("Proceed with restoration? [y/N]: ").strip().lower()
            approved = choice in ("y", "yes")

        if not approved:
            print("Excavation halted. Project remains in AWAITING_APPROVAL state.")
            # Write partial reports
            write_reports(project_id, state)
            return

        # ----------------------------------------------------
        # Stages 6 to 8: Restoration, Validation, Evolution
        # ----------------------------------------------------
        print("[6/8] Restoration Execution... ", end="", flush=True)
        # Transition state status to trigger approve flow
        state.status = ExcavationStatus.AWAITING_APPROVAL
        await repository.save(state)
        
        # Execute approve_and_restore which runs Stage 6, Stage 7 (Validation), and Stage 8 (Evolution)
        state = await supervisor.approve_and_restore(project_id)
        
        # Check if restoration completed
        if state.status == ExcavationStatus.COMPLETED:
            print("DONE")
            print("[7/8] Code Validation... PASSED")
            print("[8/8] Evolution Planning... DONE")
        elif state.status == ExcavationStatus.VALIDATED:
            print("DONE")
            print("[7/8] Code Validation... PASSED")
            print("[8/8] Evolution Planning... FAILED")
        elif state.status == ExcavationStatus.RESTORED:
            print("DONE")
            print("[7/8] Code Validation... FAILED")
            print("[8/8] Evolution Planning... SKIPPED")
        else:
            print("FAILED")
            print("[7/8] Code Validation... SKIPPED")
            print("[8/8] Evolution Planning... SKIPPED")
            
        print_separator("-")

        # ----------------------------------------------------
        # Display Evolution Suggestions & Output Reports
        # ----------------------------------------------------
        if state.evolution_report and state.evolution_report.suggestions:
            print("EVOLUTION SUGGESTIONS")
            print_separator("-")
            print(f"Generated {len(state.evolution_report.suggestions)} recommendations:")
            for sug in state.evolution_report.suggestions:
                print(f" - [{sug.suggestion_type}] {sug.title}")
                print(f"   {sug.description}")
            print_separator("-")

        # Write reports
        report_dir = write_reports(project_id, state)
        print(f"Reports successfully written to:\n{report_dir}")
        print_separator()

    except Exception as err:
        print(f"\n[ERROR] Excavation failed: {err}")
        import traceback
        traceback.print_exc()
    finally:
        # Clean up temporary cloning directory
        if temp_dir and os.path.exists(temp_dir):
            try:
                shutil.rmtree(temp_dir)
            except Exception:
                pass

def write_reports(project_id: str, state: ExcavationState) -> str:
    """Helper to write all stage data objects and a markdown summary to disk."""
    report_dir = os.path.abspath(os.path.join("reports", project_id))
    os.makedirs(report_dir, exist_ok=True)

    # 1. Profile JSON
    with open(os.path.join(report_dir, "repository_profile.json"), "w", encoding="utf-8") as f:
        json.dump(serialize_pydantic(state.profile), f, indent=2, default=str)

    # 2. Heritage Report JSON
    with open(os.path.join(report_dir, "heritage_report.json"), "w", encoding="utf-8") as f:
        json.dump(serialize_pydantic(state.heritage_report), f, indent=2, default=str)

    # 3. Architecture Report JSON
    with open(os.path.join(report_dir, "architecture_report.json"), "w", encoding="utf-8") as f:
        json.dump(serialize_pydantic(state.architecture_report), f, indent=2, default=str)

    # 4. Restoration Plan JSON
    with open(os.path.join(report_dir, "restoration_plan.json"), "w", encoding="utf-8") as f:
        json.dump(serialize_pydantic(state.restoration_plan), f, indent=2, default=str)

    # 5. Validation Report JSON
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

    # 6. Evolution Report JSON
    with open(os.path.join(report_dir, "evolution_report.json"), "w", encoding="utf-8") as f:
        json.dump(serialize_pydantic(state.evolution_report), f, indent=2, default=str)

    # 7. Summary MD
    summary_path = os.path.join(report_dir, "summary.md")
    
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
"""

    md_content += f"""
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
    with open(summary_path, "w", encoding="utf-8") as f:
        f.write(md_content)

    return report_dir

if __name__ == "__main__":
    from datetime import datetime
    asyncio.run(main_async())
