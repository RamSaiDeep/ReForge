import math
import uuid
from datetime import datetime, timezone
from pydantic import BaseModel
from reforge.domain.interfaces import ArchaeologyAgent
from reforge.domain.models import (
    AgentLog,
    ExcavationState,
    ExcavationStatus,
    HeritageReport,
    PreservationCategory,
    PreservationProfile,
)

class HeritageEvaluator(ArchaeologyAgent):
    """The agent responsible for Stage 2 — Heritage Evaluation.

    Calculates the multi-dimensional Heritage Score and Preservation Profile.
    """

    @property
    def name(self) -> str:
        return "Heritage Evaluator"

    def _calculate_historical_value(self, state: ExcavationState) -> PreservationCategory:
        profile = state.profile
        score = 50  # Baseline
        explanations = ["Baseline historical value set to 50."]

        # Age evaluation
        repo_age_years = (datetime.now(timezone.utc) - profile.created_at).days / 365.25
        if repo_age_years > 10:
            score += 30
            explanations.append(f"Project is over 10 years old ({repo_age_years:.1f} years), indicating high historical lifespan (+30).")
        elif repo_age_years > 5:
            score += 15
            explanations.append(f"Project is over 5 years old ({repo_age_years:.1f} years) (+15).")
        else:
            explanations.append(f"Project is relatively new ({repo_age_years:.1f} years).")

        # Keyword evaluation
        keywords = {
            "pioneer": 10, "first": 10, "influence": 10, "classic": 10, 
            "legacy": 5, "milestone": 10, "original": 5, "historical": 10
        }
        readme = (profile.readme_content or "").lower()
        keyword_hits = []
        for kw, points in keywords.items():
            if kw in readme:
                score += points
                keyword_hits.append(kw)
        
        if keyword_hits:
            explanations.append(f"README contains historical keywords: {', '.join(keyword_hits)}.")
        
        score = min(100, max(0, score))
        return PreservationCategory(score=score, explanation=" ".join(explanations))

    def _calculate_community_value(self, state: ExcavationState) -> PreservationCategory:
        profile = state.profile
        explanations = []

        # Log scale mapping for stars, forks, and watchers
        # log10(10) = 1 -> 25 score, log10(100) = 2 -> 50 score, log10(1000) = 3 -> 75 score
        stars_score = min(100, int(math.log10(profile.stars + 1) * 25))
        forks_score = min(100, int(math.log10(profile.forks + 1) * 33))
        watchers_score = min(100, int(math.log10(profile.watchers + 1) * 33))

        explanations.append(f"Stars score: {stars_score}/100 ({profile.stars} stars).")
        explanations.append(f"Forks score: {forks_score}/100 ({profile.forks} forks).")
        explanations.append(f"Watchers score: {watchers_score}/100 ({profile.watchers} watchers).")

        weighted_score = int(0.5 * stars_score + 0.3 * forks_score + 0.2 * watchers_score)
        return PreservationCategory(score=weighted_score, explanation=" ".join(explanations))

    def _calculate_activity_value(self, state: ExcavationState) -> PreservationCategory:
        profile = state.profile
        # Calculate days since last commit
        last_commit = profile.last_commit_at
        if last_commit.tzinfo is None:
            last_commit = last_commit.replace(tzinfo=timezone.utc)
        
        days_since_commit = (datetime.now(timezone.utc) - last_commit).days
        
        if days_since_commit < 90:
            score = 100
            explanation = f"Active development: Last commit was {days_since_commit} days ago (within 3 months). Low immediate need for archaeological recovery."
        elif days_since_commit < 365:
            score = 80
            explanation = f"Slightly inactive: Last commit was {days_since_commit} days ago (within 1 year). Maintainers might be stepping away."
        elif days_since_commit < 1095:
            score = 50
            explanation = f"Inactive: Last commit was {days_since_commit} days ago (1-3 years). Project is entering abandoned state."
        else:
            score = 20
            explanation = f"Abandoned: Last commit was {days_since_commit} days ago (over 3 years). Strong preservation candidate."

        return PreservationCategory(score=score, explanation=explanation)

    def _calculate_restoration_feasibility(self, state: ExcavationState) -> PreservationCategory:
        profile = state.profile
        score = 30  # Baseline
        explanations = ["Baseline restoration feasibility set to 30."]

        if not profile.readme_content:
            score = 10
            return PreservationCategory(score=score, explanation="README is missing or empty, making discovery of build parameters highly difficult.")

        # Check build system indicators
        build_indicators = {
            "cmake": 15, "makefile": 15, "package.json": 15, "requirements.txt": 15,
            "pyproject.toml": 15, "cargo.toml": 20, "go.mod": 20, "pom.xml": 15,
            "build.gradle": 15, "setup.py": 10
        }
        
        readme = profile.readme_content.lower()
        matched = []
        for indicator, points in build_indicators.items():
            if indicator in readme:
                score += points
                matched.append(indicator)

        if matched:
            explanations.append(f"Identified potential build configurations: {', '.join(matched)} (+{len(matched) * 15}).")
        else:
            explanations.append("No common build configurations identified in readme.")

        # License checks (GPL, MIT, Apache are easy to restore and distribute)
        if profile.license:
            score += 10
            explanations.append(f"Permissive or open license '{profile.license}' detected (+10).")

        score = min(100, max(0, score))
        return PreservationCategory(score=score, explanation=" ".join(explanations))

    def _calculate_educational_value(self, state: ExcavationState) -> PreservationCategory:
        profile = state.profile
        score = 40  # Baseline
        explanations = ["Baseline educational value set to 40."]

        keywords = {
            "compiler": 15, "interpreter": 15, "engine": 15, "algorithm": 15,
            "classic": 10, "education": 10, "tutorial": 10, "learn": 10,
            "course": 10, "research": 10
        }
        readme = (profile.readme_content or "").lower()
        matched = []
        for kw, points in keywords.items():
            if kw in readme:
                score += points
                matched.append(kw)

        if matched:
            explanations.append(f"README contains academic/educational keywords: {', '.join(matched)}.")

        score = min(100, max(0, score))
        return PreservationCategory(score=score, explanation=" ".join(explanations))

    def _calculate_innovation_value(self, state: ExcavationState) -> PreservationCategory:
        profile = state.profile
        score = 50  # Baseline
        explanations = ["Baseline innovation potential set to 50."]

        keywords = {
            "unique": 10, "experimental": 10, "novel": 15, "prototype": 10,
            "architecture": 10, "custom": 5
        }
        readme = (profile.readme_content or "").lower()
        matched = []
        for kw, points in keywords.items():
            if kw in readme:
                score += points
                matched.append(kw)

        if matched:
            explanations.append(f"README lists innovation keywords: {', '.join(matched)}.")

        # Language modernity check
        modern_languages = ["python", "rust", "go", "typescript", "kotlin", "swift"]
        if (profile.primary_language or "").lower() in modern_languages:
            score += 10
            explanations.append(f"Uses a modern and highly-supported primary language '{profile.primary_language}' (+10).")

        score = min(100, max(0, score))
        return PreservationCategory(score=score, explanation=" ".join(explanations))

    async def run(self, state: ExcavationState) -> HeritageReport:
        if not state.profile:
            raise ValueError("ExcavationState must contain a RepositoryProfile to run Heritage Evaluation.")

        state.status = ExcavationStatus.EVALUATING
        state.updated_at = datetime.utcnow()

        start_time = datetime.utcnow()
        input_params = {
            "project_id": state.project_id,
            "repository_url": state.repository_url
        }

        try:
            # 1. Calculate each category
            historical = self._calculate_historical_value(state)
            community = self._calculate_community_value(state)
            activity = self._calculate_activity_value(state)
            feasibility = self._calculate_restoration_feasibility(state)
            educational = self._calculate_educational_value(state)
            innovation = self._calculate_innovation_value(state)

            # 2. Calculate overall weighted score
            overall_score = round(
                0.25 * historical.score +
                0.20 * community.score +
                0.10 * activity.score +
                0.20 * feasibility.score +
                0.10 * educational.score +
                0.15 * innovation.score
            )

            # 3. Determine worthiness
            # ReForge Constitution: Abandoned software with educational/historical value deserves restoration
            worth_preserving = (
                overall_score >= 50 or 
                historical.score >= 70 or 
                educational.score >= 70
            )

            # 4. Generate guiding question answer
            reasons = []
            if historical.score >= 70:
                reasons.append("It represents a significant technological milestone or has historical ecosystem influence.")
            if educational.score >= 70:
                reasons.append("It holds high pedagogical value, making it an excellent learning resource for classic software engineering concepts.")
            if community.score >= 60:
                reasons.append("There remains strong community interest despite its inactive status.")
            if worth_preserving and not reasons:
                reasons.append("It displays solid overall technical value and presents a practical restoration roadmap.")

            if worth_preserving:
                guiding_answer = (
                    "This software deserves another chapter because: " + " ".join(reasons)
                )
            else:
                guiding_answer = "This software does not meet the preservation threshold under the current evaluation parameters."

            # Construct report
            profile = PreservationProfile(
                historical_value=historical,
                community_value=community,
                activity_sustainability=activity,
                restoration_feasibility=feasibility,
                educational_value=educational,
                innovation_evolution_potential=innovation
            )

            report = HeritageReport(
                repository_url=state.repository_url,
                overall_score=overall_score,
                profile=profile,
                worth_preserving=worth_preserving,
                guiding_question_answer=guiding_answer,
                explanation=(
                    f"Heritage evaluation completed. Overall score: {overall_score}/100. "
                    f"Historical: {historical.score}, Educational: {educational.score}, "
                    f"Feasibility: {feasibility.score}. Worth preserving: {worth_preserving}."
                )
            )

            state.heritage_report = report
            
            # Transition state based on worthiness
            if worth_preserving:
                state.status = ExcavationStatus.EVALUATED
            else:
                state.status = ExcavationStatus.STOPPED
                
            state.updated_at = datetime.utcnow()

            # Audit log
            log_entry = AgentLog(
                id=str(uuid.uuid4()),
                project_id=state.project_id,
                agent_name=self.name,
                action_type="HERITAGE_EVALUATION",
                timestamp=datetime.utcnow(),
                input_parameters=input_params,
                output_result=report.model_dump_json(indent=2),
                explanation=report.explanation
            )
            state.audit_logs.append(log_entry)
            return report

        except Exception as err:
            state.status = ExcavationStatus.FAILED
            state.updated_at = datetime.utcnow()
            error_message = f"{type(err).__name__}: {str(err)}"
            log_entry = AgentLog(
                id=str(uuid.uuid4()),
                project_id=state.project_id,
                agent_name=self.name,
                action_type="HERITAGE_EVALUATION_FAILED",
                timestamp=datetime.utcnow(),
                input_parameters=input_params,
                output_result=error_message,
                explanation=f"Heritage Evaluation failed. Error: {error_message}"
            )
            state.audit_logs.append(log_entry)
            raise err
