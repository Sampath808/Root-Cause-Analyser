#!/usr/bin/env python3
"""
Optional FastAPI REST API for the Root Cause Analysis Agent System

This provides a web API interface for the RCA system, allowing remote analysis requests.
"""

from fastapi import FastAPI, HTTPException, BackgroundTasks
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import Optional, Dict, Any
import uuid
from datetime import datetime
import asyncio
from pathlib import Path
import sys

# Add current directory to Python path for imports
sys.path.append(str(Path(__file__).parent))

from core.github_client import GitHubClient
from agents.root_cause_agent import RootCauseAgent
from agents.critique_agent import CritiqueAgent
from agents.orchestrator_agent import OrchestratorAgent
from models.bug_report import BugReport
from utils.config import config
from utils.logger import setup_logger

# Initialize FastAPI app
app = FastAPI(
    title="Root Cause Analysis Agent API",
    description="Intelligent bug investigation using LLM-guided GitHub exploration",
    version="1.0.0"
)

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Setup logging
logger = setup_logger("rca_api", level=config.log_level)

# In-memory storage for analysis jobs (use Redis/database in production)
analysis_jobs: Dict[str, Dict[str, Any]] = {}

# Pydantic models for API
class AnalysisRequest(BaseModel):
    """Request model for analysis."""
    bug_report: Dict[str, Any]
    repository: str
    branch: str = "main"
    max_iterations: Optional[int] = None
    max_refinements: Optional[int] = None
    skip_critique: bool = False

class AnalysisResponse(BaseModel):
    """Response model for analysis."""
    job_id: str
    status: str
    message: str

class JobStatus(BaseModel):
    """Job status response model."""
    job_id: str
    status: str
    progress: Optional[str] = None
    result: Optional[Dict[str, Any]] = None
    error: Optional[str] = None
    created_at: datetime
    completed_at: Optional[datetime] = None

@app.get("/")
async def root():
    """Root endpoint with API information."""
    return {
        "name": "Root Cause Analysis Agent API",
        "version": "1.0.0",
        "description": "Intelligent bug investigation using LLM-guided GitHub exploration",
        "endpoints": {
            "POST /analyze": "Submit bug report for analysis",
            "GET /jobs/{job_id}": "Get analysis job status",
            "GET /jobs": "List all jobs",
            "GET /health": "Health check"
        }
    }

@app.get("/health")
async def health_check():
    """Health check endpoint."""
    try:
        # Validate configuration
        if not config.validate():
            raise HTTPException(status_code=503, detail="Configuration invalid")
        
        return {
            "status": "healthy",
            "timestamp": datetime.now().isoformat(),
            "config": {
                "github_token_configured": bool(config.github_token),
                "gemini_api_configured": bool(config.gemini_api_key)
            }
        }
    except Exception as e:
        logger.error(f"Health check failed: {str(e)}")
        raise HTTPException(status_code=503, detail=f"Service unhealthy: {str(e)}")

@app.post("/analyze", response_model=AnalysisResponse)
async def analyze_bug(request: AnalysisRequest, background_tasks: BackgroundTasks):
    """Submit a bug report for analysis."""
    try:
        # Validate configuration
        if not config.validate():
            raise HTTPException(status_code=503, detail="Service configuration invalid")
        
        # Generate job ID
        job_id = str(uuid.uuid4())
        
        # Create job record
        analysis_jobs[job_id] = {
            "job_id": job_id,
            "status": "queued",
            "progress": "Initializing analysis...",
            "created_at": datetime.now(),
            "request": request.dict()
        }
        
        # Start background analysis
        background_tasks.add_task(run_analysis_job, job_id, request)
        
        logger.info(f"Analysis job {job_id} queued for repository {request.repository}")
        
        return AnalysisResponse(
            job_id=job_id,
            status="queued",
            message="Analysis job submitted successfully"
        )
        
    except Exception as e:
        logger.error(f"Failed to submit analysis job: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Failed to submit job: {str(e)}")

@app.get("/jobs/{job_id}", response_model=JobStatus)
async def get_job_status(job_id: str):
    """Get the status of an analysis job."""
    if job_id not in analysis_jobs:
        raise HTTPException(status_code=404, detail="Job not found")
    
    job = analysis_jobs[job_id]
    return JobStatus(**job)

@app.get("/jobs")
async def list_jobs(limit: int = 50, status: Optional[str] = None):
    """List analysis jobs with optional filtering."""
    jobs = list(analysis_jobs.values())
    
    # Filter by status if specified
    if status:
        jobs = [job for job in jobs if job.get("status") == status]
    
    # Sort by creation time (newest first)
    jobs.sort(key=lambda x: x.get("created_at", datetime.min), reverse=True)
    
    # Limit results
    jobs = jobs[:limit]
    
    return {
        "jobs": jobs,
        "total": len(jobs),
        "limit": limit
    }

@app.delete("/jobs/{job_id}")
async def delete_job(job_id: str):
    """Delete an analysis job."""
    if job_id not in analysis_jobs:
        raise HTTPException(status_code=404, detail="Job not found")
    
    job = analysis_jobs[job_id]
    if job.get("status") == "running":
        raise HTTPException(status_code=400, detail="Cannot delete running job")
    
    del analysis_jobs[job_id]
    logger.info(f"Deleted job {job_id}")
    
    return {"message": "Job deleted successfully"}

async def run_analysis_job(job_id: str, request: AnalysisRequest):
    """Run analysis job in background."""
    try:
        # Update job status
        analysis_jobs[job_id]["status"] = "running"
        analysis_jobs[job_id]["progress"] = "Initializing GitHub client..."
        
        # Create bug report from request
        bug_report = BugReport.from_dict(request.bug_report)
        
        # Initialize GitHub client
        analysis_jobs[job_id]["progress"] = "Connecting to GitHub..."
        github_client = GitHubClient(
            access_token=config.github_token,
            repo_full_name=request.repository,
            branch=request.branch
        )
        
        # Test GitHub connection
        try:
            repo_info = github_client.repo
            logger.info(f"Job {job_id}: Connected to {repo_info.full_name}")
        except Exception as e:
            raise Exception(f"Failed to connect to GitHub repository: {str(e)}")
        
        # Initialize agents
        analysis_jobs[job_id]["progress"] = "Initializing AI agents..."
        rca_agent = RootCauseAgent(config.gemini_api_key, github_client)
        
        if not request.skip_critique:
            critique_agent = CritiqueAgent(config.gemini_api_key, github_client)
            orchestrator = OrchestratorAgent(rca_agent, critique_agent)
        else:
            orchestrator = None
        
        # Run analysis
        analysis_jobs[job_id]["progress"] = "Running root cause analysis..."
        
        max_iterations = request.max_iterations or config.max_rca_iterations
        max_refinements = request.max_refinements or config.max_refinement_iterations
        
        if orchestrator and not request.skip_critique:
            result = orchestrator.run_analysis(bug_report, max_refinements)
        else:
            result = rca_agent.analyze_bug(bug_report, max_iterations)
        
        # Update job with results
        analysis_jobs[job_id].update({
            "status": "completed",
            "progress": "Analysis completed successfully",
            "result": result.to_dict(),
            "completed_at": datetime.now()
        })
        
        logger.info(f"Job {job_id} completed successfully")
        
    except Exception as e:
        # Update job with error
        analysis_jobs[job_id].update({
            "status": "failed",
            "progress": "Analysis failed",
            "error": str(e),
            "completed_at": datetime.now()
        })
        
        logger.error(f"Job {job_id} failed: {str(e)}")

if __name__ == "__main__":
    import uvicorn
    
    # Validate configuration on startup
    if not config.validate():
        logger.error("Configuration validation failed. Cannot start API server.")
        sys.exit(1)
    
    logger.info("Starting Root Cause Analysis API server...")
    
    uvicorn.run(
        app,
        host="0.0.0.0",
        port=8000,
        log_level="info"
    )