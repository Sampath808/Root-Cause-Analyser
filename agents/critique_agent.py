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

from models.analysis_result import AnalysisResult
from models.bug_report import BugReport
from core.github_client import GitHubClient
from utils.config import config


class CritiqueAgent:
    """Reviews and validates root cause analysis using OpenAI via ADK Wrapper."""

    def __init__(self, github_client: GitHubClient):
        self.github = github_client

        # Initialize OpenAI client
        api_key = getattr(config, "openai_api_key", None) or os.getenv("OPENAI_API_KEY")
        if not api_key:
            raise ValueError(
                "OpenAI API Key not found. Please set OPENAI_API_KEY environment variable or config."
            )

        self.client = OpenAI(api_key=api_key)

        # Define the Agent using google.adk structure
        # We set the model to gpt-4o, which our adapter will respect
        self.agent = Agent(
            name="critique_analyzer",
            model="gpt-4o",
            instruction=self._get_system_instruction(),
            tools=self._create_github_tools_list(),  # ADK expects list of functions
        )

    def _get_system_instruction(self) -> str:
        return """You are a senior software engineer reviewing a root cause analysis. Your job is to verify and critique the findings.

VERIFICATION TASKS:

1. **Verify File and Lines Exist**
   - Check if the identified file actually exists using get_file_content()
   - Verify the line numbers are correct

2. **Check Logical Consistency**
   - Does the execution trace make sense?
   - Is the root cause explanation logical?
   - Use the same tools to verify claims

3. **Verify Commit Information**
   - If commit/author info was provided, verify it's correct using get_commit_details()
   - Check if the identified commit actually changed the problematic lines

4. **Look for Alternative Explanations**
   - Are there other possible root causes?
   - Did the RCA miss anything obvious?
   - Use search_code() and other tools to investigate

5. **Assess Completeness**
   - Did the RCA check all relevant files?
   - Should additional files be examined?

CRITIQUE RESPONSE FORMAT:

## Critique

### Verification Results
[What you verified and what you found]

### Logical Consistency
[Is the analysis logically sound?]

### Alternative Explanations
[Any other possible causes?]

### Suggested Improvements
[What could be better?]

### Final Verdict
Approved: [YES/NO]
Confidence Adjustment: [+0.1, -0.2, etc.]
Comments: [Summary of issues found or approval]

If you find issues, use the available tools to investigate further and provide specific evidence."""

    def _create_github_tools_list(self) -> List[Callable]:
        """Returns list of callables for ADK Agent constructor"""
        return [
            self.github.get_repository_structure,
            self.github.search_code,
            self.github.get_file_content,
            self.github.get_directory_files,
            self.github.get_file_history,
            self.github.get_file_blame,
            self.github.get_commit_details,
            self.github.find_file_dependencies,
            self.github.search_in_file,
            self.github.find_when_line_was_added,
            self.github.get_recent_commits,
        ]

    def _get_tools_schema(self) -> List[Dict]:
        """Define tools schema specifically for OpenAI API"""
        return [
            {
                "type": "function",
                "function": {
                    "name": "get_repository_structure",
                    "description": "Get the complete directory structure of the repository.",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "max_depth": {
                                "type": "integer",
                                "description": "Maximum depth to traverse (default 3)",
                            }
                        },
                        "required": [],
                    },
                },
            },
            {
                "type": "function",
                "function": {
                    "name": "search_code",
                    "description": "Search for code using keywords.",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "query": {
                                "type": "string",
                                "description": "The search query (e.g., function name, error message)",
                            }
                        },
                        "required": ["query"],
                    },
                },
            },
            {
                "type": "function",
                "function": {
                    "name": "get_file_content",
                    "description": "Fetch the complete content of a specific file.",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "file_path": {
                                "type": "string",
                                "description": "Path to the file",
                            }
                        },
                        "required": ["file_path"],
                    },
                },
            },
            {
                "type": "function",
                "function": {
                    "name": "get_directory_files",
                    "description": "List all files in a specific directory.",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "directory_path": {
                                "type": "string",
                                "description": "Path to the directory",
                            }
                        },
                        "required": ["directory_path"],
                    },
                },
            },
            {
                "type": "function",
                "function": {
                    "name": "get_file_history",
                    "description": "Get recent commit history for a file.",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "file_path": {
                                "type": "string",
                                "description": "Path to the file",
                            },
                            "limit": {
                                "type": "integer",
                                "description": "Number of commits to return",
                            },
                        },
                        "required": ["file_path"],
                    },
                },
            },
            {
                "type": "function",
                "function": {
                    "name": "get_file_blame",
                    "description": "Get line-by-line authorship information (git blame).",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "file_path": {
                                "type": "string",
                                "description": "Path to the file",
                            },
                            "line_start": {
                                "type": "integer",
                                "description": "Start line number",
                            },
                            "line_end": {
                                "type": "integer",
                                "description": "End line number",
                            },
                        },
                        "required": ["file_path"],
                    },
                },
            },
            {
                "type": "function",
                "function": {
                    "name": "get_commit_details",
                    "description": "Get comprehensive details about a specific commit including the diff.",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "commit_sha": {
                                "type": "string",
                                "description": "The commit SHA",
                            }
                        },
                        "required": ["commit_sha"],
                    },
                },
            },
            {
                "type": "function",
                "function": {
                    "name": "find_file_dependencies",
                    "description": "Find what a file imports and what files import it.",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "file_path": {
                                "type": "string",
                                "description": "Path to the file",
                            }
                        },
                        "required": ["file_path"],
                    },
                },
            },
            {
                "type": "function",
                "function": {
                    "name": "search_in_file",
                    "description": "Search for specific text within a file and get matching lines with context.",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "file_path": {
                                "type": "string",
                                "description": "Path to the file",
                            },
                            "search_term": {
                                "type": "string",
                                "description": "Text to search for",
                            },
                        },
                        "required": ["file_path", "search_term"],
                    },
                },
            },
            {
                "type": "function",
                "function": {
                    "name": "find_when_line_was_added",
                    "description": "Find the exact commit that introduced specific lines of code.",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "file_path": {
                                "type": "string",
                                "description": "Path to the file",
                            },
                            "line_numbers": {
                                "type": "array",
                                "items": {"type": "integer"},
                                "description": "List of line numbers",
                            },
                        },
                        "required": ["file_path", "line_numbers"],
                    },
                },
            },
            {
                "type": "function",
                "function": {
                    "name": "get_recent_commits",
                    "description": "Get recent commits to the repository.",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "limit": {
                                "type": "integer",
                                "description": "Limit number of commits",
                            },
                            "since_date": {
                                "type": "string",
                                "description": "ISO date string",
                            },
                        },
                        "required": [],
                    },
                },
            },
        ]

    def _execute_agent_with_openai(self, user_prompt: str) -> str:
        """Adapter method: Executes the ADK Agent using OpenAI"""
        # Use instruction from the ADK Agent object
        system_instruction = self.agent.instruction

        messages = [
            {"role": "system", "content": system_instruction},
            {"role": "user", "content": user_prompt},
        ]

        tools = self._get_tools_schema()
        # Map function names to the callables in the ADK agent's tool list
        available_functions = {func.__name__: func for func in self.agent.tools}

        max_turns = 10
        current_turn = 0

        while current_turn < max_turns:
            current_turn += 1
            try:
                # Use model name from ADK Agent object
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

    def critique(self, bug_report: BugReport, rca_analysis: AnalysisResult) -> Dict:
        """Critique the root cause analysis"""
        print("\n" + "=" * 80)
        print("CRITIQUE ANALYSIS STARTED (ADK via OpenAI)")
        print("=" * 80)

        critique_prompt = f"""Review this root cause analysis for accuracy and completeness:

ORIGINAL BUG REPORT:
Title: {bug_report.title}
Description: {bug_report.description}

RCA AGENT'S ANALYSIS:
{rca_analysis.root_cause.explanation}

File: {rca_analysis.root_cause.file_path}
Lines: {rca_analysis.root_cause.line_numbers}
Confidence: {rca_analysis.confidence_score}

Please verify the analysis using the available tools and provide your critique following the specified format."""

        try:
            # Delegate execution to the adapter method
            response_text = self._execute_agent_with_openai(critique_prompt)

            print("\n" + "=" * 80)
            print("CRITIQUE COMPLETE")
            print("=" * 80)
            print(response_text)
            print("=" * 80)

            return self._parse_critique_response(response_text)

        except Exception as e:
            print(f"Error during critique: {str(e)}")
            return {
                "approved": False,
                "confidence_adjustment": -0.5,
                "comments": f"Critique failed: {str(e)}",
                "suggested_improvements": ["Fix critique agent error"],
            }

    def _parse_critique_response(self, response: str) -> Dict:
        response_lower = response.lower()

        approved = False
        if "approved: yes" in response_lower or "verdict: approved" in response_lower:
            approved = True
        elif (
            "approved: no" in response_lower
            or "verdict: not approved" in response_lower
        ):
            approved = False

        confidence_adjustment = 0.0
        if "confidence adjustment:" in response_lower:
            try:
                parts = response_lower.split("confidence adjustment:")
                if len(parts) > 1:
                    adj_part = parts[1].strip().split()[0]
                    clean_adj = (
                        adj_part.replace("+", "").replace(",", "").replace("]", "")
                    )
                    confidence_adjustment = float(clean_adj)
            except Exception:
                confidence_adjustment = 0.0

        return {
            "approved": approved,
            "confidence_adjustment": confidence_adjustment,
            "comments": response,
            "suggested_improvements": [],
        }
