"""Configuration management for the RCA system."""

import os
from typing import Optional
from dotenv import load_dotenv

class Config:
    """Configuration class for RCA system."""
    
    def __init__(self):
        load_dotenv()
        
        # GitHub Configuration
        self.github_token = os.getenv('GITHUB_TOKEN')
        self.repo_owner = os.getenv('REPO_OWNER')
        self.repo_name = os.getenv('REPO_NAME')
        self.default_branch = os.getenv('DEFAULT_BRANCH', 'main')
        
        # Gemini Configuration
        self.gemini_api_key = os.getenv('GEMINI_API_KEY')
        self.gemini_model = os.getenv('GEMINI_MODEL', 'models/gemini-2.5-flash')
        
        # Agent Configuration
        self.max_rca_iterations = int(os.getenv('MAX_RCA_ITERATIONS', 15))
        self.max_refinement_iterations = int(os.getenv('MAX_REFINEMENT_ITERATIONS', 2))
        self.max_api_retries = int(os.getenv('MAX_API_RETRIES', 5))
        self.retry_base_delay = float(os.getenv('RETRY_BASE_DELAY', 1.0))
        
        # Logging Configuration
        self.log_level = os.getenv('LOG_LEVEL', 'INFO')
        self.log_file = os.getenv('LOG_FILE', 'rca_agent.log')
    
    def validate(self) -> bool:
        """Validate that required configuration is present."""
        required_vars = [
            ('GITHUB_TOKEN', self.github_token),
            ('GEMINI_API_KEY', self.gemini_api_key)
        ]
        
        missing = []
        for var_name, var_value in required_vars:
            if not var_value:
                missing.append(var_name)
        
        if missing:
            print(f"❌ Missing required environment variables: {', '.join(missing)}")
            print("Please check your .env file")
            return False
        
        return True
    
    def get_repo_full_name(self, repo_override: Optional[str] = None) -> str:
        """Get full repository name in owner/repo format."""
        if repo_override:
            return repo_override
        
        if self.repo_owner and self.repo_name:
            return f"{self.repo_owner}/{self.repo_name}"
        
        raise ValueError("Repository not specified. Use --repo argument or set REPO_OWNER/REPO_NAME in .env")

# Global config instance
config = Config()