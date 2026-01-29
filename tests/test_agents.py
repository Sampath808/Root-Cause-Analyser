"""Tests for agent functionality."""

import pytest
from unittest.mock import Mock, patch, MagicMock
import sys
from pathlib import Path
from datetime import datetime

# Add parent directory to path for imports
sys.path.append(str(Path(__file__).parent.parent))

from agents.root_cause_agent import RootCauseAgent
from agents.critique_agent import CritiqueAgent
from agents.orchestrator_agent import OrchestratorAgent
from models.bug_report import BugReport
from models.analysis_result import AnalysisResult, RootCause
from core.github_client import GitHubClient

class TestRootCauseAgent:
    """Test cases for RootCauseAgent class."""
    
    @pytest.fixture
    def mock_github_client(self):
        """Create a mock GitHub client."""
        return Mock(spec=GitHubClient)
    
    @pytest.fixture
    def mock_genai(self):
        """Mock the Google Generative AI module."""
        with patch('agents.root_cause_agent.genai') as mock:
            yield mock
    
    @pytest.fixture
    def rca_agent(self, mock_genai, mock_github_client):
        """Create a RootCauseAgent instance with mocks."""
        return RootCauseAgent("fake_api_key", mock_github_client)
    
    @pytest.fixture
    def sample_bug_report(self):
        """Create a sample bug report for testing."""
        return BugReport(
            title="Login fails with NoneType error",
            description="Authentication fails when user doesn't exist",
            steps_to_reproduce=["Go to login", "Enter invalid email", "Click login"],
            expected_behavior="Show error message",
            actual_behavior="Application crashes",
            error_message="TypeError: 'NoneType' object has no attribute 'id'",
            stack_trace="File 'login.py', line 45, in authenticate_user\n    return user.id"
        )
    
    def test_initialization(self, mock_genai, mock_github_client):
        """Test RootCauseAgent initialization."""
        agent = RootCauseAgent("test_key", mock_github_client)
        
        assert agent.github == mock_github_client
        assert agent.conversation_history == []
        assert agent.tool_executions == []
        mock_genai.Client.assert_called_once_with(api_key="test_key")
    
    def test_create_adk_tools(self, rca_agent):
        """Test ADK tool configuration creation."""
        tools = rca_agent._create_adk_tools()
        
        assert len(tools) == 1  # Should have 1 Tool object
        assert len(tools[0].function_declarations) == 11  # Should have 11 function declarations
        
        function_names = [func.name for func in tools[0].function_declarations]
        
        expected_tools = [
            'get_repository_structure',
            'search_code',
            'get_file_content',
            'get_directory_files',
            'get_file_history',
            'get_file_blame',
            'get_commit_details',
            'find_file_dependencies',
            'search_in_file',
            'find_when_line_was_added',
            'get_recent_commits'
        ]
        
        for expected_tool in expected_tools:
            assert expected_tool in function_names
    
    def test_execute_tool_get_file_content(self, rca_agent):
        """Test tool execution for get_file_content."""
        # Setup mock
        rca_agent.github.get_file_content.return_value = "print('hello')"
        
        # Test
        result = rca_agent._execute_tool('get_file_content', {'file_path': 'test.py'})
        
        # Assert
        assert result == "print('hello')"
        rca_agent.github.get_file_content.assert_called_once_with('test.py')
    
    def test_execute_tool_search_code(self, rca_agent):
        """Test tool execution for search_code."""
        # Setup mock
        rca_agent.github.search_code.return_value = '{"matches": []}'
        
        # Test
        result = rca_agent._execute_tool('search_code', {'query': 'login'})
        
        # Assert
        assert result == '{"matches": []}'
        rca_agent.github.search_code.assert_called_once_with('login')
    
    def test_execute_tool_unknown(self, rca_agent):
        """Test tool execution with unknown tool."""
        result = rca_agent._execute_tool('unknown_tool', {})
        
        assert 'error' in result
        assert 'Unknown tool' in result
    
    def test_execute_tool_exception(self, rca_agent):
        """Test tool execution with exception."""
        # Setup mock to raise exception
        rca_agent.github.get_file_content.side_effect = Exception("API Error")
        
        # Test
        result = rca_agent._execute_tool('get_file_content', {'file_path': 'test.py'})
        
        # Assert
        assert 'error' in result
        assert 'API Error' in result
    
    def test_create_analysis_prompt(self, rca_agent, sample_bug_report):
        """Test analysis prompt creation."""
        prompt_content = rca_agent._create_analysis_prompt(sample_bug_report)
        
        # Check that it returns a types.Content object
        assert hasattr(prompt_content, 'role')
        assert hasattr(prompt_content, 'parts')
        assert prompt_content.role == "user"
        
        # Check that the prompt text contains expected content
        prompt_text = prompt_content.parts[0].text
        assert sample_bug_report.title in prompt_text
        assert sample_bug_report.description in prompt_text
        assert sample_bug_report.error_message in prompt_text
        assert "YOUR INVESTIGATION WORKFLOW" in prompt_text
        assert "Start your investigation now!" in prompt_text
    
    def test_create_incomplete_result(self, rca_agent, sample_bug_report):
        """Test creation of incomplete analysis result."""
        result = rca_agent._create_incomplete_result(sample_bug_report, 5)
        
        assert isinstance(result, AnalysisResult)
        assert result.bug_report_title == sample_bug_report.title
        assert result.iterations == 5
        assert result.confidence_score == 0.0
        assert "incomplete" in result.root_cause.explanation.lower()

class TestCritiqueAgent:
    """Test cases for CritiqueAgent class."""
    
    @pytest.fixture
    def mock_github_client(self):
        """Create a mock GitHub client."""
        return Mock(spec=GitHubClient)
    
    @pytest.fixture
    def mock_genai(self):
        """Mock the Google Generative AI module."""
        with patch('agents.critique_agent.genai') as mock:
            yield mock
    
    @pytest.fixture
    def critique_agent(self, mock_genai, mock_github_client):
        """Create a CritiqueAgent instance with mocks."""
        return CritiqueAgent("fake_api_key", mock_github_client)
    
    @pytest.fixture
    def sample_analysis_result(self):
        """Create a sample analysis result for testing."""
        return AnalysisResult(
            bug_report_title="Test Bug",
            root_cause=RootCause(
                file_path="src/auth/login.py",
                line_numbers=[45],
                code_snippet="return user.id",
                explanation="User is None when not found"
            ),
            commit_info=None,
            author_info=None,
            verification_steps=[],
            suggested_fix=None,
            confidence_score=0.8,
            tools_used=["get_file_content"],
            iterations=5,
            analysis_timestamp=datetime.now()
        )
    
    def test_initialization(self, mock_genai, mock_github_client):
        """Test CritiqueAgent initialization."""
        agent = CritiqueAgent("test_key", mock_github_client)
        
        assert agent.github == mock_github_client
        mock_genai.Client.assert_called_once_with(api_key="test_key")
    
    def test_critique_basic(self, critique_agent, sample_analysis_result):
        """Test basic critique functionality."""
        # Setup mock LLM response
        mock_response = Mock()
        mock_response.text = "Analysis looks good. Approved."
        critique_agent.client.models.generate_content.return_value = mock_response
        
        # Create sample bug report
        bug_report = BugReport(
            title="Test Bug",
            description="Test description",
            steps_to_reproduce=["Step 1"],
            expected_behavior="Expected",
            actual_behavior="Actual"
        )
        
        # Test
        result = critique_agent.critique(bug_report, sample_analysis_result)
        
        # Assert
        assert isinstance(result, dict)
        assert 'approved' in result
        assert 'confidence_adjustment' in result
        assert 'comments' in result
        assert 'suggested_improvements' in result

class TestOrchestratorAgent:
    """Test cases for OrchestratorAgent class."""
    
    @pytest.fixture
    def mock_rca_agent(self):
        """Create a mock RCA agent."""
        return Mock(spec=RootCauseAgent)
    
    @pytest.fixture
    def mock_critique_agent(self):
        """Create a mock Critique agent."""
        return Mock(spec=CritiqueAgent)
    
    @pytest.fixture
    def orchestrator(self, mock_rca_agent, mock_critique_agent):
        """Create an OrchestratorAgent instance with mocks."""
        return OrchestratorAgent(mock_rca_agent, mock_critique_agent)
    
    @pytest.fixture
    def sample_bug_report(self):
        """Create a sample bug report for testing."""
        return BugReport(
            title="Test Bug",
            description="Test description",
            steps_to_reproduce=["Step 1"],
            expected_behavior="Expected",
            actual_behavior="Actual"
        )
    
    @pytest.fixture
    def sample_analysis_result(self):
        """Create a sample analysis result for testing."""
        return AnalysisResult(
            bug_report_title="Test Bug",
            root_cause=RootCause(
                file_path="test.py",
                line_numbers=[10],
                code_snippet="test code",
                explanation="Test explanation"
            ),
            commit_info=None,
            author_info=None,
            verification_steps=[],
            suggested_fix=None,
            confidence_score=0.8,
            tools_used=["test_tool"],
            iterations=3,
            analysis_timestamp=datetime.now()
        )
    
    def test_initialization(self, mock_rca_agent, mock_critique_agent):
        """Test OrchestratorAgent initialization."""
        orchestrator = OrchestratorAgent(mock_rca_agent, mock_critique_agent)
        
        assert orchestrator.rca_agent == mock_rca_agent
        assert orchestrator.critique_agent == mock_critique_agent
    
    def test_run_analysis_approved(self, orchestrator, sample_bug_report, sample_analysis_result):
        """Test analysis workflow with approved critique."""
        # Setup mocks
        orchestrator.rca_agent.analyze_bug.return_value = sample_analysis_result
        orchestrator.critique_agent.critique.return_value = {
            'approved': True,
            'confidence_adjustment': 0.1,
            'comments': 'Good analysis',
            'suggested_improvements': []
        }
        
        # Test
        result = orchestrator.run_analysis(sample_bug_report, max_refinement_iterations=1)
        
        # Assert
        assert isinstance(result, AnalysisResult)
        assert result.critique_approved == True
        assert result.critique_comments == 'Good analysis'
        assert result.confidence_score == 0.9  # 0.8 + 0.1 adjustment
        
        orchestrator.rca_agent.analyze_bug.assert_called_once_with(sample_bug_report)
        orchestrator.critique_agent.critique.assert_called_once()
    
    def test_run_analysis_not_approved(self, orchestrator, sample_bug_report, sample_analysis_result):
        """Test analysis workflow with rejected critique."""
        # Setup mocks
        orchestrator.rca_agent.analyze_bug.return_value = sample_analysis_result
        orchestrator.critique_agent.critique.return_value = {
            'approved': False,
            'confidence_adjustment': -0.2,
            'comments': 'Needs improvement',
            'suggested_improvements': ['Check more files']
        }
        
        # Test
        result = orchestrator.run_analysis(sample_bug_report, max_refinement_iterations=1)
        
        # Assert
        assert isinstance(result, AnalysisResult)
        assert result.critique_approved == False
        
        orchestrator.rca_agent.analyze_bug.assert_called_once_with(sample_bug_report)
        orchestrator.critique_agent.critique.assert_called_once()
    
    def test_run_analysis_multiple_iterations(self, orchestrator, sample_bug_report, sample_analysis_result):
        """Test analysis workflow with multiple refinement iterations."""
        # Setup mocks - first critique fails, second approves
        orchestrator.rca_agent.analyze_bug.return_value = sample_analysis_result
        orchestrator.critique_agent.critique.side_effect = [
            {
                'approved': False,
                'confidence_adjustment': 0.0,
                'comments': 'First rejection',
                'suggested_improvements': []
            },
            {
                'approved': True,
                'confidence_adjustment': 0.1,
                'comments': 'Second approval',
                'suggested_improvements': []
            }
        ]
        
        # Test
        result = orchestrator.run_analysis(sample_bug_report, max_refinement_iterations=2)
        
        # Assert
        assert isinstance(result, AnalysisResult)
        assert result.critique_approved == True
        assert result.critique_comments == 'Second approval'
        
        orchestrator.rca_agent.analyze_bug.assert_called_once_with(sample_bug_report)
        assert orchestrator.critique_agent.critique.call_count == 2

if __name__ == '__main__':
    pytest.main([__file__])