# Setup Guide

This guide will help you set up and run the Root Cause Analysis Agent System.

## 🚀 Quick Setup

### 1. Prerequisites

- **Python 3.10+** - Download from [python.org](https://python.org)
- **GitHub Account** - Create at [github.com](https://github.com)
- **Google Cloud Account** - Sign up at [cloud.google.com](https://cloud.google.com)

### 2. Get API Keys

#### GitHub Personal Access Token

1. Go to GitHub Settings → Developer settings → Personal access tokens
2. Click "Generate new token (classic)"
3. Select scopes: `repo`, `read:user`
4. Copy the generated token

#### Google Gemini API Key

1. Go to [Google AI Studio](https://makersuite.google.com/app/apikey)
2. Create a new API key
3. Copy the API key

### 3. Installation

Since you already have all the files in your current directory, you can proceed directly with setting up the environment:

```bash
# Create virtual environment (recommended)
python -m venv venv

# Activate virtual environment
# On Windows:
venv\Scripts\activate
# On macOS/Linux:
source venv/bin/activate

# Install dependencies
pip install -r requirements.txt
```

**Note**: If you obtained this code from a repository, you would first need to:
```bash
git clone <repository-url>
cd root_cause_analyzer
```

### 4. Configuration

```bash
# Copy environment template (if it doesn't exist)
copy .env.example .env

# Edit .env file with your API keys
notepad .env
```

**Note**: If you don't have a `.env` file yet, create one based on the `.env.example` template.

Edit the `.env` file:

```env
# Required
GITHUB_TOKEN=your_github_token_here
GEMINI_API_KEY=your_gemini_api_key_here

# Optional
MAX_RCA_ITERATIONS=15
MAX_REFINEMENT_ITERATIONS=2
LOG_LEVEL=INFO
```

### 5. Test Installation

```bash
# Test with sample bug report (using a public repository)
python main.py --bug-report examples/bug_reports/login_bug.json --repo octocat/Hello-World
```

## 📋 Usage Examples

### Command Line Interface

```bash
# Basic analysis
python main.py \
  --bug-report examples/bug_reports/login_bug.json \
  --repo owner/repository

# Custom output format
python main.py \
  --bug-report bug.json \
  --repo owner/repo \
  --output reports/analysis.json \
  --format markdown

# Skip critique for faster analysis
python main.py \
  --bug-report bug.json \
  --repo owner/repo \
  --no-critique

# Debug mode
python main.py \
  --bug-report bug.json \
  --repo owner/repo \
  --log-level DEBUG
```

### REST API (Optional)

Start the API server:

```bash
# Install API dependencies
pip install fastapi uvicorn

# Start server
python api.py
```

Use the API:

```bash
# Submit analysis job
curl -X POST "http://localhost:8000/analyze" \
  -H "Content-Type: application/json" \
  -d '{
    "bug_report": {
      "title": "Login bug",
      "description": "User login fails",
      "steps_to_reproduce": ["Go to login", "Enter credentials"],
      "expected_behavior": "Should login",
      "actual_behavior": "Shows error"
    },
    "repository": "owner/repo"
  }'

# Check job status
curl "http://localhost:8000/jobs/{job_id}"
```

### Programmatic Usage

```python
from core.github_client import GitHubClient
from agents.root_cause_agent import RootCauseAgent
from models.bug_report import BugReport

# Initialize
github = GitHubClient("your_token", "owner/repo")
agent = RootCauseAgent("your_gemini_key", github)

# Create bug report
bug = BugReport(
    title="Login fails",
    description="Authentication error",
    steps_to_reproduce=["Step 1", "Step 2"],
    expected_behavior="Should work",
    actual_behavior="Crashes"
)

# Analyze
result = agent.analyze_bug(bug)

# Access results
print(f"Root cause: {result.root_cause.file_path}")
print(f"Confidence: {result.confidence_score}")
```

## 🔧 Troubleshooting

### Common Issues

#### 1. GitHub Authentication Error

```
Error: 401 Unauthorized
```

**Solution:**
- Check your GitHub token is correct
- Ensure token has `repo` permissions
- Verify repository name format: `owner/repo-name`

#### 2. Gemini API Error

```
Error: 403 Forbidden
```

**Solution:**
- Verify your Gemini API key
- Check API quotas in Google Cloud Console
- Ensure Gemini API is enabled

#### 3. Repository Not Found

```
Error: 404 Not Found
```

**Solution:**
- Check repository exists and is accessible
- Verify repository name spelling
- Ensure you have read access to the repository

#### 4. Rate Limiting

```
Error: 403 Rate limit exceeded
```

**Solution:**
- Wait for rate limit reset (shown in error message)
- Use authenticated requests (token required)
- Reduce analysis frequency

### Debug Mode

Enable detailed logging:

```bash
python main.py \
  --bug-report bug.json \
  --repo owner/repo \
  --log-level DEBUG \
  --log-file debug.log
```

### Test Configuration

```bash
# Test GitHub connection
python -c "
from core.github_client import GitHubClient
from utils.config import config
client = GitHubClient(config.github_token, 'octocat/Hello-World')
print(f'Connected to: {client.repo.full_name}')
"

# Test Gemini API
python -c "
from google import genai
from utils.config import config
client = genai.Client(api_key=config.gemini_api_key)
print('Gemini API working!')
"
```

## 📁 Project Structure

```
root_cause_analyzer/
├── agents/                    # AI agents
│   ├── root_cause_agent.py   # Main analysis agent
│   ├── critique_agent.py     # Validation agent
│   └── orchestrator_agent.py # Workflow manager
├── core/                     # Core functionality
│   ├── github_client.py      # GitHub API wrapper
│   └── code_analyzer.py      # Code parsing
├── models/                   # Data structures
│   ├── bug_report.py         # Bug report model
│   ├── analysis_result.py    # Results model
│   └── commit_info.py        # Commit data
├── utils/                    # Utilities
│   ├── config.py             # Configuration
│   ├── logger.py             # Logging setup
│   └── formatters.py         # Output formatting
├── examples/                 # Examples and samples
├── tests/                    # Test suite
├── main.py                   # CLI entry point
├── api.py                    # REST API (optional)
├── requirements.txt          # Dependencies
└── .env                      # Configuration (create from .env.example)
```

## 🧪 Running Tests

```bash
# Install test dependencies
pip install pytest pytest-cov

# Run all tests
pytest

# Run with coverage
pytest --cov=. --cov-report=html

# Run specific tests
pytest tests/test_github_client.py
pytest tests/test_agents.py
```

## 🚀 Production Deployment

### Environment Variables

For production, set these environment variables:

```env
GITHUB_TOKEN=your_production_token
GEMINI_API_KEY=your_production_key
LOG_LEVEL=WARNING
LOG_FILE=/var/log/rca_agent.log
MAX_RCA_ITERATIONS=20
MAX_REFINEMENT_ITERATIONS=3
```

### Docker Deployment

```dockerfile
FROM python:3.10-slim

WORKDIR /app
COPY requirements.txt .
RUN pip install -r requirements.txt

COPY . .

# CLI usage
CMD ["python", "main.py", "--help"]

# API usage
# CMD ["python", "api.py"]
```

### Security Considerations

- Never commit API keys to version control
- Use environment variables for all secrets
- Rotate API keys regularly
- Monitor API usage and costs
- Implement rate limiting in production

## 📞 Support

If you encounter issues:

1. Check this setup guide
2. Review the [main README](README.md)
3. Check the [development guide](DEVELOPMENT.md)
4. Search existing issues
5. Create a new issue with:
   - Error message
   - Steps to reproduce
   - Environment details
   - Log output (with sensitive data removed)

## 🎯 Next Steps

After successful setup:

1. **Try the examples**: Run sample analyses to understand the system
2. **Create bug reports**: Write JSON bug reports for your issues
3. **Explore repositories**: Test with different GitHub repositories
4. **Customize configuration**: Adjust settings for your needs
5. **Integrate with workflows**: Add to your development process

Happy debugging! 🐛🔍