"""Output formatting utilities for analysis results."""

import json
from datetime import datetime
from typing import Dict, Any
from models.analysis_result import AnalysisResult

def format_analysis_report(result: AnalysisResult, format_type: str = 'markdown') -> str:
    """Format analysis result into specified format.
    
    Args:
        result: Analysis result to format
        format_type: 'json', 'markdown', or 'console'
        
    Returns:
        Formatted string
    """
    if format_type == 'json':
        return result.to_json()
    elif format_type == 'markdown':
        return result.to_markdown()
    elif format_type == 'console':
        return format_console_report(result)
    else:
        raise ValueError(f"Unknown format type: {format_type}")

def format_console_report(result: AnalysisResult) -> str:
    """Format analysis result for console display."""
    report = f"""
╔══════════════════════════════════════════════════════════════════════════════╗
║                           ROOT CAUSE ANALYSIS REPORT                        ║
╚══════════════════════════════════════════════════════════════════════════════╝

🐛 BUG: {result.bug_report_title}
📅 ANALYZED: {result.analysis_timestamp.strftime('%Y-%m-%d %H:%M:%S')}
🎯 CONFIDENCE: {result.confidence_score:.1%}
🔄 ITERATIONS: {result.iterations}
✅ CRITIQUE: {'Approved' if result.critique_approved else 'Not Approved'}

┌─ ROOT CAUSE ─────────────────────────────────────────────────────────────────┐
│ File: {result.root_cause.file_path}
│ Lines: {', '.join(map(str, result.root_cause.line_numbers)) if result.root_cause.line_numbers else 'N/A'}
│ 
│ Code:
│ {result.root_cause.code_snippet or 'N/A'}
│ 
│ Explanation:
│ {result.root_cause.explanation}
└──────────────────────────────────────────────────────────────────────────────┘
"""

    if result.commit_info:
        report += f"""
┌─ COMMIT INFORMATION ─────────────────────────────────────────────────────────┐
│ SHA: {result.commit_info.commit_sha}
│ Author: {result.commit_info.author.name} ({result.commit_info.author.email})
│ Date: {result.commit_info.commit_date.strftime('%Y-%m-%d %H:%M:%S')}
│ Message: {result.commit_info.commit_message}
│ URL: {result.commit_info.commit_url}
└──────────────────────────────────────────────────────────────────────────────┘
"""

    if result.suggested_fix:
        report += f"""
┌─ SUGGESTED FIX ──────────────────────────────────────────────────────────────┐
│ {result.suggested_fix}
└──────────────────────────────────────────────────────────────────────────────┘
"""

    if result.verification_steps:
        report += f"""
┌─ VERIFICATION STEPS ─────────────────────────────────────────────────────────┐
"""
        for i, step in enumerate(result.verification_steps, 1):
            report += f"│ {i}. {step}\n"
        report += "└──────────────────────────────────────────────────────────────────────────────┘\n"

    report += f"""
┌─ ANALYSIS DETAILS ───────────────────────────────────────────────────────────┐
│ Tools Used: {', '.join(result.tools_used)}
│ Related Files: {', '.join(result.root_cause.related_files) if result.root_cause.related_files else 'None'}
└──────────────────────────────────────────────────────────────────────────────┘
"""

    if result.critique_comments:
        report += f"""
┌─ CRITIQUE COMMENTS ──────────────────────────────────────────────────────────┐
│ {result.critique_comments}
└──────────────────────────────────────────────────────────────────────────────┘
"""

    return report

def format_tool_summary(tool_executions: list) -> str:
    """Format tool execution summary."""
    if not tool_executions:
        return "No tools executed."
    
    summary = "Tool Execution Summary:\n"
    summary += "=" * 50 + "\n"
    
    for i, execution in enumerate(tool_executions, 1):
        status = "✅" if execution.success else "❌"
        summary += f"{i:2d}. {status} {execution.tool_name} ({execution.execution_time:.2f}s)\n"
        
        if execution.error:
            summary += f"     Error: {execution.error}\n"
    
    total_time = sum(e.execution_time for e in tool_executions)
    success_rate = sum(1 for e in tool_executions if e.success) / len(tool_executions)
    
    summary += f"\nTotal Time: {total_time:.2f}s\n"
    summary += f"Success Rate: {success_rate:.1%}\n"
    
    return summary

def save_analysis_report(result: AnalysisResult, output_path: str, format_type: str = 'json'):
    """Save analysis result to file.
    
    Args:
        result: Analysis result to save
        output_path: Output file path
        format_type: Format to save in ('json' or 'markdown')
    """
    content = format_analysis_report(result, format_type)
    
    with open(output_path, 'w', encoding='utf-8') as f:
        f.write(content)
    
    print(f"📄 Report saved to: {output_path}")

def create_summary_stats(results: list) -> Dict[str, Any]:
    """Create summary statistics from multiple analysis results."""
    if not results:
        return {}
    
    total_analyses = len(results)
    avg_confidence = sum(r.confidence_score for r in results) / total_analyses
    avg_iterations = sum(r.iterations for r in results) / total_analyses
    approval_rate = sum(1 for r in results if r.critique_approved) / total_analyses
    
    # Tool usage statistics
    all_tools = []
    for result in results:
        all_tools.extend(result.tools_used)
    
    tool_counts = {}
    for tool in all_tools:
        tool_counts[tool] = tool_counts.get(tool, 0) + 1
    
    most_used_tools = sorted(tool_counts.items(), key=lambda x: x[1], reverse=True)[:5]
    
    return {
        'total_analyses': total_analyses,
        'average_confidence': avg_confidence,
        'average_iterations': avg_iterations,
        'critique_approval_rate': approval_rate,
        'most_used_tools': most_used_tools,
        'tool_usage_stats': tool_counts
    }