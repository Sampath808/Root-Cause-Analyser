"""Tests for GitHub client functionality."""

import pytest
import json
from unittest.mock import Mock, patch, MagicMock
import sys
from pathlib import Path

# Add parent directory to path for imports
sys.path.append(str(Path(__file__).parent.parent))

from core.github_client import GitHubClient

class TestGitHubClient:
    """Test cases for GitHubClient class."""
    
    @pytest.fixture
    def mock_github(self):
        """Create a mock GitHub instance."""
        with patch('core.github_client.Github') as mock:
            yield mock
    
    @pytest.fixture
    def github_client(self, mock_github):
        """Create a GitHubClient instance with mocked GitHub."""
        return GitHubClient("fake_token", "owner/repo", "main")
    
    def test_initialization(self, mock_github, github_client):
        """Test GitHubClient initialization."""
        assert github_client.branch == "main"
        assert github_client._file_cache == {}
        mock_github.assert_called_once_with("fake_token")
    
    def test_get_file_content_success(self, github_client):
        """Test successful file content retrieval."""
        # Setup mock
        mock_content = Mock()
        mock_content.decoded_content = b"print('hello world')"
        github_client.repo.get_contents.return_value = mock_content
        
        # Test
        result = github_client.get_file_content("test.py")
        
        # Assert
        assert result == "print('hello world')"
        assert "test.py" in github_client._file_cache
        github_client.repo.get_contents.assert_called_once_with("test.py", ref="main")
    
    def test_get_file_content_cached(self, github_client):
        """Test file content retrieval from cache."""
        # Setup cache
        github_client._file_cache["test.py"] = "cached content"
        
        # Test
        result = github_client.get_file_content("test.py")
        
        # Assert
        assert result == "cached content"
        github_client.repo.get_contents.assert_not_called()
    
    def test_get_file_content_error(self, github_client):
        """Test file content retrieval error handling."""
        # Setup mock to raise exception
        github_client.repo.get_contents.side_effect = Exception("File not found")
        
        # Test
        result = github_client.get_file_content("nonexistent.py")
        
        # Assert
        assert result.startswith("ERROR:")
        assert "File not found" in result
    
    def test_get_repository_structure(self, github_client):
        """Test repository structure retrieval."""
        # Setup mock contents
        mock_file = Mock()
        mock_file.type = 'file'
        mock_file.name = 'README.md'
        mock_file.path = 'README.md'
        mock_file.size = 1234
        
        mock_dir = Mock()
        mock_dir.type = 'dir'
        mock_dir.name = 'src'
        mock_dir.path = 'src'
        
        github_client.repo.get_contents.return_value = [mock_file, mock_dir]
        
        # Test
        result = github_client.get_repository_structure(max_depth=1)
        
        # Assert
        result_dict = json.loads(result)
        assert 'README.md' in result_dict
        assert 'src/' in result_dict
        assert result_dict['README.md']['type'] == 'file'
        assert result_dict['src/']['type'] == 'directory'
    
    def test_search_code(self, github_client):
        """Test code search functionality."""
        # Setup mock files
        mock_file1 = Mock()
        mock_file1.path = 'src/auth/login.py'
        mock_file1.size = 500
        
        mock_file2 = Mock()
        mock_file2.path = 'tests/test_auth.py'
        mock_file2.size = 300
        
        github_client._get_all_files = Mock(return_value=[mock_file1, mock_file2])
        github_client.get_file_content = Mock(side_effect=[
            "def login_user():\n    pass",
            "def test_login():\n    pass"
        ])
        
        # Test
        result = github_client.search_code("login")
        
        # Assert
        result_list = json.loads(result)
        assert len(result_list) == 2
        assert any('login.py' in match['path'] for match in result_list)
    
    def test_get_directory_files(self, github_client):
        """Test directory file listing."""
        # Setup mock
        mock_file = Mock()
        mock_file.name = 'app.py'
        mock_file.path = 'src/app.py'
        mock_file.type = 'file'
        mock_file.size = 1000
        
        github_client.repo.get_contents.return_value = [mock_file]
        
        # Test
        result = github_client.get_directory_files("src")
        
        # Assert
        result_list = json.loads(result)
        assert len(result_list) == 1
        assert result_list[0]['name'] == 'app.py'
        assert result_list[0]['type'] == 'file'
    
    def test_get_file_history(self, github_client):
        """Test file history retrieval."""
        # Setup mock commit
        mock_commit = Mock()
        mock_commit.sha = 'abc123def456'
        mock_commit.commit.message = 'Fix login bug'
        mock_commit.commit.author.name = 'John Doe'
        mock_commit.commit.author.email = 'john@example.com'
        mock_commit.commit.author.date = Mock()
        mock_commit.commit.author.date.isoformat.return_value = '2024-01-15T10:30:00'
        mock_commit.html_url = 'https://github.com/owner/repo/commit/abc123'
        
        github_client.repo.get_commits.return_value = [mock_commit]
        
        # Test
        result = github_client.get_file_history("src/auth/login.py", limit=5)
        
        # Assert
        result_list = json.loads(result)
        assert len(result_list) == 1
        assert result_list[0]['sha'] == 'abc123def456'
        assert result_list[0]['short_sha'] == 'abc123d'
        assert result_list[0]['message'] == 'Fix login bug'
        assert result_list[0]['author'] == 'John Doe'
    
    def test_get_commit_details(self, github_client):
        """Test commit details retrieval."""
        # Setup mock commit
        mock_commit = Mock()
        mock_commit.sha = 'abc123def456'
        mock_commit.commit.message = 'Fix authentication bug'
        mock_commit.commit.author.name = 'Jane Smith'
        mock_commit.commit.author.email = 'jane@example.com'
        mock_commit.commit.author.date.isoformat.return_value = '2024-01-15T14:20:00'
        mock_commit.commit.committer.name = 'Jane Smith'
        mock_commit.commit.committer.email = 'jane@example.com'
        mock_commit.commit.committer.date.isoformat.return_value = '2024-01-15T14:20:00'
        mock_commit.stats.additions = 10
        mock_commit.stats.deletions = 5
        mock_commit.stats.total = 15
        mock_commit.html_url = 'https://github.com/owner/repo/commit/abc123'
        
        # Mock file changes
        mock_file = Mock()
        mock_file.filename = 'src/auth/login.py'
        mock_file.status = 'modified'
        mock_file.additions = 8
        mock_file.deletions = 3
        mock_file.changes = 11
        mock_file.patch = '@@ -10,3 +10,8 @@ def login():\n+    if not user:\n+        return None'
        
        mock_commit.files = [mock_file]
        github_client.repo.get_commit.return_value = mock_commit
        
        # Test
        result = github_client.get_commit_details("abc123")
        
        # Assert
        result_dict = json.loads(result)
        assert result_dict['sha'] == 'abc123def456'
        assert result_dict['short_sha'] == 'abc123d'
        assert result_dict['message'] == 'Fix authentication bug'
        assert result_dict['author']['name'] == 'Jane Smith'
        assert len(result_dict['files_changed']) == 1
        assert result_dict['files_changed'][0]['filename'] == 'src/auth/login.py'
    
    def test_search_in_file(self, github_client):
        """Test searching within a file."""
        # Setup mock file content
        file_content = """def login_user(email, password):
    user = find_user(email)
    if not user:
        return None
    if verify_password(user, password):
        return user.id
    return None"""
        
        github_client.get_file_content = Mock(return_value=file_content)
        
        # Test
        result = github_client.search_in_file("src/auth/login.py", "user")
        
        # Assert
        result_dict = json.loads(result)
        assert result_dict['file'] == 'src/auth/login.py'
        assert result_dict['search_term'] == 'user'
        assert result_dict['total_matches'] == 5  # 'user' appears 5 times (login_user, find_user, user var, user check, user.id)
        assert len(result_dict['matches']) == 5
    
    def test_find_when_line_was_added(self, github_client):
        """Test finding when specific lines were added."""
        # Setup mock commit with patch
        mock_commit = Mock()
        mock_commit.sha = 'abc123def456'
        mock_commit.commit.author.name = 'John Doe'
        mock_commit.commit.author.email = 'john@example.com'
        mock_commit.commit.author.date.isoformat.return_value = '2024-01-15T10:30:00'
        mock_commit.commit.message = 'Add user validation'
        mock_commit.html_url = 'https://github.com/owner/repo/commit/abc123'
        
        # Mock file with patch
        mock_file = Mock()
        mock_file.filename = 'src/auth/login.py'
        mock_file.patch = '@@ -40,0 +41,3 @@ def authenticate_user():\n+    if not user:\n+        return None\n+    return user.id'
        
        mock_commit.files = [mock_file]
        github_client.repo.get_commits.return_value = [mock_commit]
        github_client._line_in_patch = Mock(return_value=True)
        
        # Test
        result = github_client.find_when_line_was_added("src/auth/login.py", [42, 43])
        
        # Assert
        result_dict = json.loads(result)
        assert '42' in result_dict
        assert '43' in result_dict
        assert result_dict['42']['commit_sha'] == 'abc123d'
        assert result_dict['42']['author'] == 'John Doe'
    
    def test_error_handling(self, github_client):
        """Test error handling in various methods."""
        # Test repository structure error
        github_client.repo.get_contents.side_effect = Exception("API Error")
        
        result = github_client.get_repository_structure()
        result_dict = json.loads(result)
        assert 'error' in result_dict
        
        # Test search code error
        github_client._get_all_files = Mock(side_effect=Exception("Search Error"))
        
        result = github_client.search_code("test")
        result_dict = json.loads(result)
        assert 'error' in result_dict

if __name__ == '__main__':
    pytest.main([__file__])