"""Pure A2A-compatible Root Cause Analysis Agent with self-improvement capabilities."""

from google import genai
from google.genai import types
from typing import Dict, Any, List
import json
from datetime import datetime
import time
import random
import re
import sys
import os

# Add parent directory to path for imports
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from models.bug_report import BugReport
from models.analysis_result import AnalysisResult, RootCause, ToolExecutionResult
from core.github_client import GitHubClient
from utils.config import config


class RootCauseAgent:
    """Pure A2A-compatible Root Cause Analysis Agent with self-improvement."""

    def __init__(self, gemini_api_key: str, github_client: GitHubClient):
        """Initialize RCA Agent for A2A orchestration.

        Args:
            gemini_api_key: Google Gemini API key
            github_client: Initialized GitHub client
        """
        self.agent_id = "rca_agent"
        self.agent_type = "root_cause_analyzer"
        self.capabilities = [
            "bug_analysis",
            "code_investigation",
            "commit_tracking",
            "author_identification",
            "self_improvement",
        ]

        # Initialize LLM client
        self.client = genai.Client(api_key=gemini_api_key)
        self.model_id = config.gemini_model
        self.github = github_client

        # A2A state management
        self.conversation_history = []
        self.tool_executions = []
        self.improvement_feedback = []  # Store critique feedback for self-improvement

    def get_agent_info(self) -> Dict[str, Any]:
        """Return agent information for A2A orchestrator."""
        return {
            "agent_id": self.agent_id,
            "agent_type": self.agent_type,
            "capabilities": self.capabilities,
            "supported_tasks": [
                "analyze_bug",
                "improve_analysis",
                "get_analysis_status",
            ],
            "input_formats": ["bug_report", "improvement_feedback"],
            "output_formats": ["analysis_result", "status_report"],
            "description": "Analyzes bugs using LLM-guided GitHub exploration with self-improvement",
            "version": "2.0.0",
        }

    def process(self, message: Dict[str, Any]) -> Dict[str, Any]:
        """Process A2A message and return structured response.

        Args:
            message: A2A message with task request

        Returns:
            A2A response message with results
        """
        try:
            # Validate message format
            if not self._validate_message(message):
                return self._create_error_response(message, "Invalid message format")

            # Extract task information
            content = message.get("content", {})
            task = content.get("task")
            data = content.get("data", {})

            # Route to appropriate handler
            if task == "analyze_bug":
                return self._handle_analyze_bug(message, data)
            elif task == "improve_analysis":
                return self._handle_improve_analysis(message, data)
            elif task == "get_analysis_status":
                return self._handle_get_status(message, data)
            else:
                return self._create_error_response(
                    message,
                    f"Unsupported task: {task}. Supported: analyze_bug, improve_analysis, get_analysis_status",
                )

        except Exception as e:
            return self._create_error_response(message, f"Processing error: {str(e)}")

    def _handle_analyze_bug(
        self, message: Dict[str, Any], data: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Handle bug analysis task."""
        try:
            # Extract bug report
            bug_report_data = data.get("bug_report")
            if not bug_report_data:
                return self._create_error_response(
                    message, "Missing 'bug_report' in task data"
                )

            bug_report = BugReport.from_dict(bug_report_data)
            max_iterations = data.get("max_iterations", config.max_rca_iterations)

            print(f"[RCA-Agent] Starting analysis for: {bug_report.title}")

            # Clear previous state for new analysis
            self.conversation_history = []
            self.tool_executions = []

            # Perform analysis with self-improvement context
            analysis_result = self._analyze_bug_with_improvement(
                bug_report, max_iterations
            )

            return self._create_success_response(
                message,
                {
                    "task": "analyze_bug",
                    "analysis": analysis_result.to_dict(),
                    "metadata": {
                        "iterations_used": analysis_result.iterations,
                        "tools_used": analysis_result.tools_used,
                        "confidence_score": analysis_result.confidence_score,
                        "improvement_applied": len(self.improvement_feedback) > 0,
                    },
                },
            )

        except Exception as e:
            return self._create_error_response(message, f"Analysis failed: {str(e)}")

    def _handle_improve_analysis(
        self, message: Dict[str, Any], data: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Handle analysis improvement based on critique feedback."""
        try:
            # Extract improvement data
            critique_feedback = data.get("critique_feedback")
            original_analysis = data.get("original_analysis")
            bug_report_data = data.get("bug_report")

            if not all([critique_feedback, original_analysis, bug_report_data]):
                return self._create_error_response(
                    message,
                    "Missing required data: critique_feedback, original_analysis, bug_report",
                )

            # Store feedback for future improvements
            self.improvement_feedback.append(
                {
                    "timestamp": datetime.now().isoformat(),
                    "feedback": critique_feedback,
                    "original_analysis": original_analysis,
                }
            )

            bug_report = BugReport.from_dict(bug_report_data)

            print(f"[RCA-Agent] Improving analysis based on critique feedback")

            # Re-analyze with improvement context
            improved_analysis = self._reanalyze_with_feedback(
                bug_report, original_analysis, critique_feedback
            )

            return self._create_success_response(
                message,
                {
                    "task": "improve_analysis",
                    "improved_analysis": improved_analysis.to_dict(),
                    "improvements_applied": self._extract_improvements_applied(
                        critique_feedback
                    ),
                    "metadata": {
                        "improvement_iteration": len(self.improvement_feedback),
                        "confidence_change": improved_analysis.confidence_score
                        - original_analysis.get("confidence_score", 0),
                    },
                },
            )

        except Exception as e:
            return self._create_error_response(message, f"Improvement failed: {str(e)}")

    def _handle_get_status(
        self, message: Dict[str, Any], data: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Handle status request."""
        return self._create_success_response(
            message,
            {
                "task": "get_analysis_status",
                "status": {
                    "agent_id": self.agent_id,
                    "state": "ready",
                    "active_analysis": len(self.conversation_history) > 0,
                    "total_improvements": len(self.improvement_feedback),
                    "last_activity": datetime.now().isoformat(),
                    "capabilities": self.capabilities,
                },
            },
        )

    def _analyze_bug_with_improvement(
        self, bug_report: BugReport, max_iterations: int
    ) -> AnalysisResult:
        """Analyze bug with self-improvement context."""
        # Create analysis prompt with improvement context
        initial_prompt = self._create_analysis_prompt_with_context(bug_report)
        self.conversation_history.append(initial_prompt)

        iteration = 0
        analysis_complete = False

        while iteration < max_iterations and not analysis_complete:
            iteration += 1
            print(f"Iteration {iteration}/{max_iterations}")

            # Get LLM response with retry logic
            tools = self._create_adk_tools()
            response = self._call_llm_with_retry(tools)

            # Check if LLM wants to call a function
            if hasattr(response.candidates[0].content.parts[0], "function_call"):
                function_call = response.candidates[0].content.parts[0].function_call

                # Validate function call
                if (
                    not function_call
                    or not hasattr(function_call, "name")
                    or not function_call.name
                ):
                    print("Invalid function call received, treating as final response")
                    analysis_complete = True
                    final_response = (
                        response.text or "Analysis completed without final response"
                    )
                    print("ANALYSIS COMPLETE")
                    print("=" * 80)
                    print(final_response)
                    print("=" * 80)
                    return self._parse_final_analysis(
                        bug_report, final_response, iteration
                    )

                # Execute tool
                print(f"Calling tool: {function_call.name}")
                start_time = datetime.now()
                tool_result = self._execute_tool(
                    function_call.name, dict(function_call.args)
                )
                execution_time = (datetime.now() - start_time).total_seconds()

                print(f"   Completed in {execution_time:.2f}s")

                # Record tool execution
                self.tool_executions.append(
                    ToolExecutionResult(
                        tool_name=function_call.name,
                        parameters=dict(function_call.args),
                        result=str(tool_result)[:1000],
                        execution_time=execution_time,
                        success=True,
                    )
                )

                # Add to conversation history
                self.conversation_history.append(
                    types.Content(
                        role="model", parts=[types.Part(function_call=function_call)]
                    )
                )
                self.conversation_history.append(
                    types.Content(
                        role="user",
                        parts=[
                            types.Part(
                                function_response=types.FunctionResponse(
                                    name=function_call.name,
                                    response={"result": tool_result},
                                )
                            )
                        ],
                    )
                )
            else:
                # LLM provided final analysis
                analysis_complete = True
                final_response = response.text

                print("ANALYSIS COMPLETE")
                print("=" * 80)
                print(final_response)
                print("=" * 80)

                return self._parse_final_analysis(bug_report, final_response, iteration)

        # Max iterations reached
        print("Max iterations reached without completion")
        return self._create_incomplete_result(bug_report, iteration)

    def _reanalyze_with_feedback(
        self,
        bug_report: BugReport,
        original_analysis: Dict[str, Any],
        critique_feedback: Dict[str, Any],
    ) -> AnalysisResult:
        """Re-analyze incorporating critique feedback."""
        # Create improvement-focused prompt
        improvement_prompt = self._create_improvement_prompt(
            bug_report, original_analysis, critique_feedback
        )

        # Reset conversation for improvement
        self.conversation_history = [improvement_prompt]

        # Perform focused re-analysis
        return self._analyze_bug_with_improvement(
            bug_report, config.max_rca_iterations // 2
        )

    def _create_analysis_prompt_with_context(
        self, bug_report: BugReport
    ) -> types.Content:
        """Create analysis prompt with self-improvement context."""
        base_prompt = self._create_base_analysis_prompt(bug_report)

        # Add improvement context if available
        if self.improvement_feedback:
            improvement_context = "\n\nSELF-IMPROVEMENT CONTEXT:\n"
            improvement_context += (
                "Based on previous critique feedback, pay special attention to:\n"
            )

            for feedback in self.improvement_feedback[-3:]:  # Last 3 feedbacks
                critique = feedback["feedback"]
                if not critique.get("approved", True):
                    improvement_context += (
                        f"- {critique.get('comments', 'No specific comments')}\n"
                    )
                    for improvement in critique.get("suggested_improvements", []):
                        improvement_context += f"  * {improvement}\n"

            base_prompt += improvement_context

        return types.Content(role="user", parts=[types.Part(text=base_prompt)])

    def _create_improvement_prompt(
        self,
        bug_report: BugReport,
        original_analysis: Dict[str, Any],
        critique_feedback: Dict[str, Any],
    ) -> types.Content:
        """Create focused improvement prompt."""
        prompt = f"""You are improving a previous root cause analysis based on critique feedback.

ORIGINAL BUG REPORT:
{bug_report.title}
{bug_report.description}

PREVIOUS ANALYSIS SUMMARY:
File: {original_analysis.get('root_cause', {}).get('file_path', 'Unknown')}
Confidence: {original_analysis.get('confidence_score', 0):.2f}
Explanation: {original_analysis.get('root_cause', {}).get('explanation', 'No explanation')}

CRITIQUE FEEDBACK:
Approved: {critique_feedback.get('approved', False)}
Comments: {critique_feedback.get('comments', 'No comments')}
Suggested Improvements:
"""

        for improvement in critique_feedback.get("suggested_improvements", []):
            prompt += f"- {improvement}\n"

        prompt += """
IMPROVEMENT TASK:
Address the critique feedback by:
1. Re-examining the identified issues
2. Investigating alternative explanations mentioned in feedback
3. Providing more thorough analysis where suggested
4. Improving confidence through better evidence

Use the same tools as before but focus on the areas highlighted in the critique.
Provide a refined analysis that addresses the feedback concerns.
"""

        return types.Content(role="user", parts=[types.Part(text=prompt)])

    def _create_base_analysis_prompt(self, bug_report: BugReport) -> str:
        """Create base analysis prompt."""
        prompt = f"""You are an expert software engineer performing root cause analysis.

BUG REPORT:
Title: {bug_report.title}
Description: {bug_report.description}

Steps to Reproduce:
{chr(10).join(f'{i+1}. {step}' for i, step in enumerate(bug_report.steps_to_reproduce))}

Expected: {bug_report.expected_behavior}
Actual: {bug_report.actual_behavior}
"""

        if bug_report.error_message:
            prompt += f"Error: {bug_report.error_message}\n"

        if bug_report.stack_trace:
            prompt += f"Stack Trace:\n{bug_report.stack_trace}\n"

        prompt += """
INVESTIGATION WORKFLOW:
1. Understand project structure (get_repository_structure)
2. Search for relevant code (search_code)
3. Examine suspicious files (get_file_content)
4. Find WHO and WHEN (get_file_blame, get_commit_details)
5. Provide complete analysis with commit/author info

When ready, provide structured analysis:
## Root Cause Analysis
### Summary
[Brief summary]
### Root Cause
File: [path]
Lines: [numbers]
Code: [snippet]
Explanation: [detailed explanation]
### Commit Information
- SHA: [commit]
- Author: [name] ([email])
- Date: [date]
### Confidence Score
[0.0-1.0]

Start investigation now!"""

        return prompt

    def _extract_improvements_applied(
        self, critique_feedback: Dict[str, Any]
    ) -> List[str]:
        """Extract what improvements were applied based on feedback."""
        improvements = []

        if not critique_feedback.get("approved", True):
            improvements.append("Re-analyzed based on critique rejection")

        for suggestion in critique_feedback.get("suggested_improvements", []):
            improvements.append(f"Applied: {suggestion}")

        if critique_feedback.get("confidence_adjustment", 0) != 0:
            improvements.append("Adjusted confidence based on feedback")

        return improvements

    # Include all the helper methods from the original agent
    def _call_llm_with_retry(self, tools, max_retries=None):
        """Call LLM with retry logic for rate limiting."""
        if max_retries is None:
            max_retries = config.max_api_retries

        for attempt in range(max_retries):
            try:
                response = self.client.models.generate_content(
                    model=self.model_id,
                    contents=self.conversation_history,
                    config=types.GenerateContentConfig(tools=tools, temperature=0.1),
                )
                return response
            except Exception as e:
                error_str = str(e)

                if "429" in error_str or "RESOURCE_EXHAUSTED" in error_str:
                    retry_delay = self._extract_retry_delay(error_str)
                    if retry_delay is None:
                        retry_delay = config.retry_base_delay * (
                            2**attempt
                        ) + random.uniform(0, 1)

                    print(
                        f"Rate limit hit. Waiting {retry_delay:.1f}s before retry {attempt + 1}/{max_retries}..."
                    )
                    time.sleep(retry_delay)

                    if attempt == max_retries - 1:
                        raise Exception(
                            f"Max retries ({max_retries}) exceeded. Last error: {error_str}"
                        )
                else:
                    raise e

        return None

    def _extract_retry_delay(self, error_message):
        """Extract retry delay from error message."""
        try:
            match = re.search(r"retry in (\d+\.?\d*)s", error_message)
            if match:
                return float(match.group(1))

            match = re.search(r"'retryDelay': '(\d+)s'", error_message)
            if match:
                return float(match.group(1))

        except:
            pass
        return None

    def _create_adk_tools(self) -> List[types.Tool]:
        """Define GitHub tools for LLM function calling."""
        return [
            types.Tool(
                function_declarations=[
                    types.FunctionDeclaration(
                        name="get_repository_structure",
                        description="Get complete directory structure to understand project layout",
                        parameters={
                            "type": "object",
                            "properties": {
                                "max_depth": {
                                    "type": "integer",
                                    "description": "Maximum depth to traverse",
                                }
                            },
                        },
                    ),
                    types.FunctionDeclaration(
                        name="search_code",
                        description="Search for code using keywords from error messages or stack traces",
                        parameters={
                            "type": "object",
                            "properties": {
                                "query": {
                                    "type": "string",
                                    "description": "Search query",
                                }
                            },
                            "required": ["query"],
                        },
                    ),
                    types.FunctionDeclaration(
                        name="get_file_content",
                        description="Fetch complete content of a specific file",
                        parameters={
                            "type": "object",
                            "properties": {
                                "file_path": {
                                    "type": "string",
                                    "description": "Path to file",
                                }
                            },
                            "required": ["file_path"],
                        },
                    ),
                    types.FunctionDeclaration(
                        name="get_file_blame",
                        description="Get line-by-line authorship info to find WHO wrote problematic code",
                        parameters={
                            "type": "object",
                            "properties": {
                                "file_path": {
                                    "type": "string",
                                    "description": "Path to file",
                                },
                                "line_start": {
                                    "type": "integer",
                                    "description": "Start line (optional)",
                                },
                                "line_end": {
                                    "type": "integer",
                                    "description": "End line (optional)",
                                },
                            },
                            "required": ["file_path"],
                        },
                    ),
                    types.FunctionDeclaration(
                        name="get_commit_details",
                        description="Get comprehensive commit details including diff",
                        parameters={
                            "type": "object",
                            "properties": {
                                "commit_sha": {
                                    "type": "string",
                                    "description": "Commit SHA",
                                }
                            },
                            "required": ["commit_sha"],
                        },
                    ),
                    types.FunctionDeclaration(
                        name="search_in_file",
                        description="Search for specific text within a file",
                        parameters={
                            "type": "object",
                            "properties": {
                                "file_path": {
                                    "type": "string",
                                    "description": "Path to file",
                                },
                                "search_term": {
                                    "type": "string",
                                    "description": "Term to search",
                                },
                            },
                            "required": ["file_path", "search_term"],
                        },
                    ),
                    types.FunctionDeclaration(
                        name="get_file_history",
                        description="Get recent commit history for a file",
                        parameters={
                            "type": "object",
                            "properties": {
                                "file_path": {
                                    "type": "string",
                                    "description": "Path to file",
                                },
                                "limit": {
                                    "type": "integer",
                                    "description": "Number of commits",
                                },
                            },
                            "required": ["file_path"],
                        },
                    ),
                    types.FunctionDeclaration(
                        name="find_when_line_was_added",
                        description="Find exact commit that introduced specific lines",
                        parameters={
                            "type": "object",
                            "properties": {
                                "file_path": {
                                    "type": "string",
                                    "description": "Path to file",
                                },
                                "line_numbers": {
                                    "type": "array",
                                    "items": {"type": "integer"},
                                },
                            },
                            "required": ["file_path", "line_numbers"],
                        },
                    ),
                ]
            )
        ]

    def _execute_tool(self, tool_name: str, parameters: Dict[str, Any]) -> str:
        """Execute GitHub tool."""
        try:
            if tool_name == "get_repository_structure":
                return self.github.get_repository_structure(
                    parameters.get("max_depth", 3)
                )
            elif tool_name == "search_code":
                return self.github.search_code(parameters["query"])
            elif tool_name == "get_file_content":
                return self.github.get_file_content(parameters["file_path"])
            elif tool_name == "get_file_blame":
                return self.github.get_file_blame(
                    parameters["file_path"],
                    parameters.get("line_start"),
                    parameters.get("line_end"),
                )
            elif tool_name == "get_commit_details":
                return self.github.get_commit_details(parameters["commit_sha"])
            elif tool_name == "search_in_file":
                return self.github.search_in_file(
                    parameters["file_path"], parameters["search_term"]
                )
            elif tool_name == "get_file_history":
                return self.github.get_file_history(
                    parameters["file_path"], parameters.get("limit", 10)
                )
            elif tool_name == "find_when_line_was_added":
                return self.github.find_when_line_was_added(
                    parameters["file_path"], parameters["line_numbers"]
                )
            else:
                return json.dumps({"error": f"Unknown tool: {tool_name}"})
        except Exception as e:
            return json.dumps({"error": str(e)})

    def _parse_final_analysis(
        self, bug_report: BugReport, analysis_text: str, iterations: int
    ) -> AnalysisResult:
        """Parse LLM analysis into structured format."""
        return AnalysisResult(
            bug_report_title=bug_report.title,
            root_cause=RootCause(
                file_path="extracted_from_analysis",
                line_numbers=[],
                code_snippet="",
                explanation=analysis_text,
                confidence_score=0.8,
            ),
            commit_info=None,
            author_info=None,
            verification_steps=[],
            suggested_fix=None,
            confidence_score=0.8,
            tools_used=[t.tool_name for t in self.tool_executions],
            iterations=iterations,
            analysis_timestamp=datetime.now(),
            critique_approved=False,
        )

    def _create_incomplete_result(
        self, bug_report: BugReport, iterations: int
    ) -> AnalysisResult:
        """Create result when analysis doesn't complete."""
        return AnalysisResult(
            bug_report_title=bug_report.title,
            root_cause=RootCause(
                file_path="unknown",
                line_numbers=[],
                code_snippet="",
                explanation="Analysis incomplete - max iterations reached",
                confidence_score=0.0,
            ),
            commit_info=None,
            author_info=None,
            verification_steps=[],
            suggested_fix=None,
            confidence_score=0.0,
            tools_used=[t.tool_name for t in self.tool_executions],
            iterations=iterations,
            analysis_timestamp=datetime.now(),
            critique_approved=False,
        )

    def _validate_message(self, message: Dict[str, Any]) -> bool:
        """Validate A2A message format."""
        required_fields = ["message_id", "sender_id", "content"]
        return all(field in message for field in required_fields)

    def _create_success_response(
        self, original_message: Dict[str, Any], result: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Create successful A2A response."""
        return {
            "message_id": f"rca_response_{datetime.now().timestamp()}",
            "sender_id": self.agent_id,
            "recipient_id": original_message.get("sender_id", "orchestrator"),
            "message_type": "task_response",
            "status": "success",
            "content": {"result": result},
            "timestamp": datetime.now().isoformat(),
        }

    def _create_error_response(
        self, original_message: Dict[str, Any], error_message: str
    ) -> Dict[str, Any]:
        """Create error A2A response."""
        return {
            "message_id": f"rca_error_{datetime.now().timestamp()}",
            "sender_id": self.agent_id,
            "recipient_id": original_message.get("sender_id", "orchestrator"),
            "message_type": "task_response",
            "status": "error",
            "content": {"error": error_message},
            "timestamp": datetime.now().isoformat(),
        }
