# Root Cause Analysis Agent System

A production-ready, LLM-agentic Root Cause Analysis system that intelligently investigates software bugs by exploring GitHub repositories using tool-calling capabilities. The system uses **Google ADK (Agent Development Kit) with Gemini models** and function calling to allow agents to decide which files to examine, trace execution flows, and identify the exact commit and author responsible for bugs.

## 🚀 Key Features

- **🧠 Intelligent Investigation**: Uses LLM-guided tool calling to explore codebases on-demand
- **🤖 Google ADK Integration**: Built with Google's Agent Development Kit for robust agent orchestration
- **🔥 Gemini Models**: Powered by Google's Gemini 2.0 Flash for superior reasoning and analysis
- **🔍 No Pre-indexing Required**: Dynamically explores repositories using GitHub's API
- **👤 Author Attribution**: Identifies who wrote the problematic code and when
- **📊 High Accuracy**: Self-critique system ensures reliable results
- **🛠️ Production Ready**: Comprehensive error handling, logging, and configuration
- **📈 Multiple Output Formats**: JSON, Markdown, and console reports

## 🏗️ Architecture

The system consists of three main **intelligent AI agents** built with Google ADK:

1. **Root Cause Agent**: Investigates bugs using 12 specialized GitHub tools
2. **Critique Agent**: Reviews and validates findings for accuracy
3. **Orchestrator Agent**: **Intelligent coordinator** that decides when to call which agent and manages the refinement loop

### 🧠 Intelligent Orchestration

Unlike traditional static workflows, the **Orchestrator Agent** is an AI that:

- Decides when to run RCA analysis
- Determines if critique feedback requires rework
- Manages iteration loops intelligently
- Makes decisions based on confidence scores and feedback quality
- Continues refinement until critique agent approves OR max iterations reached

### Core Philosophy

**NO PRE-INDEXING. NO VECTOR DATABASES.**

The agents use GitHub's API and intelligent tool-calling to explore codebases on-demand. The LLM decides what to investigate based on the bug report and project structure.

## 📦 Installation

### Prerequisites

- Python 3.10 or higher
- GitHub Personal Access Token
- **Google Gemini API Key** (with ADK support)

### Setup

1. **Clone the repository**

```bash
git clone <repository-url>
cd root_cause_analyzer
```

2. **Install dependencies**

```bash
pip install -r requirements.txt
```

3. **Configure environment**

```bash
cp .env.example .env
# Edit .env with your API keys
```

4. **Set up API keys**

Edit `.env` file:

```env
GITHUB_TOKEN=your_github_personal_access_token_here
GEMINI_API_KEY=your_gemini_api_key_here
GEMINI_MODEL=gemini-2.0-flash-exp
```

## 🚀 Quick Start

### Command Line Usage

```bash
# Basic analysis
python main.py \
  --bug-report examples/bug_reports/login_bug.json \
  --repo owner/repository \
  --branch main

# With custom output
python main.py \
  --bug-report bug.json \
  --repo owner/repo \
  --output reports/analysis.json \
  --format both
```

### Programmatic Usage

```python
from core.github_client import GitHubClient
from agents.root_cause_agent import RootCauseAgent
from agents.critique_agent import CritiqueAgent
from agents.orchestrator_agent import OrchestratorAgent
from models.bug_report import BugReport

# Initialize GitHub client
github = GitHubClient(token, "owner/repo")

# Initialize ADK agents with Gemini
rca_agent = RootCauseAgent(github)
critique_agent = CritiqueAgent(github)
orchestrator = OrchestratorAgent(rca_agent, critique_agent)

# Load bug report
bug = BugReport.from_json_file("bug.json")

# Run intelligent analysis with orchestration
result = orchestrator.run_analysis(bug, max_refinement_iterations=3)

# Access results
print(f"Root cause: {result.root_cause.file_path}")
print(f"Author: {result.author_info.name}")
print(f"Commit: {result.commit_info.commit_sha}")
print(f"Critique approved: {result.critique_approved}")
```

## 📋 Bug Report Format

Create bug reports in JSON format:

```json
{
  "title": "Login fails with NoneType error",
  "description": "When attempting to login with a non-existent email...",
  "steps_to_reproduce": [
    "Navigate to /login",
    "Enter email: nonexistent@example.com",
    "Click 'Login' button"
  ],
  "expected_behavior": "Should show 'Invalid credentials' error",
  "actual_behavior": "Application crashes with 500 error",
  "error_message": "TypeError: 'NoneType' object has no attribute 'id'",
  "stack_trace": "Traceback (most recent call last):\n  File \"src/auth/login.py\"...",
  "environment": {
    "python_version": "3.10.5",
    "framework": "Flask 2.3.0"
  },
  "severity": "high"
}
```

## 🛠️ Available Tools

The system includes 12 specialized GitHub tools:

1. **Repository Structure** - Get project layout
2. **Code Search** - Find files by keywords
3. **File Content** - Read complete files
4. **Directory Listing** - Explore directories
5. **File History** - See recent changes
6. **File Blame** - Find who wrote each line
7. **Commit Details** - Get full commit information
8. **Dependencies** - Trace imports and usage
9. **File Search** - Search within files
10. **Line History** - Find when lines were added
11. **Recent Commits** - See repository activity
12. **Function Analysis** - Extract and analyze functions

## 📊 Output Formats

### Console Report

```
╔══════════════════════════════════════════════════════════════════════════════╗
║                           ROOT CAUSE ANALYSIS REPORT                        ║
╚══════════════════════════════════════════════════════════════════════════════╝

🐛 BUG: Login fails with NoneType error
📅 ANALYZED: 2024-01-15 14:30:22
🎯 CONFIDENCE: 85%
🔄 ITERATIONS: 8
✅ CRITIQUE: Approved
```

### JSON Report

```json
{
  "bug_report_title": "Login fails with NoneType error",
  "root_cause": {
    "file_path": "src/auth/login.py",
    "line_numbers": [45],
    "explanation": "The authenticate_user function..."
  },
  "commit_info": {
    "commit_sha": "a3f5b2c",
    "author": {
      "name": "John Doe",
      "email": "john@example.com"
    }
  }
}
```

### Markdown Report

Complete markdown report with all analysis details, commit information, and suggested fixes.

## ⚙️ Configuration

### Environment Variables

| Variable                    | Description                  | Default              |
| --------------------------- | ---------------------------- | -------------------- |
| `GITHUB_TOKEN`              | GitHub Personal Access Token | Required             |
| `GEMINI_API_KEY`            | Google Gemini API Key        | Required             |
| `GEMINI_MODEL`              | Gemini model to use          | gemini-2.0-flash-exp |
| `MAX_RCA_ITERATIONS`        | Maximum analysis iterations  | 15                   |
| `MAX_REFINEMENT_ITERATIONS` | Maximum critique iterations  | 2                    |
| `LOG_LEVEL`                 | Logging level                | INFO                 |

### Command Line Options

```bash
python main.py --help
```

- `--bug-report`: Path to bug report JSON file (required)
- `--repo`: GitHub repository in owner/repo format (required)
- `--branch`: Branch to analyze (default: main)
- `--output`: Output file path (default: analysis_report.json)
- `--format`: Output format - json, markdown, or both (default: both)
- `--max-iterations`: Maximum RCA iterations
- `--max-refinements`: Maximum refinement iterations
- `--no-critique`: Skip critique phase for faster analysis

## 🧪 Testing

### Quick Example

Run the example analysis:

```bash
python examples/sample_analysis.py
```

This will demonstrate the system using a sample bug report and public repository.

### Comprehensive End-to-End Testing

The system includes a comprehensive end-to-end test suite that validates the complete workflow using a real GitHub repository:

**Test Repository:** `Sampath808/Smart_Summarizer`  
**Bug Scenario:** YouTube video screenshots not visible in final report

#### Validate Test Setup

Before running tests, validate your environment:

```bash
python validate_test_setup.py
```

This checks Python version, dependencies, API keys, and connections.

#### Run Tests

```bash
# Quick tests (recommended for development)
python run_e2e_test.py --quick --verbose

# Full test suite (complete validation)
python run_e2e_test.py --full --verbose --save-logs

# Mocked tests (no API calls, good for CI/CD)
python run_e2e_test.py --mocked --verbose

# Manual test using main.py
python run_e2e_test.py --manual
```

#### Test Coverage

The end-to-end test validates:

- ✅ Bug report creation and validation
- ✅ GitHub client connection and operations
- ✅ Agent initialization (RCA, Critique, Orchestrator)
- ✅ Individual tool functionality
- ✅ Complete RCA analysis workflow
- ✅ Orchestrated analysis with critique
- ✅ Output generation (JSON, Markdown)
- ✅ Error handling scenarios
- ✅ Performance metrics validation

#### Direct pytest Usage

```bash
# Run all tests
pytest tests/test_end_to_end_real_repo.py -v -s

# Run quick tests only (skip slow analysis)
pytest tests/test_end_to_end_real_repo.py -v -s -m "not slow"

# Run specific test
pytest tests/test_end_to_end_real_repo.py::TestEndToEndRealRepo::test_01_bug_report_creation -v -s
```

See `TEST_DOCUMENTATION.md` for detailed testing information.

## 📁 Project Structure

```
root_cause_analyzer/
├── agents/                    # AI agents
│   ├── root_cause_agent.py   # Main RCA agent
│   ├── critique_agent.py     # Review agent
│   └── orchestrator_agent.py # Workflow coordinator
├── core/                     # Core functionality
│   ├── github_client.py      # GitHub API wrapper
│   └── code_analyzer.py      # Code parsing utilities
├── models/                   # Data models
│   ├── bug_report.py         # Bug report structure
│   ├── analysis_result.py    # Analysis results
│   └── commit_info.py        # Commit information
├── utils/                    # Utilities
│   ├── config.py             # Configuration management
│   ├── logger.py             # Logging setup
│   └── formatters.py         # Output formatting
├── examples/                 # Example usage
│   ├── sample_analysis.py    # Programmatic example
│   └── bug_reports/          # Sample bug reports
├── main.py                   # CLI entry point
└── requirements.txt          # Dependencies
```

## 🔧 Advanced Usage

### Custom Analysis Workflow

```python
# Initialize components
github_client = GitHubClient(token, repo, branch)
rca_agent = RootCauseAgent(gemini_key, github_client)
critique_agent = CritiqueAgent(gemini_key, github_client)

# Run analysis with custom parameters
result = rca_agent.analyze_bug(bug_report, max_iterations=20)

# Run critique
critique = critique_agent.critique(bug_report, result)

# Access detailed results
for tool_execution in rca_agent.tool_executions:
    print(f"Tool: {tool_execution.tool_name}")
    print(f"Time: {tool_execution.execution_time:.2f}s")
```

### Batch Analysis

```python
bug_reports = [
    BugReport.from_json_file("bug1.json"),
    BugReport.from_json_file("bug2.json"),
    BugReport.from_json_file("bug3.json")
]

results = []
for bug in bug_reports:
    result = orchestrator.run_analysis(bug)
    results.append(result)

# Generate summary statistics
from utils.formatters import create_summary_stats
stats = create_summary_stats(results)
print(f"Average confidence: {stats['average_confidence']:.2f}")
```

## 🚨 Error Handling

The system includes comprehensive error handling:

- **GitHub API Errors**: Rate limiting, authentication, repository access
- **LLM Errors**: API failures, token limits, malformed responses
- **File System Errors**: Missing files, permission issues
- **Network Errors**: Timeouts, connection failures

All errors are logged with appropriate detail levels and user-friendly messages.

## 🔒 Security Considerations

- API keys are never logged or exposed
- All file paths are validated to prevent path traversal
- Input sanitization prevents code injection
- No code execution from repository content

## 📈 Performance

- **Typical Analysis Time**: 2-5 minutes
- **API Calls**: 10-50 GitHub API calls per analysis
- **Memory Usage**: < 100MB for most repositories
- **Caching**: File content cached to reduce API calls

## 🤝 Contributing

1. Fork the repository
2. Create a feature branch
3. Add tests for new functionality
4. Ensure all tests pass
5. Submit a pull request

## 📄 License

This project is licensed under the MIT License - see the LICENSE file for details.

## 🆘 Support

For issues and questions:

1. Check the [Issues](../../issues) page
2. Review the [Documentation](DEVELOPMENT.md)
3. Create a new issue with detailed information

## 🎯 Success Criteria

The system successfully:

✅ Accepts any bug report from any repository  
✅ Intelligently explores codebases using LLM-guided tool calling  
✅ Identifies root causes with specific file paths and line numbers  
✅ Finds the commit that introduced the bug  
✅ Identifies the author responsible for the code  
✅ Self-critiques and refines analysis  
✅ Generates comprehensive reports in multiple formats  
✅ Completes analysis in under 5 minutes for typical bugs  
✅ Handles edge cases gracefully  
✅ Provides high confidence scores (>0.8 for clear bugs)

---

**Built with ❤️ for developers who want to understand their code better.**
