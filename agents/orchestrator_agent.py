from typing import Dict
import sys
import os

# Add parent directory to path for imports
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from models.bug_report import BugReport
from models.analysis_result import AnalysisResult
from .root_cause_agent import RootCauseAgent
from .critique_agent import CritiqueAgent

class OrchestratorAgent:
    """Manages the workflow between RCA and Critique agents.
    Handles iteration and final report generation."""

    def __init__(self, rca_agent: RootCauseAgent, critique_agent: CritiqueAgent):
        self.rca_agent = rca_agent
        self.critique_agent = critique_agent

    def run_analysis(self, bug_report: BugReport, max_refinement_iterations: int = 2) -> AnalysisResult:
        """Run complete analysis with critique loop
        
        Args:
            bug_report: The bug to analyze
            max_refinement_iterations: How many times to refine based on critique
            
        Returns:
            Final approved analysis result
        """
        print("\n" + "="*80)
        print("ORCHESTRATOR: Starting Analysis Workflow")
        print("="*80)

        # Initial RCA
        print("\nPhase 1: Root Cause Analysis")
        analysis = self.rca_agent.analyze_bug(bug_report)

        # Critique loop
        for iteration in range(max_refinement_iterations):
            print(f"\nPhase 2.{iteration+1}: Critique")
            critique = self.critique_agent.critique(bug_report, analysis)

            if critique['approved']:
                print("Critique approved the analysis!")
                analysis.critique_approved = True
                analysis.critique_comments = critique['comments']
                analysis.confidence_score += critique['confidence_adjustment']
                analysis.confidence_score = max(0.0, min(1.0, analysis.confidence_score))
                break
            else:
                print(f"Critique found issues (iteration {iteration+1}/{max_refinement_iterations})")
                print(f"Issues: {critique['comments']}")
                
                if iteration < max_refinement_iterations - 1:
                    # Refine analysis based on critique
                    # TODO: Implement refinement logic
                    pass

        print("\n" + "="*80)
        print("FINAL REPORT GENERATED")
        print("="*80)

        return analysis