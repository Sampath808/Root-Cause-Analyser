from google import genai
from google.genai import types
from typing import List, Dict, Any
import json
from datetime import datetime
import sys
import os
import time
import random

# Add parent directory to path for imports
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from models.bug_report import BugReport
from models.analysis_result import AnalysisResult, RootCause, ToolExecutionResult
from core.github_client import GitHubClient
from utils.config import config

class RootCauseAgent:
    """Intelligent agent that investigates bugs using GitHub tools.
    Uses Gemini's function calling to decide which tools to use."""

    def __init__(self, gemini_api_key: str, github_client: GitHubClient):
        """Initialize RCA agent
        
        Args:
            gemini_api_key: Google Gemini API key
            github_client: Initialized GitHub client
        """
        self.client = genai.Client(api_key=gemini_api_key)
        self.model_id = config.gemini_model
        self.github = github_client
        self.conversation_history = []
        self.tool_executions = []

    def _call_llm_with_retry(self, tools, max_retries=None):
        """Call LLM with retry logic for rate limiting."""
        if max_retries is None:
            max_retries = config.max_api_retries
            
        for attempt in range(max_retries):
            try:
                response = self.client.models.generate_content(
                    model=self.model_id,
                    contents=self.conversation_history,
                    config=types.GenerateContentConfig(
                        tools=tools,
                        temperature=0.1
                    )
                )
                return response
            except Exception as e:
                error_str = str(e)
                
                # Check if it's a rate limit error
                if "429" in error_str or "RESOURCE_EXHAUSTED" in error_str:
                    # Extract retry delay from error message if available
                    retry_delay = self._extract_retry_delay(error_str)
                    if retry_delay is None:
                        # Use exponential backoff if no delay specified
                        retry_delay = config.retry_base_delay * (2 ** attempt) + random.uniform(0, 1)
                    
                    print(f"Rate limit hit. Waiting {retry_delay:.1f}s before retry {attempt + 1}/{max_retries}...")
                    time.sleep(retry_delay)
                    
                    if attempt == max_retries - 1:
                        raise Exception(f"Max retries ({max_retries}) exceeded. Last error: {error_str}")
                else:
                    # Non-rate-limit error, don't retry
                    raise e
        
        return None

    def _extract_retry_delay(self, error_message):
        """Extract retry delay from error message."""
        try:
            # Look for patterns like "Please retry in 6.093737172s"
            import re
            match = re.search(r'retry in (\d+\.?\d*)s', error_message)
            if match:
                return float(match.group(1))
            
            # Look for patterns like "'retryDelay': '6s'"
            match = re.search(r"'retryDelay': '(\d+)s'", error_message)
            if match:
                return float(match.group(1))
                
        except:
            pass
        return None

    def _create_adk_tools(self) -> List[types.Tool]:
        """Define all GitHub tools available to the agent using ADK format.
        These will be exposed to Gemini for function calling."""
        return [
            types.Tool(
                function_declarations=[
                    types.FunctionDeclaration(
                        name="get_repository_structure",
                        description='''Get the complete directory structure of the repository. Use this FIRST to understand the project layout and identify relevant directories.
This helps you understand where authentication, database, API, and other components are located.''',
                        parameters={
                            "type": "object",
                            "properties": {
                                "max_depth": {
                                    "type": "integer",
                                    "description": "Maximum depth to traverse (default: 3, recommended for initial overview)"
                                }
                            }
                        }
                    ),
                    types.FunctionDeclaration(
                        name="search_code",
                        description='''Search for code using keywords. Use keywords from error messages, stack traces, function names, or class names.
This is very effective for finding files related to specific errors or features.''',
                        parameters={
                            "type": "object",
                            "properties": {
                                "query": {
                                    "type": "string",
                                    "description": "Search query (e.g., \"login\", \"AuthenticationError\", \"validate_token\")"
                                }
                            },
                            "required": ["query"]
                        }
                    ),
                    types.FunctionDeclaration(
                        name="get_file_content",
                        description='''Fetch the complete content of a specific file.
Use this after identifying potentially relevant files from search or directory listing.''',
                        parameters={
                            "type": "object",
                            "properties": {
                                "file_path": {
                                    "type": "string",
                                    "description": "Path to the file (e.g., \"src/auth/login.py\")"
                                }
                            },
                            "required": ["file_path"]
                        }
                    ),
                    types.FunctionDeclaration(
                        name="get_directory_files",
                        description='''List all files in a specific directory.
Use this to explore a directory you identified as potentially relevant.''',
                        parameters={
                            "type": "object",
                            "properties": {
                                "directory_path": {
                                    "type": "string",
                                    "description": "Path to directory (e.g., \"src/auth\")"
                                }
                            },
                            "required": ["directory_path"]
                        }
                    ),
                    types.FunctionDeclaration(
                        name="get_file_history",
                        description='''Get recent commit history for a file.
Use this to see what changed recently in a suspicious file.''',
                        parameters={
                            "type": "object",
                            "properties": {
                                "file_path": {
                                    "type": "string",
                                    "description": "Path to file"
                                },
                                "limit": {
                                    "type": "integer",
                                    "description": "Number of commits (default: 10)"
                                }
                            },
                            "required": ["file_path"]
                        }
                    ),
                    types.FunctionDeclaration(
                        name="get_file_blame",
                        description='''Get line-by-line authorship information (git blame).
Use this AFTER identifying the problematic lines to find WHO wrote them and WHEN.
You can optionally specify line range to focus on specific lines.''',
                        parameters={
                            "type": "object",
                            "properties": {
                                "file_path": {
                                    "type": "string",
                                    "description": "Path to file"
                                },
                                "line_start": {
                                    "type": "integer",
                                    "description": "Start line number (optional)"
                                },
                                "line_end": {
                                    "type": "integer",
                                    "description": "End line number (optional)"
                                }
                            },
                            "required": ["file_path"]
                        }
                    ),
                    types.FunctionDeclaration(
                        name="get_commit_details",
                        description='''Get comprehensive details about a specific commit including the diff.
Use this after finding a suspicious commit from blame or history to see exactly what changed.''',
                        parameters={
                            "type": "object",
                            "properties": {
                                "commit_sha": {
                                    "type": "string",
                                    "description": "Commit SHA hash (can be short form like \"a3f5b2c\")"
                                }
                            },
                            "required": ["commit_sha"]
                        }
                    ),
                    types.FunctionDeclaration(
                        name="find_file_dependencies",
                        description='''Find what a file imports and what files import it.
Use this to trace the execution flow and find related files.''',
                        parameters={
                            "type": "object",
                            "properties": {
                                "file_path": {
                                    "type": "string",
                                    "description": "Path to file"
                                }
                            },
                            "required": ["file_path"]
                        }
                    ),
                    types.FunctionDeclaration(
                        name="search_in_file",
                        description='''Search for specific text within a file and get matching lines with context.
Use this to find specific functions, variables, or error messages within a file.''',
                        parameters={
                            "type": "object",
                            "properties": {
                                "file_path": {
                                    "type": "string",
                                    "description": "Path to file"
                                },
                                "search_term": {
                                    "type": "string",
                                    "description": "Term to search for"
                                }
                            },
                            "required": ["file_path", "search_term"]
                        }
                    ),
                    types.FunctionDeclaration(
                        name="find_when_line_was_added",
                        description='''Find the exact commit that introduced specific lines of code.
Use this AFTER identifying problematic line numbers to find the commit that added them.''',
                        parameters={
                            "type": "object",
                            "properties": {
                                "file_path": {
                                    "type": "string",
                                    "description": "Path to file"
                                },
                                "line_numbers": {
                                    "type": "array",
                                    "items": {"type": "integer"},
                                    "description": "List of line numbers to investigate"
                                }
                            },
                            "required": ["file_path", "line_numbers"]
                        }
                    ),
                    types.FunctionDeclaration(
                        name="get_recent_commits",
                        description='''Get recent commits to the repository.
Use this to see what changed recently, especially useful for regression bugs.''',
                        parameters={
                            "type": "object",
                            "properties": {
                                "limit": {
                                    "type": "integer",
                                    "description": "Number of commits (default: 20)"
                                },
                                "since_date": {
                                    "type": "string",
                                    "description": "ISO date string (e.g., \"2024-01-01\")"
                                }
                            }
                        }
                    )
                ]
            )
        ]
    def analyze_bug(self, bug_report: BugReport, max_iterations: int = 15) -> AnalysisResult:
        """Main analysis workflow.
        
        Args:
            bug_report: Structured bug report
            max_iterations: Maximum tool-calling iterations (prevent infinite loops)
            
        Returns:
            Complete analysis result
        """
        print("\n" + "="*80)
        print("ROOT CAUSE ANALYSIS STARTED")
        print("="*80)
        print(f"Bug: {bug_report.title}")
        print(f"Max iterations: {max_iterations}\n")

        # Clear state
        self.conversation_history = []
        self.tool_executions = []

        # Create initial analysis prompt
        initial_prompt = self._create_analysis_prompt(bug_report)
        self.conversation_history.append(initial_prompt)

        iteration = 0
        analysis_complete = False

        while iteration < max_iterations and not analysis_complete:
            iteration += 1
            print(f"\nIteration {iteration}/{max_iterations}")

            # Get LLM response with function calling and retry logic
            tools = self._create_adk_tools()
            response = self._call_llm_with_retry(tools)

            # Check if LLM wants to call a function
            if hasattr(response.candidates[0].content.parts[0], 'function_call'):
                function_call = response.candidates[0].content.parts[0].function_call

                # Execute the tool
                print(f"Calling tool: {function_call.name}")
                print(f"   Parameters: {dict(function_call.args)}")
                
                start_time = datetime.now()
                tool_result = self._execute_tool(function_call.name, dict(function_call.args))
                execution_time = (datetime.now() - start_time).total_seconds()
                
                print(f"   Completed in {execution_time:.2f}s")
                print(f"   Result size: {len(str(tool_result))} chars")

                # Record tool execution
                self.tool_executions.append(ToolExecutionResult(
                    tool_name=function_call.name,
                    parameters=dict(function_call.args),
                    result=str(tool_result)[:1000],  # Truncate for storage
                    execution_time=execution_time,
                    success=True
                ))

                # Add to conversation history
                self.conversation_history.append(
                    types.Content(
                        role="model",
                        parts=[types.Part(function_call=function_call)]
                    )
                )
                self.conversation_history.append(
                    types.Content(
                        role="user",
                        parts=[types.Part(
                            function_response=types.FunctionResponse(
                                name=function_call.name,
                                response={"result": tool_result}
                            )
                        )]
                    )
                )
            else:
                # LLM has provided final analysis
                analysis_complete = True
                final_response = response.text
                
                print("\n" + "="*80)
                print("ANALYSIS COMPLETE")
                print("="*80)
                print(final_response)
                print("="*80)

                # Parse the final response into structured result
                return self._parse_final_analysis(bug_report, final_response, iteration)

        # Max iterations reached
        print("\nMax iterations reached without completion")
        return self._create_incomplete_result(bug_report, iteration)

    def _create_analysis_prompt(self, bug_report: BugReport) -> types.Content:
        """Create the initial analysis prompt"""
        prompt = f"""You are an expert software engineer performing root cause analysis on a bug.

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

        prompt += """
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
[0.0-1.0]

Start your investigation now!"""

        return types.Content(
            role="user",
            parts=[types.Part(text=prompt)]
        )

    def _execute_tool(self, tool_name: str, parameters: Dict[str, Any]) -> str:
        """Execute a GitHub tool"""
        try:
            if tool_name == 'get_repository_structure':
                return self.github.get_repository_structure(
                    max_depth=parameters.get('max_depth', 3)
                )
            elif tool_name == 'search_code':
                return self.github.search_code(parameters['query'])
            elif tool_name == 'get_file_content':
                return self.github.get_file_content(parameters['file_path'])
            elif tool_name == 'get_directory_files':
                return self.github.get_directory_files(parameters['directory_path'])
            elif tool_name == 'get_file_history':
                return self.github.get_file_history(
                    parameters['file_path'],
                    limit=parameters.get('limit', 10)
                )
            elif tool_name == 'get_file_blame':
                return self.github.get_file_blame(
                    parameters['file_path'],
                    line_start=parameters.get('line_start'),
                    line_end=parameters.get('line_end')
                )
            elif tool_name == 'get_commit_details':
                return self.github.get_commit_details(parameters['commit_sha'])
            elif tool_name == 'find_file_dependencies':
                return self.github.find_file_dependencies(parameters['file_path'])
            elif tool_name == 'search_in_file':
                return self.github.search_in_file(
                    parameters['file_path'],
                    parameters['search_term']
                )
            elif tool_name == 'find_when_line_was_added':
                return self.github.find_when_line_was_added(
                    parameters['file_path'],
                    parameters['line_numbers']
                )
            elif tool_name == 'get_recent_commits':
                return self.github.get_recent_commits(
                    limit=parameters.get('limit', 20),
                    since_date=parameters.get('since_date')
                )
            else:
                return json.dumps({'error': f'Unknown tool: {tool_name}'})
        except Exception as e:
            return json.dumps({'error': str(e)})

    def _parse_final_analysis(self, bug_report: BugReport, analysis_text: str, iterations: int) -> AnalysisResult:
        """Parse the LLM's final analysis into structured format.
        This is a simplified version - you may want to use more robust parsing."""
        
        # TODO: Implement robust parsing of the analysis text
        # For now, return a basic structure
        return AnalysisResult(
            bug_report_title=bug_report.title,
            root_cause=RootCause(
                file_path="extracted_from_analysis",
                line_numbers=[],
                code_snippet="",
                explanation=analysis_text,
                confidence_score=0.8
            ),
            commit_info=None,  # Extract from analysis
            author_info=None,  # Extract from analysis
            verification_steps=[],
            suggested_fix=None,
            confidence_score=0.8,
            tools_used=[t.tool_name for t in self.tool_executions],
            iterations=iterations,
            analysis_timestamp=datetime.now(),
            critique_approved=False
        )

    def _create_incomplete_result(self, bug_report: BugReport, iterations: int) -> AnalysisResult:
        """Create result when analysis doesn't complete"""
        return AnalysisResult(
            bug_report_title=bug_report.title,
            root_cause=RootCause(
                file_path="unknown",
                line_numbers=[],
                code_snippet="",
                explanation="Analysis incomplete - max iterations reached",
                confidence_score=0.0
            ),
            commit_info=None,
            author_info=None,
            verification_steps=[],
            suggested_fix=None,
            confidence_score=0.0,
            tools_used=[t.tool_name for t in self.tool_executions],
            iterations=iterations,
            analysis_timestamp=datetime.now(),
            critique_approved=False
        )