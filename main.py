#!/usr/bin/env python3
"""
Root Cause Analysis Agent System - Main Entry Point

A production-ready, LLM-agentic Root Cause Analysis system that intelligently
investigates software bugs by exploring GitHub repositories using tool-calling capabilities.
"""

import argparse
import sys
from pathlib import Path

# Add current directory to Python path for imports
sys.path.append(str(Path(__file__).parent))

from core.github_client import GitHubClient
from agents.root_cause_agent import RootCauseAgent
from agents.critique_agent import CritiqueAgent
from agents.orchestrator_agent import OrchestratorAgent
from models.bug_report import BugReport
from utils.config import config
from utils.logger import setup_logger, log_analysis_start, log_analysis_complete
from utils.formatters import (
    format_analysis_report,
    save_analysis_report,
    format_console_report,
)


def main():
    """Main entry point for the RCA system."""

    # Parse command line arguments
    parser = argparse.ArgumentParser(
        description="Root Cause Analysis Agent - Intelligently investigate software bugs",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python main.py --bug-report examples/bug_reports/login_bug.json --repo owner/repo
  python main.py --bug-report bug.json --repo owner/repo --branch develop --format markdown
  python main.py --bug-report bug.json --repo owner/repo --output reports/analysis.json
        """,
    )

    parser.add_argument(
        "--bug-report", required=True, help="Path to bug report JSON file"
    )
    parser.add_argument(
        "--repo", required=True, help="GitHub repository (owner/repo-name)"
    )
    parser.add_argument(
        "--branch", default="main", help="Branch to analyze (default: main)"
    )
    parser.add_argument(
        "--output",
        default="analysis_report.json",
        help="Output file path (default: analysis_report.json)",
    )
    parser.add_argument(
        "--format",
        choices=["json", "markdown", "both"],
        default="both",
        help="Output format (default: both)",
    )
    parser.add_argument(
        "--max-iterations",
        type=int,
        default=None,
        help=f"Maximum RCA iterations (default: {config.max_rca_iterations})",
    )
    parser.add_argument(
        "--max-refinements",
        type=int,
        default=None,
        help=f"Maximum refinement iterations (default: {config.max_refinement_iterations})",
    )
    parser.add_argument(
        "--log-level",
        choices=["DEBUG", "INFO", "WARNING", "ERROR"],
        default=config.log_level,
        help=f"Logging level (default: {config.log_level})",
    )
    parser.add_argument(
        "--log-file",
        default=config.log_file,
        help=f"Log file path (default: {config.log_file})",
    )
    parser.add_argument(
        "--no-critique",
        action="store_true",
        help="Skip critique phase (faster but less accurate)",
    )

    args = parser.parse_args()

    # Set up logging
    logger = setup_logger(name="rca_main", level=args.log_level, log_file=args.log_file)

    try:
        # Validate configuration
        if not config.validate():
            return 1

        # Load bug report
        logger.info(f"Loading bug report from {args.bug_report}")
        if not Path(args.bug_report).exists():
            logger.error(f"Bug report file not found: {args.bug_report}")
            return 1

        bug_report = BugReport.from_json_file(args.bug_report)
        logger.info(f"Bug report loaded: {bug_report.title}")

        # Initialize GitHub client
        logger.info(f"Connecting to GitHub repository: {args.repo}")
        github_client = GitHubClient(
            access_token=config.github_token,
            repo_full_name=args.repo,
            branch=args.branch,
        )

        # Test GitHub connection
        try:
            repo_info = github_client.repo
            logger.info(
                f"Connected to {repo_info.full_name} ({repo_info.default_branch})"
            )
        except Exception as e:
            logger.error(f"Failed to connect to GitHub repository: {str(e)}")
            logger.error("Please check your GITHUB_TOKEN and repository name")
            return 1

        # Initialize AI agents
        logger.info("Initializing AI agents...")
        rca_agent = RootCauseAgent(github_client)

        if not args.no_critique:
            critique_agent = CritiqueAgent(github_client)
            orchestrator = OrchestratorAgent(rca_agent, critique_agent)
        else:
            orchestrator = None

        logger.info("Agents initialized successfully")

        # Log analysis start
        log_analysis_start(logger, bug_report.title, args.repo)

        # Run analysis
        max_iterations = args.max_iterations or config.max_rca_iterations
        max_refinements = args.max_refinements or config.max_refinement_iterations

        if orchestrator and not args.no_critique:
            logger.info("Starting orchestrated analysis with critique...")
            result = orchestrator.run_analysis(bug_report, max_refinements)
        else:
            logger.info("Starting direct RCA analysis...")
            result = rca_agent.analyze_bug(bug_report, max_iterations)

        # Log completion
        log_analysis_complete(logger, result.iterations, result.confidence_score)

        # Display console summary
        console_report = format_console_report(result)
        print(console_report)

        # Save results
        output_path = Path(args.output)
        output_path.parent.mkdir(parents=True, exist_ok=True)

        if args.format in ["json", "both"]:
            json_path = output_path.with_suffix(".json")
            save_analysis_report(result, str(json_path), "json")

        if args.format in ["markdown", "both"]:
            md_path = output_path.with_suffix(".md")
            save_analysis_report(result, str(md_path), "markdown")

        # Final summary
        logger.info("")
        logger.info("Analysis complete!")
        logger.info(f"Confidence Score: {result.confidence_score:.1%}")
        logger.info(f"Iterations Used: {result.iterations}")
        logger.info(f"Tools Used: {len(set(result.tools_used))}")

        if result.critique_approved:
            logger.info("Analysis approved by critique agent")
        elif not args.no_critique:
            logger.warning("Analysis not approved by critique agent")

        return 0

    except KeyboardInterrupt:
        logger.warning("Analysis interrupted by user")
        return 1
    except Exception as e:
        logger.error(f"Unexpected error: {str(e)}")
        logger.debug("Full traceback:", exc_info=True)
        return 1


if __name__ == "__main__":
    exit_code = main()
    sys.exit(exit_code)
