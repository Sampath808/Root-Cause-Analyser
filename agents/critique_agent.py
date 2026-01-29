from google import genai
from google.genai import types
from typing import Dict
import sys
import os
import time
import random
import re

# Add parent directory to path for imports
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from models.analysis_result import AnalysisResult
from models.bug_report import BugReport
from core.github_client import GitHubClient
from utils.config import config

class CritiqueAgent:
    """Reviews and validates root cause analysis.
    Uses same tools to verify claims."""

    def __init__(self, gemini_api_key: str, github_client: GitHubClient):
        self.client = genai.Client(api_key=gemini_api_key)
        self.model_id = config.gemini_model
        self.github = github_client

    def _call_llm_with_retry(self, contents, max_retries=None):
        """Call LLM with retry logic for rate limiting."""
        if max_retries is None:
            max_retries = config.max_api_retries
            
        for attempt in range(max_retries):
            try:
                response = self.client.models.generate_content(
                    model=self.model_id,
                    contents=contents,
                    config=types.GenerateContentConfig(temperature=0.1)
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
                    
                    print(f"Rate limit hit in critique. Waiting {retry_delay:.1f}s before retry {attempt + 1}/{max_retries}...")
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

    def critique(self, bug_report: BugReport, rca_analysis: AnalysisResult) -> Dict:
        """Critique the root cause analysis
        
        Returns:
            Dictionary with:
            - approved: bool
            - confidence_adjustment: float
            - comments: str
            - suggested_improvements: List[str]
        """
        critique_prompt = f"""You are reviewing a root cause analysis. Your job is to verify and critique the findings.

ORIGINAL BUG REPORT:
{bug_report.title}
{bug_report.description}

RCA AGENT'S ANALYSIS:
{rca_analysis.root_cause.explanation}

File: {rca_analysis.root_cause.file_path}
Lines: {rca_analysis.root_cause.line_numbers}
Confidence: {rca_analysis.confidence_score}

VERIFICATION TASKS:

1. **Verify File and Lines Exist**
   - Check if the identified file actually exists
   - Verify the line numbers are correct

2. **Check Logical Consistency**
   - Does the execution trace make sense?
   - Is the root cause explanation logical?

3. **Verify Commit Information**
   - If commit/author info was provided, verify it's correct
   - Check if the identified commit actually changed the problematic lines

4. **Look for Alternative Explanations**
   - Are there other possible root causes?
   - Did the RCA miss anything obvious?

5. **Assess Completeness**
   - Did the RCA check all relevant files?
   - Should additional files be examined?

Provide your critique in this format:

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
Comments: [Summary]

If you find issues, you can use the same tools to investigate further."""

        # Send to LLM for critique with retry logic
        response = self._call_llm_with_retry([types.Content(
            role="user",
            parts=[types.Part(text=critique_prompt)]
        )])

        # Parse critique
        # TODO: Implement structured parsing
        return {
            'approved': True,  # Parse from response
            'confidence_adjustment': 0.0,
            'comments': response.text,
            'suggested_improvements': []
        }