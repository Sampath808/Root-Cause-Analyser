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

# Orchestrator agent will be created inline for A2A compatibility
from models.bug_report import BugReport
from models.analysis_result import AnalysisResult
from utils.config import config
from utils.logger import setup_logger, log_analysis_start, log_analysis_complete
from utils.formatters import (
    format_analysis_report,
    save_analysis_report,
    format_console_report,
)


def create_a2a_message(sender_id: str, task: str, data: dict) -> dict:
    """Create A2A message format."""
    from datetime import datetime

    return {
        "message_id": f"{sender_id}_{task}_{datetime.now().timestamp()}",
        "sender_id": sender_id,
        "recipient_id": "target_agent",
        "message_type": "task_request",
        "content": {"task": task, "data": data},
        "timestamp": datetime.now().isoformat(),
    }


def run_direct_a2a_analysis(rca_agent, bug_report, max_iterations, logger):
    """Run direct RCA analysis using A2A message protocol."""
    logger.info("Starting direct A2A analysis...")

    # Create A2A message for bug analysis
    message = create_a2a_message(
        sender_id="orchestrator",
        task="analyze_bug",
        data={"bug_report": bug_report.to_dict(), "max_iterations": max_iterations},
    )

    # Send message to RCA agent
    response = rca_agent.process(message)

    if response.get("status") == "success":
        analysis_data = response["content"]["result"]["analysis"]
        logger.info("A2A analysis completed successfully")
        return AnalysisResult.from_dict(analysis_data)
    else:
        error_msg = response["content"].get("error", "Unknown error")
        logger.error(f"A2A analysis failed: {error_msg}")
        raise Exception(f"RCA analysis failed: {error_msg}")


def run_a2a_orchestrated_analysis(
    rca_agent, critique_agent, bug_report, max_refinements, logger
):
    """Run orchestrated analysis with critique using A2A message protocol."""
    logger.info("Starting A2A orchestrated analysis with critique...")

    # Step 1: Initial RCA analysis
    logger.info("Step 1: Running initial RCA analysis...")
    rca_message = create_a2a_message(
        sender_id="orchestrator",
        task="analyze_bug",
        data={
            "bug_report": bug_report.to_dict(),
            "max_iterations": 10,  # Reduced for iterative refinement
        },
    )

    rca_response = rca_agent.process(rca_message)

    if rca_response.get("status") != "success":
        error_msg = rca_response["content"].get("error", "Unknown error")
        logger.error(f"Initial RCA analysis failed: {error_msg}")
        raise Exception(f"RCA analysis failed: {error_msg}")

    analysis_data = rca_response["content"]["result"]["analysis"]
    logger.info("Initial analysis completed")

    # Step 2: Critique analysis
    refinement_count = 0

    while refinement_count < max_refinements:
        logger.info(f"Step 2.{refinement_count + 1}: Running critique analysis...")

        critique_message = create_a2a_message(
            sender_id="orchestrator",
            task="critique_analysis",
            data={"bug_report": bug_report.to_dict(), "analysis_result": analysis_data},
        )

        critique_response = critique_agent.process(critique_message)

        if critique_response.get("status") != "success":
            logger.warning("Critique failed, using original analysis")
            break

        critique_data = critique_response["content"]["result"]["critique"]
        logger.info(
            f"Critique completed - Approved: {critique_data.get('approved', False)}"
        )

        # Step 3: Check if improvement needed
        if critique_data.get("approved", False):
            logger.info("Analysis approved by critique agent")
            # Update analysis with critique approval
            analysis_data["critique_approved"] = True
            analysis_data["critique_feedback"] = critique_data
            break

        # Step 4: Improve analysis based on critique
        if refinement_count < max_refinements - 1:
            logger.info("Improving analysis based on critique feedback...")

            improvement_message = create_a2a_message(
                sender_id="orchestrator",
                task="improve_analysis",
                data={
                    "bug_report": bug_report.to_dict(),
                    "original_analysis": analysis_data,
                    "critique_feedback": critique_data,
                },
            )

            improvement_response = rca_agent.process(improvement_message)

            if improvement_response.get("status") == "success":
                analysis_data = improvement_response["content"]["result"][
                    "improved_analysis"
                ]
                logger.info("Analysis improved")
            else:
                logger.warning("Improvement failed, keeping original analysis")
                break

        refinement_count += 1

    if refinement_count >= max_refinements:
        logger.warning(f"Max refinements ({max_refinements}) reached")
        analysis_data["critique_approved"] = False

    logger.info("A2A orchestrated analysis completed")
    return AnalysisResult.from_dict(analysis_data)


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
    parser.add_argument(
        "--a2a-server",
        action="store_true",
        help="Run orchestrator as A2A server instead of single analysis",
    )
    parser.add_argument(
        "--a2a-port",
        type=int,
        default=8002,
        help="Port for A2A server (default: 8002)",
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
        rca_agent = RootCauseAgent(config.gemini_api_key, github_client)

        if not args.no_critique:
            critique_agent = CritiqueAgent(config.gemini_api_key, github_client)
            logger.info("Both RCA and Critique agents initialized for A2A workflow")
        else:
            critique_agent = None
            logger.info("Only RCA agent initialized (critique disabled)")

        logger.info("Agents initialized successfully")

        # Check if running as A2A server
        if args.a2a_server:
            logger.error("A2A server mode not yet implemented for pure A2A agents")
            logger.info("Use direct analysis mode instead")
            return 1

        # Log analysis start
        log_analysis_start(logger, bug_report.title, args.repo)

        # Run analysis using A2A message protocol
        max_iterations = args.max_iterations or config.max_rca_iterations
        max_refinements = args.max_refinements or config.max_refinement_iterations

        if critique_agent and not args.no_critique:
            logger.info("Starting A2A orchestrated analysis with critique...")
            result = run_a2a_orchestrated_analysis(
                rca_agent, critique_agent, bug_report, max_refinements, logger
            )
        else:
            logger.info("Starting direct A2A analysis...")
            result = run_direct_a2a_analysis(
                rca_agent, bug_report, max_iterations, logger
            )

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
