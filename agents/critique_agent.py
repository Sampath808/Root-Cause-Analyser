"""Pure A2A-compatible Critique Agent for analysis validation."""

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

from models.analysis_result import AnalysisResult
from models.bug_report import BugReport
from core.github_client import GitHubClient
from utils.config import config


class CritiqueAgent:
    """Pure A2A-compatible Critique Agent for analysis validation."""

    def __init__(self, gemini_api_key: str, github_client: GitHubClient):
        """Initialize Critique Agent for A2A orchestration.

        Args:
            gemini_api_key: Google Gemini API key
            github_client: Initialized GitHub client
        """
        self.agent_id = "critique_agent"
        self.agent_type = "analysis_validator"
        self.capabilities = [
            "analysis_review",
            "result_validation",
            "confidence_assessment",
            "improvement_suggestions",
            "evidence_verification",
        ]

        # Initialize LLM client
        self.client = genai.Client(api_key=gemini_api_key)
        self.model_id = config.gemini_model
        self.github = github_client

    def get_agent_info(self) -> Dict[str, Any]:
        """Return agent information for A2A orchestrator."""
        return {
            "agent_id": self.agent_id,
            "agent_type": self.agent_type,
            "capabilities": self.capabilities,
            "supported_tasks": [
                "critique_analysis",
                "validate_evidence",
                "suggest_improvements",
            ],
            "input_formats": ["analysis_result", "bug_report"],
            "output_formats": ["critique_result", "validation_report"],
            "description": "Reviews and validates root cause analysis results with improvement suggestions",
            "version": "2.0.0",
        }

    def process(self, message: Dict[str, Any]) -> Dict[str, Any]:
        """Process A2A message and return structured response.

        Args:
            message: A2A message with task request

        Returns:
            A2A response message with critique results
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
            if task == "critique_analysis":
                return self._handle_critique_analysis(message, data)
            elif task == "validate_evidence":
                return self._handle_validate_evidence(message, data)
            elif task == "suggest_improvements":
                return self._handle_suggest_improvements(message, data)
            else:
                return self._create_error_response(
                    message,
                    f"Unsupported task: {task}. Supported: critique_analysis, validate_evidence, suggest_improvements",
                )

        except Exception as e:
            return self._create_error_response(message, f"Processing error: {str(e)}")

    def _handle_critique_analysis(
        self, message: Dict[str, Any], data: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Handle analysis critique task."""
        try:
            # Extract required data
            bug_report_data = data.get("bug_report")
            analysis_data = data.get("analysis_result")

            if not bug_report_data or not analysis_data:
                return self._create_error_response(
                    message, "Missing required data: bug_report and analysis_result"
                )

            bug_report = BugReport.from_dict(bug_report_data)

            print(f"[Critique-Agent] Reviewing analysis for: {bug_report.title}")

            # Perform comprehensive critique
            critique_result = self._perform_comprehensive_critique(
                bug_report, analysis_data
            )

            return self._create_success_response(
                message,
                {
                    "task": "critique_analysis",
                    "critique": critique_result,
                    "metadata": {
                        "critique_timestamp": datetime.now().isoformat(),
                        "analysis_approved": critique_result.get("approved", False),
                        "confidence_adjustment": critique_result.get(
                            "confidence_adjustment", 0.0
                        ),
                        "improvement_suggestions_count": len(
                            critique_result.get("suggested_improvements", [])
                        ),
                    },
                },
            )

        except Exception as e:
            return self._create_error_response(message, f"Critique failed: {str(e)}")

    def _handle_validate_evidence(
        self, message: Dict[str, Any], data: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Handle evidence validation task."""
        try:
            analysis_data = data.get("analysis_result")
            if not analysis_data:
                return self._create_error_response(message, "Missing analysis_result")

            print("[Critique-Agent] Validating evidence...")

            validation_result = self._validate_analysis_evidence(analysis_data)

            return self._create_success_response(
                message,
                {
                    "task": "validate_evidence",
                    "validation": validation_result,
                    "metadata": {
                        "validation_timestamp": datetime.now().isoformat(),
                        "evidence_score": validation_result.get("evidence_score", 0.0),
                    },
                },
            )

        except Exception as e:
            return self._create_error_response(message, f"Validation failed: {str(e)}")

    def _handle_suggest_improvements(
        self, message: Dict[str, Any], data: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Handle improvement suggestions task."""
        try:
            bug_report_data = data.get("bug_report")
            analysis_data = data.get("analysis_result")

            if not bug_report_data or not analysis_data:
                return self._create_error_response(
                    message, "Missing required data: bug_report and analysis_result"
                )

            bug_report = BugReport.from_dict(bug_report_data)

            print("[Critique-Agent] Generating improvement suggestions...")

            suggestions = self._generate_improvement_suggestions(
                bug_report, analysis_data
            )

            return self._create_success_response(
                message,
                {
                    "task": "suggest_improvements",
                    "suggestions": suggestions,
                    "metadata": {
                        "suggestion_count": len(suggestions),
                        "priority_suggestions": [
                            s for s in suggestions if s.get("priority") == "high"
                        ],
                    },
                },
            )

        except Exception as e:
            return self._create_error_response(
                message, f"Suggestion generation failed: {str(e)}"
            )

    def _perform_comprehensive_critique(
        self, bug_report: BugReport, analysis_data: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Perform comprehensive critique of analysis."""
        critique_prompt = self._create_critique_prompt(bug_report, analysis_data)

        # Call LLM for critique
        response = self._call_llm_with_retry(
            [types.Content(role="user", parts=[types.Part(text=critique_prompt)])]
        )

        # Parse critique response
        critique_text = response.text

        # Extract structured critique (simplified - could be enhanced with better parsing)
        critique_result = self._parse_critique_response(critique_text, analysis_data)

        return critique_result

    def _validate_analysis_evidence(
        self, analysis_data: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Validate the evidence provided in analysis."""
        validation_prompt = f"""You are validating the evidence quality in a root cause analysis.

ANALYSIS TO VALIDATE:
{json.dumps(analysis_data, indent=2)}

VALIDATION CRITERIA:
1. File paths - Are they realistic and specific?
2. Line numbers - Are they provided and reasonable?
3. Code snippets - Are they included and relevant?
4. Commit information - Is author/SHA/date provided?
5. Explanation quality - Is it detailed and logical?

Provide validation score (0.0-1.0) and specific feedback on evidence quality.
Focus on what evidence is missing or could be stronger.

Format your response as:
EVIDENCE SCORE: [0.0-1.0]
VALIDATION DETAILS:
- [Specific validation point]
- [Another validation point]
MISSING EVIDENCE:
- [What's missing]
- [What could be improved]
"""

        response = self._call_llm_with_retry(
            [types.Content(role="user", parts=[types.Part(text=validation_prompt)])]
        )

        return self._parse_validation_response(response.text)

    def _generate_improvement_suggestions(
        self, bug_report: BugReport, analysis_data: Dict[str, Any]
    ) -> List[Dict[str, Any]]:
        """Generate specific improvement suggestions."""
        suggestion_prompt = f"""Generate specific, actionable improvement suggestions for this root cause analysis.

BUG REPORT:
{bug_report.title}
{bug_report.description}

CURRENT ANALYSIS:
{json.dumps(analysis_data, indent=2)}

Generate 3-5 specific improvement suggestions that would make this analysis stronger.
Each suggestion should be:
1. Actionable (specific steps to take)
2. Prioritized (high/medium/low)
3. Focused (one clear improvement per suggestion)

Format as:
SUGGESTION 1:
Priority: [high/medium/low]
Action: [Specific action to take]
Reason: [Why this would improve the analysis]

SUGGESTION 2:
...
"""

        response = self._call_llm_with_retry(
            [types.Content(role="user", parts=[types.Part(text=suggestion_prompt)])]
        )

        return self._parse_suggestions_response(response.text)

    def _create_critique_prompt(
        self, bug_report: BugReport, analysis_data: Dict[str, Any]
    ) -> str:
        """Create comprehensive critique prompt."""
        return f"""You are an expert code reviewer critiquing a root cause analysis.

ORIGINAL BUG REPORT:
Title: {bug_report.title}
Description: {bug_report.description}
Expected: {bug_report.expected_behavior}
Actual: {bug_report.actual_behavior}
Error: {bug_report.error_message or 'None'}

ANALYSIS TO CRITIQUE:
{json.dumps(analysis_data, indent=2)}

CRITIQUE CHECKLIST:
1. **Accuracy**: Is the identified root cause plausible?
2. **Completeness**: Are all necessary details provided?
3. **Evidence**: Is there sufficient evidence (file paths, line numbers, commits)?
4. **Logic**: Does the explanation make logical sense?
5. **Alternatives**: Could there be other explanations?

PROVIDE STRUCTURED CRITIQUE:
APPROVED: [YES/NO]
CONFIDENCE_ADJUSTMENT: [+0.2, -0.1, etc.]
MAIN_CONCERNS:
- [Primary concern if any]
- [Secondary concern if any]
SUGGESTED_IMPROVEMENTS:
- [Specific improvement 1]
- [Specific improvement 2]
ALTERNATIVE_EXPLANATIONS:
- [Alternative possibility 1]
- [Alternative possibility 2]

Be thorough but constructive. Focus on making the analysis stronger."""

    def _parse_critique_response(
        self, critique_text: str, analysis_data: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Parse critique response into structured format."""
        # Simplified parsing - could be enhanced with better NLP
        approved = (
            "YES" in critique_text.upper() and "APPROVED:" in critique_text.upper()
        )

        # Extract confidence adjustment
        confidence_adjustment = 0.0
        try:
            import re

            match = re.search(
                r"CONFIDENCE_ADJUSTMENT:\s*([-+]?\d*\.?\d+)", critique_text
            )
            if match:
                confidence_adjustment = float(match.group(1))
        except:
            pass

        # Extract concerns and improvements (simplified)
        concerns = []
        improvements = []

        lines = critique_text.split("\n")
        in_concerns = False
        in_improvements = False

        for line in lines:
            line = line.strip()
            if "MAIN_CONCERNS:" in line:
                in_concerns = True
                in_improvements = False
            elif "SUGGESTED_IMPROVEMENTS:" in line:
                in_concerns = False
                in_improvements = True
            elif line.startswith("- "):
                if in_concerns:
                    concerns.append(line[2:])
                elif in_improvements:
                    improvements.append(line[2:])

        return {
            "approved": approved,
            "confidence_adjustment": confidence_adjustment,
            "comments": critique_text,
            "main_concerns": concerns,
            "suggested_improvements": improvements,
            "original_confidence": analysis_data.get("confidence_score", 0.0),
            "adjusted_confidence": min(
                1.0,
                max(
                    0.0,
                    analysis_data.get("confidence_score", 0.0) + confidence_adjustment,
                ),
            ),
        }

    def _parse_validation_response(self, validation_text: str) -> Dict[str, Any]:
        """Parse validation response."""
        evidence_score = 0.5  # Default

        try:
            import re

            match = re.search(r"EVIDENCE SCORE:\s*(\d*\.?\d+)", validation_text)
            if match:
                evidence_score = float(match.group(1))
        except:
            pass

        return {
            "evidence_score": evidence_score,
            "validation_details": validation_text,
            "timestamp": datetime.now().isoformat(),
        }

    def _parse_suggestions_response(
        self, suggestions_text: str
    ) -> List[Dict[str, Any]]:
        """Parse improvement suggestions."""
        suggestions = []

        # Simple parsing - could be enhanced
        lines = suggestions_text.split("\n")
        current_suggestion = {}

        for line in lines:
            line = line.strip()
            if line.startswith("SUGGESTION"):
                if current_suggestion:
                    suggestions.append(current_suggestion)
                current_suggestion = {}
            elif line.startswith("Priority:"):
                current_suggestion["priority"] = line.split(":", 1)[1].strip()
            elif line.startswith("Action:"):
                current_suggestion["action"] = line.split(":", 1)[1].strip()
            elif line.startswith("Reason:"):
                current_suggestion["reason"] = line.split(":", 1)[1].strip()

        if current_suggestion:
            suggestions.append(current_suggestion)

        return suggestions

    def _call_llm_with_retry(self, contents, max_retries=None):
        """Call LLM with retry logic for rate limiting."""
        if max_retries is None:
            max_retries = config.max_api_retries

        for attempt in range(max_retries):
            try:
                response = self.client.models.generate_content(
                    model=self.model_id,
                    contents=contents,
                    config=types.GenerateContentConfig(temperature=0.1),
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
                        f"Rate limit hit in critique. Waiting {retry_delay:.1f}s before retry {attempt + 1}/{max_retries}..."
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

    def _validate_message(self, message: Dict[str, Any]) -> bool:
        """Validate A2A message format."""
        required_fields = ["message_id", "sender_id", "content"]
        return all(field in message for field in required_fields)

    def _create_success_response(
        self, original_message: Dict[str, Any], result: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Create successful A2A response."""
        return {
            "message_id": f"critique_response_{datetime.now().timestamp()}",
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
            "message_id": f"critique_error_{datetime.now().timestamp()}",
            "sender_id": self.agent_id,
            "recipient_id": original_message.get("sender_id", "orchestrator"),
            "message_type": "task_response",
            "status": "error",
            "content": {"error": error_message},
            "timestamp": datetime.now().isoformat(),
        }
