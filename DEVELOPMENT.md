# Development Guide

This document provides detailed information for developers working on the Root Cause Analysis Agent System.

## 🏗️ Architecture Overview

### System Components

The RCA system follows a modular architecture with clear separation of concerns:

```
┌─────────────────┐    ┌─────────────────┐    ┌─────────────────┐
│   CLI/API       │    │   Orchestrator  │    │   Formatters    │
│   Interface     │────│     Agent       │────│   & Reports     │
└─────────────────┘    └─────────────────┘    └─────────────────┘
                              │
                    ┌─────────┴─────────┐
                    │                   │
            ┌───────▼────────┐  ┌───────▼────────┐
            │ Root Cause     │  │ Critique       │
            │ Agent          │  │ Agent          │
            └───────┬────────┘  └───────┬────────┘
                    │                   │
                    └─────────┬─────────┘
                              │
                    ┌─────────▼─────────┐
                    │ GitHub Client     │
                    │ (12 Tools)        │
                    └───────────────────┘
```

### Data Flow

1. **Input**: Bug report (JSON) + Repository information
2. **Analysis**: RCA Agent uses GitHub tools via LLM function calling
3. **Critique**: Critique Agent validates findings
4. **Refinement**: Orchestrator manages iteration cycles
5. **Output**: Structured analysis results in multiple formats

## 🔧 Development Setup

### Prerequisites

- Python 3.10+
- Git
- GitHub account with personal access token
- Google Cloud account with Gemini API access

### Local Development

```bash
# Clone and setup
git clone <repo-url>
cd root_cause_analyzer

# Create virtual environment
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt

# Install development dependencies
pip install pytest pytest-cov black flake8 mypy

# Setup pre-commit hooks
pip install pre-commit
pre-commit install
```

### Environment Configuration

Create `.env` file:

```env
# Required
GITHUB_TOKEN=ghp_xxxxxxxxxxxxxxxxxxxx
GEMINI_API_KEY=AIzaSyxxxxxxxxxxxxxxxxxx

# Optional Development Settings
LOG_LEVEL=DEBUG
LOG_FILE=logs/rca_dev.log
MAX_RCA_ITERATIONS=10  # Shorter for testing
MAX_REFINEMENT_ITERATIONS=1
```

## 🧪 Testing Strategy

### Test Structure

```
tests/
├── unit/
│   ├── test_github_client.py
│   ├── test_agents.py
│   ├── test_models.py
│   └── test_utils.py
├── integration/
│   ├── test_full_workflow.py
│   └── test_github_integration.py
├── fixtures/
│   ├── sample_repositories/
│   ├── mock_responses/
│   └── test_bug_reports.json
└── conftest.py
```

### Running Tests

```bash
# Run all tests
pytest

# Run with coverage
pytest --cov=. --cov-report=html

# Run specific test categories
pytest tests/unit/
pytest tests/integration/

# Run with verbose output
pytest -v -s
```

### Test Categories

1. **Unit Tests**: Test individual components in isolation
2. **Integration Tests**: Test component interactions
3. **End-to-End Tests**: Test complete workflows
4. **Mock Tests**: Test with simulated GitHub/LLM responses

### Writing Tests

Example unit test:

```python
import pytest
from unittest.mock import Mock, patch
from core.github_client import GitHubClient

class TestGitHubClient:
    @pytest.fixture
    def github_client(self):
        return GitHubClient("fake_token", "owner/repo")
    
    @patch('github.Github')
    def test_get_file_content(self, mock_github, github_client):
        # Setup mock
        mock_content = Mock()
        mock_content.decoded_content = b"print('hello')"
        mock_github.return_value.get_repo.return_value.get_contents.return_value = mock_content
        
        # Test
        result = github_client.get_file_content("test.py")
        
        # Assert
        assert result == "print('hello')"
```

## 🔍 Code Quality

### Code Style

We use Black for code formatting and follow PEP 8:

```bash
# Format code
black .

# Check style
flake8 .

# Type checking
mypy .
```

### Code Review Checklist

- [ ] Code follows PEP 8 style guidelines
- [ ] All functions have docstrings
- [ ] Type hints are used where appropriate
- [ ] Error handling is comprehensive
- [ ] Tests cover new functionality
- [ ] No hardcoded secrets or tokens
- [ ] Logging is appropriate and informative

### Pre-commit Hooks

The project uses pre-commit hooks to ensure code quality:

```yaml
# .pre-commit-config.yaml
repos:
  - repo: https://github.com/psf/black
    rev: 23.1.0
    hooks:
      - id: black
  - repo: https://github.com/pycqa/flake8
    rev: 6.0.0
    hooks:
      - id: flake8
  - repo: https://github.com/pre-commit/mirrors-mypy
    rev: v1.0.1
    hooks:
      - id: mypy
```

## 🛠️ Adding New Features

### Adding a New GitHub Tool

1. **Add method to GitHubClient**:

```python
def new_tool_method(self, param1: str, param2: int = 10) -> str:
    """Description of what this tool does.
    
    Args:
        param1: Description
        param2: Description with default
        
    Returns:
        JSON string with results
    """
    try:
        # Implementation
        result = self.repo.some_api_call(param1, param2)
        return json.dumps(result, indent=2)
    except Exception as e:
        return json.dumps({'error': str(e)})
```

2. **Add tool configuration to RootCauseAgent**:

```python
{
    'name': 'new_tool_method',
    'description': '''Detailed description for the LLM about when and how to use this tool.''',
    'parameters': {
        'type': 'object',
        'properties': {
            'param1': {
                'type': 'string',
                'description': 'Parameter description'
            },
            'param2': {
                'type': 'integer',
                'description': 'Optional parameter (default: 10)'
            }
        },
        'required': ['param1']
    }
}
```

3. **Add execution logic**:

```python
elif tool_name == 'new_tool_method':
    return self.github.new_tool_method(
        parameters['param1'],
        parameters.get('param2', 10)
    )
```

4. **Write tests**:

```python
def test_new_tool_method(self, github_client):
    result = github_client.new_tool_method("test_param")
    assert "error" not in result
    # Additional assertions
```

### Adding a New Agent

1. **Create agent class**:

```python
class NewAgent:
    def __init__(self, gemini_api_key: str, github_client: GitHubClient):
        # Initialize
        pass
    
    def process(self, input_data) -> output_type:
        # Implementation
        pass
```

2. **Add to orchestrator**:

```python
def __init__(self, rca_agent, critique_agent, new_agent):
    self.new_agent = new_agent
    # ...
```

3. **Update workflow**:

```python
def run_analysis(self, bug_report):
    # Existing workflow
    result = self.rca_agent.analyze_bug(bug_report)
    
    # Add new agent step
    enhanced_result = self.new_agent.process(result)
    
    return enhanced_result
```

## 📊 Performance Optimization

### Caching Strategy

The system implements several caching mechanisms:

1. **File Content Cache**: Avoid repeated GitHub API calls
2. **Repository Structure Cache**: Cache directory listings
3. **Commit Information Cache**: Cache commit details

### Rate Limiting

GitHub API has rate limits (5000 requests/hour for authenticated users):

```python
def _handle_rate_limit(self):
    """Handle GitHub API rate limiting."""
    rate_limit = self.g.get_rate_limit()
    if rate_limit.core.remaining < 10:
        reset_time = rate_limit.core.reset
        wait_time = (reset_time - datetime.now()).total_seconds()
        logger.warning(f"Rate limit low, waiting {wait_time}s")
        time.sleep(wait_time)
```

### Memory Management

For large repositories:

```python
def _manage_memory(self):
    """Clear caches when memory usage is high."""
    if len(self._file_cache) > 1000:
        # Keep only most recently used files
        self._file_cache = dict(list(self._file_cache.items())[-500:])
```

## 🔐 Security Guidelines

### API Key Management

- Never commit API keys to version control
- Use environment variables for all secrets
- Rotate keys regularly
- Use minimal required permissions

### Input Validation

```python
def validate_file_path(self, path: str) -> bool:
    """Validate file path to prevent directory traversal."""
    # Normalize path
    normalized = os.path.normpath(path)
    
    # Check for directory traversal attempts
    if '..' in normalized or normalized.startswith('/'):
        raise ValueError(f"Invalid file path: {path}")
    
    return True
```

### Error Information

```python
def safe_error_message(self, error: Exception) -> str:
    """Return safe error message without sensitive information."""
    # Don't expose internal paths, tokens, or system details
    safe_message = str(error).replace(self.github_token, '[TOKEN]')
    return safe_message
```

## 📝 Documentation Standards

### Docstring Format

Use Google-style docstrings:

```python
def analyze_function(self, file_path: str, function_name: str) -> Dict[str, Any]:
    """Extract and analyze a specific function from a file.
    
    This method uses AST parsing to extract function information including
    parameters, docstrings, and complexity metrics.
    
    Args:
        file_path: Path to the file containing the function
        function_name: Name of the function to analyze
        
    Returns:
        Dictionary containing function analysis results with keys:
        - function_name: Name of the function
        - start_line: Starting line number
        - parameters: List of parameter names
        - complexity: Estimated complexity score
        
    Raises:
        FileNotFoundError: If the specified file doesn't exist
        SyntaxError: If the file contains invalid Python syntax
        
    Example:
        >>> client = GitHubClient(token, "owner/repo")
        >>> result = client.analyze_function("src/utils.py", "helper_func")
        >>> print(result['parameters'])
        ['param1', 'param2']
    """
```

### README Updates

When adding features, update:

1. Feature list in README
2. Usage examples
3. Configuration options
4. API documentation

## 🚀 Deployment

### Production Considerations

1. **Environment Variables**: Use secure secret management
2. **Logging**: Configure appropriate log levels and rotation
3. **Monitoring**: Add health checks and metrics
4. **Error Handling**: Ensure graceful degradation
5. **Rate Limiting**: Implement backoff strategies

### Docker Deployment

```dockerfile
FROM python:3.10-slim

WORKDIR /app
COPY requirements.txt .
RUN pip install -r requirements.txt

COPY . .

CMD ["python", "main.py"]
```

### API Deployment

For REST API deployment:

```python
# api.py
from fastapi import FastAPI, HTTPException
from models.bug_report import BugReport

app = FastAPI(title="RCA Agent API")

@app.post("/analyze")
async def analyze_bug(bug_report: BugReport, repo: str):
    try:
        # Initialize and run analysis
        result = orchestrator.run_analysis(bug_report)
        return result.to_dict()
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
```

## 🐛 Debugging

### Common Issues

1. **GitHub API Authentication**:
   ```bash
   # Test token
   curl -H "Authorization: token $GITHUB_TOKEN" https://api.github.com/user
   ```

2. **Gemini API Issues**:
   ```python
   # Test API key
   import google.generativeai as genai
   genai.configure(api_key=api_key)
   model = genai.GenerativeModel('gemini-pro')
   response = model.generate_content("Hello")
   ```

3. **Rate Limiting**:
   ```python
   # Check rate limit status
   rate_limit = github_client.g.get_rate_limit()
   print(f"Remaining: {rate_limit.core.remaining}")
   ```

### Debug Mode

Enable debug logging:

```bash
python main.py --log-level DEBUG --bug-report bug.json --repo owner/repo
```

### Profiling

For performance analysis:

```python
import cProfile
import pstats

# Profile analysis
profiler = cProfile.Profile()
profiler.enable()

result = agent.analyze_bug(bug_report)

profiler.disable()
stats = pstats.Stats(profiler)
stats.sort_stats('cumulative').print_stats(20)
```

## 📈 Metrics and Monitoring

### Key Metrics

1. **Analysis Success Rate**: Percentage of successful analyses
2. **Average Confidence Score**: Quality of results
3. **Analysis Time**: Performance metric
4. **API Usage**: GitHub API calls per analysis
5. **Error Rates**: System reliability

### Logging Best Practices

```python
# Structured logging
logger.info("Analysis started", extra={
    'bug_id': bug_report.title,
    'repo': repo_name,
    'timestamp': datetime.now().isoformat()
})

# Performance logging
with timer() as t:
    result = agent.analyze_bug(bug_report)
logger.info(f"Analysis completed in {t.elapsed:.2f}s")
```

## 🤝 Contributing Guidelines

### Pull Request Process

1. **Fork** the repository
2. **Create** a feature branch: `git checkout -b feature/new-tool`
3. **Implement** changes with tests
4. **Run** test suite: `pytest`
5. **Format** code: `black .`
6. **Commit** with descriptive message
7. **Push** and create pull request

### Commit Message Format

```
type(scope): description

- feat: new feature
- fix: bug fix
- docs: documentation
- style: formatting
- refactor: code restructuring
- test: adding tests
- chore: maintenance

Example:
feat(github): add repository statistics tool

- Add get_repository_stats method to GitHubClient
- Include metrics like contributor count, language breakdown
- Add corresponding tool configuration for RCA agent
```

### Code Review Process

1. **Automated Checks**: CI/CD pipeline runs tests and linting
2. **Manual Review**: Code review by maintainers
3. **Testing**: Verify functionality works as expected
4. **Documentation**: Ensure docs are updated
5. **Merge**: Squash and merge after approval

---

This development guide should help you understand the system architecture and contribute effectively to the project.