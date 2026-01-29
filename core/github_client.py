from github import Github
from typing import List, Dict, Optional
import json
import re
from datetime import datetime

class GitHubClient:
    """Comprehensive GitHub client exposing all repository operations as tools.
    Each method should be designed to return JSON-serializable results."""

    def __init__(self, access_token: str, repo_full_name: str, branch: str = 'main'):
        """Initialize GitHub client
        
        Args:
            access_token: GitHub personal access token
            repo_full_name: Format "owner/repo-name"
            branch: Branch to analyze (default: main)
        """
        self.g = Github(access_token)
        self.repo = self.g.get_repo(repo_full_name)
        self.branch = branch
        self._file_cache = {}  # Cache for file contents

    # ============================================================
    # TOOL 1: Repository Structure
    # ============================================================
    def get_repository_structure(self, max_depth: int = 3, path: str = '') -> str:
        """Get hierarchical directory structure of the repository.
        
        Returns: JSON string with tree structure
        Example output:
        {
            "src/": {
                "type": "directory",
                "children": {
                    "auth/": {...},
                    "models/": {...}
                }
            },
            "README.md": {
                "type": "file",
                "size": 1234
            }
        }
        """
        def build_tree(current_path: str = '', depth: int = 0) -> dict:
            if depth >= max_depth:
                return {}
            
            try:
                contents = self.repo.get_contents(current_path, ref=self.branch)
                if not isinstance(contents, list):
                    contents = [contents]
                
                structure = {}
                for content in contents:
                    if content.type == 'dir':
                        structure[content.name + '/'] = {
                            'type': 'directory',
                            'path': content.path,
                            'children': build_tree(content.path, depth + 1)
                        }
                    else:
                        structure[content.name] = {
                            'type': 'file',
                            'path': content.path,
                            'size': content.size,
                            'extension': content.name.split('.')[-1] if '.' in content.name else None
                        }
                return structure
            except Exception as e:
                return {'error': str(e)}
        
        result = build_tree(path)
        return json.dumps(result, indent=2)

    # ============================================================
    # TOOL 2: Code Search
    # ============================================================
    def search_code(self, query: str, max_results: int = 20) -> str:
        """Search for code in the repository.
        Searches both filenames and file contents.
        
        Args:
            query: Search query (keywords, error messages, function names)
            max_results: Maximum number of results to return
            
        Returns: JSON string with matching files
        """
        matches = []
        query_lower = query.lower()
        
        try:
            # Get all files
            all_files = self._get_all_files()
            
            # Search in filenames
            for file in all_files:
                score = 0
                match_type = []
                
                # Filename match
                if query_lower in file.path.lower():
                    score += 10
                    match_type.append('filename')
                
                # For code files, search content (limited to avoid rate limits)
                if file.path.endswith(('.py', '.js', '.java', '.cpp', '.go', '.rb', '.ts')):
                    try:
                        content = self.get_file_content(file.path)
                        if query_lower in content.lower():
                            score += 20
                            match_type.append('content')
                            
                            # Find line numbers where query appears
                            lines = content.split('\n')
                            matching_lines = [i + 1 for i, line in enumerate(lines) 
                                            if query_lower in line.lower()]
                            
                            if matching_lines:
                                matches.append({
                                    'path': file.path,
                                    'score': score,
                                    'match_type': match_type,
                                    'matching_lines': matching_lines[:5],  # First 5 matches
                                    'size': file.size
                                })
                    except:
                        pass  # Skip files that can't be read
                elif score > 0:
                    matches.append({
                        'path': file.path,
                        'score': score,
                        'match_type': match_type,
                        'size': file.size
                    })
            
            # Sort by score
            matches.sort(key=lambda x: x['score'], reverse=True)
            return json.dumps(matches[:max_results], indent=2)
            
        except Exception as e:
            return json.dumps({'error': str(e)})

    # ============================================================
    # TOOL 3: Get File Content
    # ============================================================
    def get_file_content(self, file_path: str) -> str:
        """Fetch the complete content of a specific file.
        Uses caching to avoid repeated API calls.
        
        Args:
            file_path: Path to file (e.g., "src/auth/login.py")
            
        Returns: File content as string
        """
        # Check cache first
        if file_path in self._file_cache:
            return self._file_cache[file_path]
        
        try:
            content = self.repo.get_contents(file_path, ref=self.branch)
            decoded = content.decoded_content.decode('utf-8')
            self._file_cache[file_path] = decoded
            return decoded
        except Exception as e:
            return f"ERROR: Could not read file '{file_path}': {str(e)}"
    # ============================================================
    # TOOL 4: Get Directory Files
    # ============================================================
    def get_directory_files(self, directory_path: str = '') -> str:
        """List all files in a specific directory (non-recursive).
        
        Returns: JSON string with file list
        """
        try:
            contents = self.repo.get_contents(directory_path, ref=self.branch)
            if not isinstance(contents, list):
                contents = [contents]
            
            files = []
            for item in contents:
                files.append({
                    'name': item.name,
                    'path': item.path,
                    'type': item.type,
                    'size': item.size if item.type == 'file' else None
                })
            
            return json.dumps(files, indent=2)
        except Exception as e:
            return json.dumps({'error': str(e)})

    # ============================================================
    # TOOL 5: Get File History
    # ============================================================
    def get_file_history(self, file_path: str, limit: int = 10) -> str:
        """Get commit history for a specific file.
        
        Returns: JSON string with commit list
        """
        try:
            commits = self.repo.get_commits(path=file_path, sha=self.branch)
            history = []
            
            for commit in list(commits)[:limit]:
                history.append({
                    'sha': commit.sha,
                    'short_sha': commit.sha[:7],
                    'message': commit.commit.message,
                    'author': commit.commit.author.name,
                    'author_email': commit.commit.author.email,
                    'date': commit.commit.author.date.isoformat(),
                    'url': commit.html_url
                })
            
            return json.dumps(history, indent=2)
        except Exception as e:
            return json.dumps({'error': str(e)})

    # ============================================================
    # TOOL 6: Get File Blame (WHO wrote WHAT)
    # ============================================================
    def get_file_blame(self, file_path: str, line_start: Optional[int] = None, 
                      line_end: Optional[int] = None) -> str:
        """Get git blame information showing who wrote each line.
        
        Args:
            file_path: Path to file
            line_start: Optional start line number
            line_end: Optional end line number
            
        Returns: JSON string with blame information per line
        """
        try:
            # Get file content
            content = self.get_file_content(file_path)
            if content.startswith('ERROR'):
                return json.dumps({'error': content})
            
            lines = content.split('\n')
            
            # Get commits that touched this file
            commits = list(self.repo.get_commits(path=file_path, sha=self.branch))
            
            blame_data = []
            for idx, line in enumerate(lines, 1):
                # Filter by line range if specified
                if line_start and line_end:
                    if not (line_start <= idx <= line_end):
                        continue
                
                # Find which commit last modified this line
                # (Simplified - real implementation would use git blame API)
                line_commit = self._find_line_commit(file_path, idx, commits)
                
                blame_data.append({
                    'line_number': idx,
                    'line_content': line,
                    'commit_sha': line_commit['sha'],
                    'author': line_commit['author'],
                    'author_email': line_commit['email'],
                    'date': line_commit['date'],
                    'commit_message': line_commit['message']
                })
            
            return json.dumps(blame_data, indent=2)
        except Exception as e:
            return json.dumps({'error': str(e)})

    # ============================================================
    # TOOL 7: Get Commit Details
    # ============================================================
    def get_commit_details(self, commit_sha: str) -> str:
        """Get comprehensive information about a specific commit.
        
        Returns: JSON string with commit details including diff
        """
        try:
            commit = self.repo.get_commit(commit_sha)
            
            details = {
                'sha': commit.sha,
                'short_sha': commit.sha[:7],
                'message': commit.commit.message,
                'author': {
                    'name': commit.commit.author.name,
                    'email': commit.commit.author.email,
                    'date': commit.commit.author.date.isoformat()
                },
                'committer': {
                    'name': commit.commit.committer.name,
                    'email': commit.commit.committer.email,
                    'date': commit.commit.committer.date.isoformat()
                },
                'stats': {
                    'additions': commit.stats.additions,
                    'deletions': commit.stats.deletions,
                    'total': commit.stats.total
                },
                'files_changed': [],
                'url': commit.html_url
            }
            
            # Get files changed with diffs
            for file in commit.files:
                file_info = {
                    'filename': file.filename,
                    'status': file.status,
                    'additions': file.additions,
                    'deletions': file.deletions,
                    'changes': file.changes
                }
                
                # Include patch (diff) if available
                if hasattr(file, 'patch') and file.patch:
                    file_info['patch'] = file.patch
                
                details['files_changed'].append(file_info)
            
            return json.dumps(details, indent=2)
        except Exception as e:
            return json.dumps({'error': str(e)})

    # ============================================================
    # TOOL 8: Find File Dependencies
    # ============================================================
    def find_file_dependencies(self, file_path: str) -> str:
        """Find what this file imports and what files import this file.
        
        Returns: JSON string with dependencies
        """
        try:
            content = self.get_file_content(file_path)
            if content.startswith('ERROR'):
                return json.dumps({'error': content})
            
            # Parse imports (Python example - extend for other languages)
            imports = self._parse_imports(content, file_path)
            
            # Find files that import this file
            importers = self._find_importers(file_path)
            
            return json.dumps({
                'file': file_path,
                'imports': imports,
                'imported_by': importers
            }, indent=2)
        except Exception as e:
            return json.dumps({'error': str(e)})

    # ============================================================
    # TOOL 9: Search in File
    # ============================================================
    def search_in_file(self, file_path: str, search_term: str) -> str:
        """Search for specific text within a file and return matching lines.
        
        Returns: JSON string with matching lines and context
        """
        try:
            content = self.get_file_content(file_path)
            if content.startswith('ERROR'):
                return json.dumps({'error': content})
            
            lines = content.split('\n')
            matches = []
            
            for idx, line in enumerate(lines, 1):
                if search_term.lower() in line.lower():
                    # Include context (2 lines before and after)
                    context_start = max(0, idx - 3)
                    context_end = min(len(lines), idx + 2)
                    
                    matches.append({
                        'line_number': idx,
                        'line': line,
                        'context': {
                            'before': lines[context_start:idx-1],
                            'after': lines[idx:context_end]
                        }
                    })
            
            return json.dumps({
                'file': file_path,
                'search_term': search_term,
                'matches': matches,
                'total_matches': len(matches)
            }, indent=2)
        except Exception as e:
            return json.dumps({'error': str(e)})

    # ============================================================
    # TOOL 10: Get Recent Commits
    # ============================================================
    def get_recent_commits(self, limit: int = 20, since_date: Optional[str] = None) -> str:
        """Get recent commits to the entire repository.
        
        Args:
            limit: Number of commits
            since_date: ISO date string (e.g., "2024-01-01")
            
        Returns: JSON string with commit list
        """
        try:
            kwargs = {'sha': self.branch}
            if since_date:
                kwargs['since'] = datetime.fromisoformat(since_date)
            
            commits = self.repo.get_commits(**kwargs)
            commit_list = []
            
            for commit in list(commits)[:limit]:
                commit_list.append({
                    'sha': commit.sha[:7],
                    'message': commit.commit.message,
                    'author': commit.commit.author.name,
                    'date': commit.commit.author.date.isoformat(),
                    'files_changed': len(commit.files),
                    'url': commit.html_url
                })
            
            return json.dumps(commit_list, indent=2)
        except Exception as e:
            return json.dumps({'error': str(e)})

    # ============================================================
    # TOOL 11: Find When Line Was Added
    # ============================================================
    def find_when_line_was_added(self, file_path: str, line_numbers: List[int]) -> str:
        """Find the exact commit that introduced specific lines of code.
        
        Args:
            file_path: Path to file
            line_numbers: List of line numbers to investigate
            
        Returns: JSON string mapping line numbers to commits
        """
        try:
            commits = list(self.repo.get_commits(path=file_path, sha=self.branch))
            results = {}
            
            for line_num in line_numbers:
                # Go through commits from newest to oldest
                for commit in commits:
                    for file in commit.files:
                        if file.filename == file_path and hasattr(file, 'patch'):
                            # Check if this line was added/modified in this commit
                            if self._line_in_patch(file.patch, line_num):
                                results[str(line_num)] = {
                                    'commit_sha': commit.sha[:7],
                                    'full_sha': commit.sha,
                                    'author': commit.commit.author.name,
                                    'author_email': commit.commit.author.email,
                                    'date': commit.commit.author.date.isoformat(),
                                    'message': commit.commit.message,
                                    'url': commit.html_url
                                }
                                break
                    if str(line_num) in results:
                        break
            
            return json.dumps(results, indent=2)
        except Exception as e:
            return json.dumps({'error': str(e)})

    # ============================================================
    # TOOL 12: Analyze Function
    # ============================================================
    def analyze_function(self, file_path: str, function_name: str) -> str:
        """Extract and analyze a specific function from a file.
        
        Returns: JSON string with function details
        """
        try:
            content = self.get_file_content(file_path)
            if content.startswith('ERROR'):
                return json.dumps({'error': content})
            
            # Use AST parsing (implement in code_analyzer.py)
            from .code_analyzer import extract_function
            function_info = extract_function(content, function_name, file_path)
            return json.dumps(function_info, indent=2)
        except Exception as e:
            return json.dumps({'error': str(e)})

    # ============================================================
    # Helper Methods (Private)
    # ============================================================
    def _get_all_files(self, path: str = ''):
        """Recursively get all files in repository"""
        contents = self.repo.get_contents(path, ref=self.branch)
        files = []
        
        if not isinstance(contents, list):
            contents = [contents]
        
        for content in contents:
            if content.type == 'dir':
                files.extend(self._get_all_files(content.path))
            else:
                files.append(content)
        
        return files

    def _parse_imports(self, content: str, file_path: str) -> List[str]:
        """Parse import statements (Python)"""
        imports = []
        
        # Python imports
        if file_path.endswith('.py'):
            import_pattern = r'^(?:from\s+([\w.]+)\s+import|import\s+([\w.]+))'
            matches = re.findall(import_pattern, content, re.MULTILINE)
            for match in matches:
                module = match[0] or match[1]
                imports.append(module)
        
        # TODO: Add parsers for JavaScript, Java, etc.
        return imports

    def _find_importers(self, file_path: str) -> List[str]:
        """Find files that import this file"""
        file_name = file_path.split('/')[-1].replace('.py', '')
        importers = []
        
        all_files = self._get_all_files()
        for file in all_files:
            if file.path.endswith('.py') and file.path != file_path:
                try:
                    content = self.get_file_content(file.path)
                    if file_name in content:
                        importers.append(file.path)
                except:
                    pass
        
        return importers[:20]  # Limit to avoid huge lists

    def _find_line_commit(self, file_path: str, line_number: int, commits) -> dict:
        """Find which commit last modified a line (simplified)"""
        # Simplified: return most recent commit
        # Real implementation would parse git blame properly
        if commits:
            commit = commits[0]
            return {
                'sha': commit.sha[:7],
                'author': commit.commit.author.name,
                'email': commit.commit.author.email,
                'date': commit.commit.author.date.isoformat(),
                'message': commit.commit.message
            }
        
        return {
            'sha': 'unknown',
            'author': 'unknown',
            'email': 'unknown',
            'date': 'unknown',
            'message': 'unknown'
        }

    def _line_in_patch(self, patch: str, line_number: int) -> bool:
        """Check if a line number appears in a patch (simplified)"""
        # Parse unified diff format
        # Look for @@ -X,Y +A,B @@ headers
        # Real implementation would properly parse the diff
        return f'+{line_number}' in patch or str(line_number) in patch