from google.adk import Agent
from typing import List, Dict, Any, Callable
import json
from datetime import datetime
import sys
import os
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
from models.analysis_result import AnalysisResult, RootCause
from core.github_client import GitHubClient
from utils.config import config


class RootCauseAgent:
    """Intelligent agent that investigates bugs using GitHub tools.
    Uses OpenAI GPT models via ADK Wrapper."""

    def __init__(self, github_client: GitHubClient):
        """Initialize RCA agent"""
        self.github = github_client
        self.tool_executions = []

        # Initialize OpenAI client
        api_key = getattr(config, "openai_api_key", None) or os.getenv("OPENAI_API_KEY")
        if not api_key:
            raise ValueError(
                "OpenAI API Key not found. Please set OPENAI_API_KEY environment variable or config."
            )

        self.client = OpenAI(api_key=api_key)

        # Define ADK Agent
        self.agent = Agent(
            name="root_cause_analyzer",
            model="gpt-4o",
            instruction=self._get_system_instruction(),
            tools=self._create_github_tools_list(),
        )

    def _get_system_instruction(self) -> str:
        """Get the system instruction for the RCA agent"""
        return """You are an expert software engineer performing root cause analysis on bugs.

YOUR INVESTIGATION WORKFLOW:

1. **Understand the Project Structure**
   - Call get_repository_structure() to understand the codebase organization
   - Identify directories likely related to this bug (auth, api, models, etc.)

2. **Initial Search**
   - If there's a stack trace, extract file names from it
   - Search for error messages or keywords using search_code()
   - List files in relevant directories using get_directory_files()

3. **Examine Suspicious Files**
   - Get content of files that seem related using get_file_content()
   - Search within files for specific functions/errors using search_in_file()
   - Check file dependencies using find_file_dependencies()

4. **Identify Root Cause**
   - Analyze the code to understand what's causing the issue
   - Trace the execution flow through multiple files if needed
   - Identify the EXACT lines of code causing the problem

5. **Find WHO and WHEN** (CRITICAL - DON'T SKIP THIS)
   - Once you identify problematic lines, use get_file_blame() to see who wrote them
   - Use find_when_line_was_added() for the exact commit
   - Use get_commit_details() to see the full context of the change

6. **Prepare Final Report**
   - Provide a clear explanation of the root cause
   - Include file path and exact line numbers
   - Include the commit SHA and author information
   - Suggest a fix
   - List verification steps

IMPORTANT GUIDELINES:
- Be systematic and thorough
- Don't make assumptions - verify by reading actual code
- When you identify problematic code, ALWAYS find the commit and author
- Use tools efficiently - don't fetch the same information twice
- Provide specific line numbers, not vague descriptions
- Your final response should be structured and detailed

When you're ready with your complete analysis including commit and author information, provide it in this format:

## Root Cause Analysis

### Summary
[Brief 2-3 sentence summary]

### Root Cause
File: [file path]
Lines: [line numbers]
Code:
```
[code snippet]
```
Explanation: [Detailed explanation of why this code causes the bug]

### Execution Trace
1. [Step 1]
2. [Step 2]
...

### Commit Information
- Commit SHA: [sha]
- Author: [name] ([email])
- Date: [date]
- Message: [commit message]
- URL: [commit url]

### Suggested Fix
[Proposed solution]

### Verification Steps
1. [Step 1]
2. [Step 2]

### Confidence Score
[0.0-1.0]"""

    def _create_github_tools_list(self) -> List[Callable]:
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
        """Define tools schema for OpenAI"""
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
                            self.tool_executions.append(
                                f"{function_name}({function_args})"
                            )
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

        return "Error: Maximum conversation turns reached without final answer."

    def analyze_bug(self, bug_report: BugReport) -> AnalysisResult:
        """Main analysis workflow."""
        print("\n" + "=" * 80)
        print("ROOT CAUSE ANALYSIS STARTED (ADK via OpenAI)")
        print("=" * 80)
        print(f"Bug: {bug_report.title}")

        self.tool_executions = []

        analysis_prompt = self._create_analysis_prompt(bug_report)

        print("\nRunning Agent analysis...")
        start_time = datetime.now()

        try:
            response_text = self._execute_agent_with_openai(analysis_prompt)

            execution_time = (datetime.now() - start_time).total_seconds()

            print(f"\nAnalysis completed in {execution_time:.2f}s")
            print("\n" + "=" * 80)
            print("ANALYSIS COMPLETE")
            print("=" * 80)
            print(response_text)
            print("=" * 80)

            return self._parse_final_analysis(bug_report, response_text)

        except Exception as e:
            print(f"Error during analysis: {str(e)}")
            import traceback

            traceback.print_exc()
            return self._create_error_result(bug_report, str(e))

    def _create_analysis_prompt(self, bug_report: BugReport) -> str:
        prompt = f"""Analyze this bug report and find the root cause:

BUG REPORT:
Title: {bug_report.title}
Description: {bug_report.description}

Steps to Reproduce:
{chr(10).join(f'{i+1}. {step}' for i, step in enumerate(bug_report.steps_to_reproduce))}

Expected Behavior: {bug_report.expected_behavior}
Actual Behavior: {bug_report.actual_behavior}
"""
        if bug_report.error_message:
            prompt += f"Error Message: {bug_report.error_message}\n"

        if bug_report.stack_trace:
            prompt += f"\nStack Trace:\n{bug_report.stack_trace}\n"

        if bug_report.environment:
            prompt += f"\nEnvironment: {json.dumps(bug_report.environment, indent=2)}\n"

        prompt += "\nStart your investigation now and provide a complete analysis following the format specified in your instructions."
        return prompt

    def _parse_final_analysis(
        self, bug_report: BugReport, analysis_text: str
    ) -> AnalysisResult:
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
            tools_used=list(set([t.split("(")[0] for t in self.tool_executions])),
            iterations=1,
            analysis_timestamp=datetime.now(),
            critique_approved=False,
        )

    def _create_error_result(
        self, bug_report: BugReport, error_message: str
    ) -> AnalysisResult:
        return AnalysisResult(
            bug_report_title=bug_report.title,
            root_cause=RootCause(
                file_path="unknown",
                line_numbers=[],
                code_snippet="",
                explanation=f"Analysis failed: {error_message}",
                confidence_score=0.0,
            ),
            commit_info=None,
            author_info=None,
            verification_steps=[],
            suggested_fix=None,
            confidence_score=0.0,
            tools_used=[],
            iterations=0,
            analysis_timestamp=datetime.now(),
            critique_approved=False,
        )
