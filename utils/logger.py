"""Logging configuration for the RCA system."""

import logging
import sys
from datetime import datetime
from pathlib import Path
from rich.console import Console
from rich.logging import RichHandler

def setup_logger(name: str = "rca_agent", level: str = "INFO", log_file: str = None) -> logging.Logger:
    """Set up logger with rich formatting and optional file output.
    
    Args:
        name: Logger name
        level: Logging level (DEBUG, INFO, WARNING, ERROR)
        log_file: Optional log file path
        
    Returns:
        Configured logger
    """
    logger = logging.getLogger(name)
    logger.setLevel(getattr(logging, level.upper()))
    
    # Clear existing handlers
    logger.handlers.clear()
    
    # Console handler with rich formatting
    console = Console()
    console_handler = RichHandler(
        console=console,
        show_time=True,
        show_path=False,
        rich_tracebacks=True
    )
    console_handler.setLevel(getattr(logging, level.upper()))
    
    # Format for console
    console_format = logging.Formatter(
        fmt="%(message)s",
        datefmt="[%X]"
    )
    console_handler.setFormatter(console_format)
    logger.addHandler(console_handler)
    
    # File handler if specified
    if log_file:
        log_path = Path(log_file)
        log_path.parent.mkdir(parents=True, exist_ok=True)
        
        file_handler = logging.FileHandler(log_path)
        file_handler.setLevel(logging.DEBUG)  # Always log everything to file
        
        # Format for file
        file_format = logging.Formatter(
            fmt="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
            datefmt="%Y-%m-%d %H:%M:%S"
        )
        file_handler.setFormatter(file_format)
        logger.addHandler(file_handler)
    
    return logger

def log_tool_execution(logger: logging.Logger, tool_name: str, parameters: dict, 
                      execution_time: float, success: bool, error: str = None):
    """Log tool execution details."""
    if success:
        logger.info(f"Tool {tool_name} completed in {execution_time:.2f}s")
        logger.debug(f"   Parameters: {parameters}")
    else:
        logger.error(f"Tool {tool_name} failed after {execution_time:.2f}s")
        logger.error(f"   Error: {error}")
        logger.debug(f"   Parameters: {parameters}")

def log_analysis_start(logger: logging.Logger, bug_title: str, repo: str):
    """Log analysis start."""
    logger.info("="*80)
    logger.info("ROOT CAUSE ANALYSIS STARTED")
    logger.info("="*80)
    logger.info(f"Bug: {bug_title}")
    logger.info(f"Repository: {repo}")
    logger.info(f"Timestamp: {datetime.now().isoformat()}")
    logger.info("")

def log_analysis_complete(logger: logging.Logger, iterations: int, confidence: float):
    """Log analysis completion."""
    logger.info("")
    logger.info("="*80)
    logger.info("ANALYSIS COMPLETE")
    logger.info("="*80)
    logger.info(f"Iterations: {iterations}")
    logger.info(f"Confidence: {confidence:.2f}")
    logger.info("="*80)