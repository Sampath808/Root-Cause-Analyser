#!/usr/bin/env python3
"""
Sample usage of the Root Cause Analysis Agent System

This example shows how to use the RCA system programmatically.
"""

import sys
from pathlib import Path

# Add parent directory to path for imports
sys.path.append(str(Path(__file__).parent.parent))

from core.github_client import GitHubClient
from agents.root_cause_agent import RootCauseAgent
from agents.critique_agent import CritiqueAgent
from agents.orchestrator_agent import OrchestratorAgent
from models.bug_report import BugReport
from utils.config import config
from utils.logger import setup_logger
from utils.formatters import format_console_report

def main():
    """Example usage of the RCA system."""
    
    # Set up logging
    logger = setup_logger(name="rca_example", level="INFO")
    
    # Validate configuration
    if not config.validate():
        logger.error("Configuration validation failed")
        return
    
    # Load a sample bug report
    bug_report_path = Path(__file__).parent / "bug_reports" / "login_bug.json"
    bug_report = BugReport.from_json_file(str(bug_report_path))
    
    logger.info(f"Loaded bug report: {bug_report.title}")
    
    # Initialize GitHub client (replace with actual repository)
    # For this example, we'll use a public repository
    github_client = GitHubClient(
        access_token=config.github_token,
        repo_full_name="octocat/Hello-World",  # Example public repo
        branch="master"
    )
    
    # Initialize agents
    rca_agent = RootCauseAgent(config.gemini_api_key, github_client)
    critique_agent = CritiqueAgent(config.gemini_api_key, github_client)
    orchestrator = OrchestratorAgent(rca_agent, critique_agent)
    
    logger.info("Agents initialized successfully")
    
    # Run analysis
    logger.info("Starting root cause analysis...")
    result = orchestrator.run_analysis(bug_report, max_refinement_iterations=1)
    
    # Display results
    console_report = format_console_report(result)
    print(console_report)
    
    # Access specific result fields
    logger.info(f"Root cause file: {result.root_cause.file_path}")
    logger.info(f"Confidence score: {result.confidence_score:.2f}")
    logger.info(f"Tools used: {', '.join(set(result.tools_used))}")
    
    # Save results
    output_dir = Path("output")
    output_dir.mkdir(exist_ok=True)
    
    # Save as JSON
    json_path = output_dir / "sample_analysis.json"
    with open(json_path, 'w') as f:
        f.write(result.to_json())
    
    # Save as Markdown
    md_path = output_dir / "sample_analysis.md"
    with open(md_path, 'w') as f:
        f.write(result.to_markdown())
    
    logger.info(f"Results saved to {output_dir}")

if __name__ == "__main__":
    main()