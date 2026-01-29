from dataclasses import dataclass
from typing import List, Optional
from datetime import datetime

@dataclass
class AuthorInfo:
    """Information about code author"""
    name: str
    email: str
    github_username: Optional[str] = None
    total_commits_to_repo: Optional[int] = None
    recent_commits_to_file: Optional[int] = None

@dataclass
class CommitInfo:
    """Detailed commit information"""
    commit_sha: str
    short_sha: str
    commit_message: str
    commit_date: datetime
    commit_url: str
    author: AuthorInfo
    files_changed: List[str]
    additions: int
    deletions: int
    patch: Optional[str] = None  # Actual code diff

    def to_dict(self) -> dict:
        """Convert to dictionary"""
        return {
            'commit_sha': self.commit_sha,
            'short_sha': self.short_sha,
            'commit_message': self.commit_message,
            'commit_date': self.commit_date.isoformat(),
            'commit_url': self.commit_url,
            'author': {
                'name': self.author.name,
                'email': self.author.email,
                'github_username': self.author.github_username,
                'total_commits_to_repo': self.author.total_commits_to_repo,
                'recent_commits_to_file': self.author.recent_commits_to_file
            },
            'files_changed': self.files_changed,
            'additions': self.additions,
            'deletions': self.deletions,
            'patch': self.patch
        }

@dataclass
class FileBlameInfo:
    """Git blame information for specific lines"""
    file_path: str
    line_number: int
    line_content: str
    commit_sha: str
    author_name: str
    author_email: str
    commit_date: datetime
    commit_message: str