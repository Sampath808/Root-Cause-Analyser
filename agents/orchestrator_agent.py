from google.adk import Agent
from typing import Dict, List, Any, Callable
import sys
import os
import json
import time

# Add parent directory to path for imports
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

try:
    from openai import OpenAI
except ImportError:
    print(
        "Error: 'openai' package is missing. Please install it using: pip install openai"
    )
    sys.exit(1)

from models.bug_report import BugReport
from models.analysis_result import AnalysisResult
from .root_cause_agent import RootCauseAgent
from .critique_agent import CritiqueAgent
from utils.config import config


class OrchestratorAgent:
    """Intelligent orchestrator that manages the workflow between RCA and Critique agents using OpenAI via ADK Wrapper."""

    def __init__(self, rca_agent: RootCauseAgent, critique_agent: CritiqueAgent):
        self.rca_agent = rca_agent
        self.critique_agent = critique_agent

        # Initialize OpenAI client
        api_key = getattr(config, "openai_api_key", None) or os.getenv("OPENAI_API_KEY")
        if not api_key:
            raise ValueError(
                "OpenAI API Key not found. Please set OPENAI_API_KEY environment variable or config."
            )

        self.client = OpenAI(api_key=api_key)

        # Define ADK Agent
        self.agent = Agent(
            name="orchestrator",
            model="gpt-4o",
            instruction=self._get_system_instruction(),
            tools=self._create_orchestrator_tools_list(),
        )

    def _get_system_instruction(self) -> str:
        return """You are an intelligent orchestrator managing a root cause analysis workflow. You coordinate between two specialized agents:

1. **RCA Agent**: Performs initial root cause analysis on bugs
2. **Critique Agent**: Reviews and validates the RCA analysis

YOUR WORKFLOW MANAGEMENT:

1. **Start Analysis**: Always begin by calling run_rca_analysis() with the bug report
2. **Review Analysis**: After RCA completes, call run_critique_analysis() to review the results
3. **Decision Making**: Based on critique results:
   - If APPROVED: Finalize and return the analysis
   - If NOT APPROVED: Send back to RCA with critique feedback for rework
4. **Iteration Control**: Continue the RCA -> Critique loop until:
   - Critique approves the analysis, OR
   - Maximum iterations reached (default: 3)

DECISION CRITERIA:
- Always run critique after each RCA analysis
- If critique finds significant issues, require RCA rework
- Consider confidence scores and specific feedback
- Balance thoroughness with efficiency

COMMUNICATION:
- Provide clear status updates during the workflow
- Explain decisions (why sending back for rework, why approving)
- Include iteration counts and confidence scores
- Summarize final results

Your goal is to ensure high-quality, accurate root cause analysis through intelligent coordination of the specialized agents."""

    def _create_orchestrator_tools_list(self) -> List[Callable]:
        return [
            self.run_rca_analysis,
            self.run_critique_analysis,
            self.make_workflow_decision,
            self.finalize_analysis,
            self.request_rca_rework,
        ]

    def _get_tools_schema(self) -> List[Dict]:
        """Define orchestrator tools schema for OpenAI"""
        return [
            {
                "type": "function",
                "function": {
                    "name": "run_rca_analysis",
                    "description": "Run root cause analysis on a bug report.",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "bug_title": {
                                "type": "string",
                                "description": "Title of the bug (for logging)",
                            }
                        },
                        "required": ["bug_title"],
                    },
                },
            },
            {
                "type": "function",
                "function": {
                    "name": "run_critique_analysis",
                    "description": "Run critique analysis on the RCA results.",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "analysis_summary": {
                                "type": "string",
                                "description": "Short summary of the analysis",
                            }
                        },
                        "required": ["analysis_summary"],
                    },
                },
            },
            {
                "type": "function",
                "function": {
                    "name": "make_workflow_decision",
                    "description": "Make intelligent decision about next workflow step.",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "iteration": {
                                "type": "integer",
                                "description": "Current iteration count",
                            },
                            "max_iterations": {
                                "type": "integer",
                                "description": "Maximum allowed iterations",
                            },
                            "critique_approved": {
                                "type": "boolean",
                                "description": "Whether the critique approved the analysis",
                            },
                            "confidence": {
                                "type": "number",
                                "description": "Current confidence score",
                            },
                        },
                        "required": [
                            "iteration",
                            "max_iterations",
                            "critique_approved",
                            "confidence",
                        ],
                    },
                },
            },
            {
                "type": "function",
                "function": {
                    "name": "finalize_analysis",
                    "description": "Finalize the analysis with updated confidence and comments.",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "final_confidence": {
                                "type": "number",
                                "description": "Final confidence score (0-1)",
                            },
                            "final_comments": {
                                "type": "string",
                                "description": "Final closing comments",
                            },
                        },
                        "required": ["final_confidence", "final_comments"],
                    },
                },
            },
            {
                "type": "function",
                "function": {
                    "name": "request_rca_rework",
                    "description": "Request RCA agent to rework the analysis based on critique feedback.",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "feedback": {
                                "type": "string",
                                "description": "Specific feedback for rework",
                            },
                            "iteration": {
                                "type": "integer",
                                "description": "Current iteration number",
                            },
                        },
                        "required": ["feedback", "iteration"],
                    },
                },
            },
        ]

    # Tool Implementation Methods
    def run_rca_analysis(self, bug_title: str) -> str:
        """Run root cause analysis on a bug report."""
        try:
            if hasattr(self, "current_bug_report"):
                analysis = self.rca_agent.analyze_bug(self.current_bug_report)
                self.current_analysis = analysis

                return f"""RCA Analysis Complete:
Title: {analysis.bug_report_title}
Confidence: {analysis.confidence_score}
File: {analysis.root_cause.file_path}
Lines: {analysis.root_cause.line_numbers}
Explanation: {analysis.root_cause.explanation[:500]}...
Tools Used: {analysis.tools_used}
Iterations: {analysis.iterations}"""
            else:
                return "Error: No bug report available for analysis"
        except Exception as e:
            return f"RCA Analysis Error: {str(e)}"

    def run_critique_analysis(self, analysis_summary: str) -> str:
        """Run critique analysis on the RCA results."""
        try:
            if hasattr(self, "current_analysis") and hasattr(
                self, "current_bug_report"
            ):
                critique_result = self.critique_agent.critique(
                    self.current_bug_report, self.current_analysis
                )
                self.current_critique = critique_result

                return f"""Critique Analysis Complete:
Approved: {critique_result['approved']}
Confidence Adjustment: {critique_result['confidence_adjustment']}
Comments: {critique_result['comments'][:500]}...
Suggested Improvements: {critique_result['suggested_improvements']}"""
            else:
                return "Error: No analysis available for critique"
        except Exception as e:
            return f"Critique Analysis Error: {str(e)}"

    def make_workflow_decision(
        self,
        iteration: int,
        max_iterations: int,
        critique_approved: bool,
        confidence: float,
    ) -> str:
        if critique_approved:
            return "FINALIZE_APPROVED"
        elif iteration >= max_iterations:
            return "FINALIZE_MAX_ITERATIONS"
        elif confidence < 0.5:
            return "REWORK_LOW_CONFIDENCE"
        else:
            return "REWORK_CRITIQUE_ISSUES"

    def finalize_analysis(self, final_confidence: float, final_comments: str) -> str:
        try:
            if hasattr(self, "current_analysis"):
                self.current_analysis.confidence_score = final_confidence
                self.current_analysis.critique_approved = True
                return f"Analysis finalized with confidence: {final_confidence}"
            return "No analysis to finalize"
        except Exception as e:
            return f"Finalization Error: {str(e)}"

    def request_rca_rework(self, feedback: str, iteration: int) -> str:
        return f"RCA rework requested (iteration {iteration}): {feedback}"

    def _execute_agent_with_openai(self, user_prompt: str) -> str:
        """Adapter method: Executes the ADK Agent using OpenAI"""
        messages = [
            {"role": "system", "content": self.agent.instruction},
            {"role": "user", "content": user_prompt},
        ]

        tools = self._get_tools_schema()
        available_functions = {func.__name__: func for func in self.agent.tools}

        max_turns = 15
        current_turn = 0

        while current_turn < max_turns:
            current_turn += 1

            try:
                response = self.client.chat.completions.create(
                    model=self.agent.model,
                    messages=messages,
                    tools=tools,
                    tool_choice="auto",
                )

                response_message = response.choices[0].message

                if not response_message.tool_calls:
                    return response_message.content

                messages.append(response_message)

                for tool_call in response_message.tool_calls:
                    function_name = tool_call.function.name
                    function_args = json.loads(tool_call.function.arguments)

                    if function_name in available_functions:
                        function_to_call = available_functions[function_name]
                        try:
                            function_response = function_to_call(**function_args)
                            if not isinstance(function_response, str):
                                function_response = str(function_response)
                        except Exception as e:
                            function_response = (
                                f"Error executing {function_name}: {str(e)}"
                            )
                    else:
                        function_response = f"Error: Function {function_name} not found"

                    messages.append(
                        {
                            "role": "tool",
                            "tool_call_id": tool_call.id,
                            "name": function_name,
                            "content": function_response,
                        }
                    )

            except Exception as e:
                print(f"OpenAI API Error: {str(e)}")
                time.sleep(1)
                return f"Error during OpenAI execution: {str(e)}"

        return "Error: Maximum conversation turns reached."

    def run_analysis(
        self, bug_report: BugReport, max_refinement_iterations: int = 3
    ) -> AnalysisResult:
        """Run complete analysis with intelligent orchestration"""
        print("\n" + "=" * 80)
        print("INTELLIGENT ORCHESTRATOR: Starting Analysis Workflow (ADK via OpenAI)")
        print("=" * 80)
        print(f"Bug: {bug_report.title}")
        print(f"Max refinement iterations: {max_refinement_iterations}\n")

        self.current_bug_report = bug_report
        self.current_analysis = None
        self.current_critique = None

        orchestration_prompt = f"""Manage the root cause analysis workflow for this bug:

BUG REPORT:
Title: {bug_report.title}
Description: {bug_report.description}
Steps to Reproduce: {bug_report.steps_to_reproduce}
Expected Behavior: {bug_report.expected_behavior}
Actual Behavior: {bug_report.actual_behavior}
Error Message: {bug_report.error_message or 'None'}

WORKFLOW PARAMETERS:
- Maximum refinement iterations: {max_refinement_iterations}
- Target confidence threshold: 0.7

Start the analysis workflow now. Use the available tools to:
1. Run RCA analysis using run_rca_analysis()
2. Run critique analysis using run_critique_analysis()
3. Make decisions using make_workflow_decision()
4. Iterate if needed using request_rca_rework()
5. Finalize when approved using finalize_analysis()"""

        try:
            print("🤖 Starting intelligent orchestration...")

            response_text = self._execute_agent_with_openai(orchestration_prompt)

            print("\n" + "=" * 80)
            print("ORCHESTRATION COMPLETE")
            print("=" * 80)
            print(response_text)
            print("=" * 80)

            if self.current_analysis:
                print("✅ Agent successfully orchestrated the analysis via tools.")
                return self.current_analysis
            else:
                print(
                    "⚠️ Agent did not complete analysis. Falling back to manual workflow."
                )
                return self._execute_workflow(bug_report, max_refinement_iterations)

        except Exception as e:
            print(f"Error during orchestration: {str(e)}")
            return self._execute_workflow(bug_report, max_refinement_iterations)

    def _execute_workflow(
        self, bug_report: BugReport, max_iterations: int
    ) -> AnalysisResult:
        """Execute the actual workflow with critique loop (Fallback/Manual Mode)"""
        analysis = None

        for iteration in range(max_iterations):
            print(f"\n--- Iteration {iteration+1}/{max_iterations} ---")

            if analysis is None:
                print("🔍 Running initial RCA analysis...")
                analysis = self.rca_agent.analyze_bug(bug_report)
            else:
                print("🔄 Running RCA rework...")
                analysis = self.rca_agent.analyze_bug(bug_report)

            print("🧐 Running critique analysis...")
            critique = self.critique_agent.critique(bug_report, analysis)

            analysis.critique_approved = critique["approved"]
            analysis.critique_comments = critique["comments"]
            analysis.confidence_score += critique["confidence_adjustment"]
            analysis.confidence_score = max(0.0, min(1.0, analysis.confidence_score))

            if critique["approved"]:
                print("✅ Analysis approved by critique!")
                break
            elif iteration == max_iterations - 1:
                print("⚠️ Max iterations reached, finalizing current analysis")
                break
            else:
                print("❌ Critique not approved, preparing for rework...")

        print("\n" + "=" * 80)
        print("WORKFLOW COMPLETE")
        print("=" * 80)

        return analysis
