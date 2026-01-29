from dataclasses import dataclass, field
from typing import List, Optional
from datetime import datetime
import json
from .commit_info import CommitInfo, AuthorInfo

@dataclass
class RootCause:
    """Root cause identification"""
    file_path: str
    line_numbers: List[int]
    code_snippet: str
    explanation: str
    execution_trace: List[str] = field(default_factory=list)
    related_files: List[str] = field(default_factory=list)
    confidence_score: float = 0.0  # 0.0 to 1.0

@dataclass
class AnalysisResult:
    """Complete analysis result"""
    bug_report_title: str
    root_cause: RootCause
    commit_info: Optional[CommitInfo]
    author_info: Optional[AuthorInfo]
    verification_steps: List[str]
    suggested_fix: Optional[str]
    confidence_score: float
    tools_used: List[str]
    iterations: int
    analysis_timestamp: datetime
    critique_approved: bool = False
    critique_comments: Optional[str] = None

    def to_dict(self) -> dict:
        """Convert to dictionary"""
        return {
            'bug_report_title': self.bug_report_title,
            'root_cause': {
                'file_path': self.root_cause.file_path,
                'line_numbers': self.root_cause.line_numbers,
                'code_snippet': self.root_cause.code_snippet,
                'explanation': self.root_cause.explanation,
                'execution_trace': self.root_cause.execution_trace,
                'related_files': self.root_cause.related_files,
                'confidence_score': self.root_cause.confidence_score
            },
            'commit_info': self.commit_info.to_dict() if self.commit_info else None,
            'author_info': {
                'name': self.author_info.name,
                'email': self.author_info.email,
                'github_username': self.author_info.github_username,
                'total_commits_to_repo': self.author_info.total_commits_to_repo,
                'recent_commits_to_file': self.author_info.recent_commits_to_file
            } if self.author_info else None,
            'verification_steps': self.verification_steps,
            'suggested_fix': self.suggested_fix,
            'confidence_score': self.confidence_score,
            'tools_used': self.tools_used,
            'iterations': self.iterations,
            'analysis_timestamp': self.analysis_timestamp.isoformat(),
            'critique_approved': self.critique_approved,
            'critique_comments': self.critique_comments
        }

    def to_json(self) -> str:
        """Convert to JSON string"""
        return json.dumps(self.to_dict(), indent=2, default=str)

    def to_markdown(self) -> str:
        """Convert to Markdown report"""
        md = f"""# Root Cause Analysis Report

## Bug Report
**Title:** {self.bug_report_title}
**Analysis Date:** {self.analysis_timestamp.strftime('%Y-%m-%d %H:%M:%S')}
**Confidence Score:** {self.confidence_score:.2f}
**Iterations:** {self.iterations}
**Critique Approved:** {'✅ Yes' if self.critique_approved else '❌ No'}

## Root Cause

**File:** `{self.root_cause.file_path}`
**Lines:** {', '.join(map(str, self.root_cause.line_numbers))}

### Code Snippet
```
{self.root_cause.code_snippet}
```

### Explanation
{self.root_cause.explanation}

### Execution Trace
"""
        for i, step in enumerate(self.root_cause.execution_trace, 1):
            md += f"{i}. {step}\n"

        if self.commit_info:
            md += f"""
## Commit Information
- **SHA:** {self.commit_info.commit_sha}
- **Author:** {self.commit_info.author.name} ({self.commit_info.author.email})
- **Date:** {self.commit_info.commit_date.strftime('%Y-%m-%d %H:%M:%S')}
- **Message:** {self.commit_info.commit_message}
- **URL:** {self.commit_info.commit_url}
- **Files Changed:** {len(self.commit_info.files_changed)}
- **Additions:** +{self.commit_info.additions}
- **Deletions:** -{self.commit_info.deletions}
"""

        if self.suggested_fix:
            md += f"""
## Suggested Fix
{self.suggested_fix}
"""

        md += """
## Verification Steps
"""
        for i, step in enumerate(self.verification_steps, 1):
            md += f"{i}. {step}\n"

        md += f"""
## Tools Used
{', '.join(self.tools_used)}

## Related Files
"""
        for file in self.root_cause.related_files:
            md += f"- `{file}`\n"

        if self.critique_comments:
            md += f"""
## Critique Comments
{self.critique_comments}
"""

        return md

@dataclass
class ToolExecutionResult:
    """Result from a tool execution"""
    tool_name: str
    parameters: dict
    result: str
    execution_time: float
    success: bool
    error: Optional[str] = None