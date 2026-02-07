from github import Github
from typing import List, Dict, Optional
import json
import re
from datetime import datetime


class GitHubClient:
    """Comprehensive GitHub client exposing all repository operations as tools.
    Each method should be designed to return JSON-serializable results."""

    def __init__(self, access_token: str, repo_full_name: str, branch: str = "main"):
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
    def get_repository_structure(self, max_depth: int = 3, path: str = "") -> str:
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

        def build_tree(current_path: str = "", depth: int = 0) -> dict:
            if depth >= max_depth:
                return {}

            try:
                contents = self.repo.get_contents(current_path, ref=self.branch)
                if not isinstance(contents, list):
                    contents = [contents]

                structure = {}
                for content in contents:
                    if content.type == "dir":
                        structure[content.name + "/"] = {
                            "type": "directory",
                            "path": content.path,
                            "children": build_tree(content.path, depth + 1),
                        }
                    else:
                        structure[content.name] = {
                            "type": "file",
                            "path": content.path,
                            "size": content.size,
                            "extension": (
                                content.name.split(".")[-1]
                                if "." in content.name
                                else None
                            ),
                        }
                return structure
            except Exception as e:
                return {"error": str(e)}

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
                    match_type.append("filename")

                # For code files, search content (limited to avoid rate limits)
                if file.path.endswith(
                    (".py", ".js", ".java", ".cpp", ".go", ".rb", ".ts")
                ):
                    try:
                        content = self.get_file_content(file.path)
                        if query_lower in content.lower():
                            score += 20
                            match_type.append("content")

                            # Find line numbers where query appears
                            lines = content.split("\n")
                            matching_lines = [
                                i + 1
                                for i, line in enumerate(lines)
                                if query_lower in line.lower()
                            ]

                            if matching_lines:
                                matches.append(
                                    {
                                        "path": file.path,
                                        "score": score,
                                        "match_type": match_type,
                                        "matching_lines": matching_lines[
                                            :5
                                        ],  # First 5 matches
                                        "size": file.size,
                                    }
                                )
                    except:
                        pass  # Skip files that can't be read
                elif score > 0:
                    matches.append(
                        {
                            "path": file.path,
                            "score": score,
                            "match_type": match_type,
                            "size": file.size,
                        }
                    )

            # Sort by score
            matches.sort(key=lambda x: x["score"], reverse=True)
            return json.dumps(matches[:max_results], indent=2)

        except Exception as e:
            return json.dumps({"error": str(e)})

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
            decoded = content.decoded_content.decode("utf-8")
            self._file_cache[file_path] = decoded
            return decoded
        except Exception as e:
            return f"ERROR: Could not read file '{file_path}': {str(e)}"

    # ============================================================
    # TOOL 4: Get Directory Files
    # ============================================================
    def get_directory_files(self, directory_path: str = "") -> str:
        """List all files in a specific directory (non-recursive).

        Returns: JSON string with file list
        """
        try:
            contents = self.repo.get_contents(directory_path, ref=self.branch)
            if not isinstance(contents, list):
                contents = [contents]

            files = []
            for item in contents:
                files.append(
                    {
                        "name": item.name,
                        "path": item.path,
                        "type": item.type,
                        "size": item.size if item.type == "file" else None,
                    }
                )

            return json.dumps(files, indent=2)
        except Exception as e:
            return json.dumps({"error": str(e)})

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
                history.append(
                    {
                        "sha": commit.sha,
                        "short_sha": commit.sha[:7],
                        "message": commit.commit.message,
                        "author": commit.commit.author.name,
                        "author_email": commit.commit.author.email,
                        "date": commit.commit.author.date.isoformat(),
                        "url": commit.html_url,
                    }
                )

            return json.dumps(history, indent=2)
        except Exception as e:
            return json.dumps({"error": str(e)})

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
                "sha": commit.sha,
                "short_sha": commit.sha[:7],
                "message": commit.commit.message,
                "author": {
                    "name": commit.commit.author.name,
                    "email": commit.commit.author.email,
                    "date": commit.commit.author.date.isoformat(),
                },
                "committer": {
                    "name": commit.commit.committer.name,
                    "email": commit.commit.committer.email,
                    "date": commit.commit.committer.date.isoformat(),
                },
                "stats": {
                    "additions": commit.stats.additions,
                    "deletions": commit.stats.deletions,
                    "total": commit.stats.total,
                },
                "files_changed": [],
                "url": commit.html_url,
            }

            # Get files changed with diffs
            for file in commit.files:
                file_info = {
                    "filename": file.filename,
                    "status": file.status,
                    "additions": file.additions,
                    "deletions": file.deletions,
                    "changes": file.changes,
                }

                # Include patch (diff) if available
                if hasattr(file, "patch") and file.patch:
                    file_info["patch"] = file.patch

                details["files_changed"].append(file_info)

            return json.dumps(details, indent=2)
        except Exception as e:
            return json.dumps({"error": str(e)})

    # ============================================================
    # TOOL 8: Find File Dependencies
    # ============================================================
    def find_file_dependencies(self, file_path: str) -> str:
        """Find what this file imports and what files import this file.

        Returns: JSON string with dependencies
        """
        try:
            content = self.get_file_content(file_path)
            if content.startswith("ERROR"):
                return json.dumps({"error": content})

            # Parse imports (Python example - extend for other languages)
            imports = self._parse_imports(content, file_path)

            # Find files that import this file
            importers = self._find_importers(file_path)

            return json.dumps(
                {"file": file_path, "imports": imports, "imported_by": importers},
                indent=2,
            )
        except Exception as e:
            return json.dumps({"error": str(e)})

    # ============================================================
    # TOOL 9: Search in File
    # ============================================================
    def search_in_file(self, file_path: str, search_term: str) -> str:
        """Search for specific text within a file and return matching lines.

        Returns: JSON string with matching lines and context
        """
        try:
            content = self.get_file_content(file_path)
            if content.startswith("ERROR"):
                return json.dumps({"error": content})

            lines = content.split("\n")
            matches = []

            for idx, line in enumerate(lines, 1):
                if search_term.lower() in line.lower():
                    # Include context (2 lines before and after)
                    context_start = max(0, idx - 3)
                    context_end = min(len(lines), idx + 2)

                    matches.append(
                        {
                            "line_number": idx,
                            "line": line,
                            "context": {
                                "before": lines[context_start : idx - 1],
                                "after": lines[idx:context_end],
                            },
                        }
                    )

            return json.dumps(
                {
                    "file": file_path,
                    "search_term": search_term,
                    "matches": matches,
                    "total_matches": len(matches),
                },
                indent=2,
            )
        except Exception as e:
            return json.dumps({"error": str(e)})

    # ============================================================
    # TOOL 10: Get Recent Commits
    # ============================================================
    def get_recent_commits(
        self, limit: int = 20, since_date: Optional[str] = None
    ) -> str:
        """Get recent commits to the entire repository.

        Args:
            limit: Number of commits
            since_date: ISO date string (e.g., "2024-01-01")

        Returns: JSON string with commit list
        """
        try:
            kwargs = {"sha": self.branch}
            if since_date:
                kwargs["since"] = datetime.fromisoformat(since_date)

            commits = self.repo.get_commits(**kwargs)
            commit_list = []

            for commit in list(commits)[:limit]:
                commit_list.append(
                    {
                        "sha": commit.sha[:7],
                        "message": commit.commit.message,
                        "author": commit.commit.author.name,
                        "date": commit.commit.author.date.isoformat(),
                        "files_changed": len(commit.files),
                        "url": commit.html_url,
                    }
                )

            return json.dumps(commit_list, indent=2)
        except Exception as e:
            return json.dumps({"error": str(e)})

    # ============================================================
    # TOOL 6: Get File Blame (WHO wrote WHAT)
    # ============================================================
    def get_file_blame(
        self,
        file_path: str,
        line_start: Optional[int] = None,
        line_end: Optional[int] = None,
    ) -> str:
        """Get git blame information showing who wrote each line.

        Args:
            file_path: Path to file
            line_start: Optional start line number
            line_end: Optional end line number

        Returns: JSON string with blame information per line
        """
        try:
            # Get file content to know total lines
            content = self.get_file_content(file_path)
            if content.startswith("ERROR"):
                return json.dumps({"error": content})

            lines = content.split("\n")
            total_lines = len(lines)

            # Determine line range
            start = line_start if line_start else 1
            end = line_end if line_end else total_lines

            # Clamp to valid range
            start = max(1, min(start, total_lines))
            end = max(start, min(end, total_lines))

            # Get commits that modified this file
            commits = list(self.repo.get_commits(path=file_path, sha=self.branch))

            blame_data = []

            # For each line in the range, find the most recent commit that modified it
            for line_num in range(start, end + 1):
                line_content = lines[line_num - 1] if line_num <= len(lines) else ""

                # Find the commit that last modified this line
                line_commit = self._find_line_commit_real(
                    file_path, line_num, commits, line_content
                )

                blame_data.append(
                    {
                        "line_number": line_num,
                        "line_content": line_content,
                        "commit_sha": line_commit["sha"],
                        "author": line_commit["author"],
                        "author_email": line_commit["email"],
                        "date": line_commit["date"],
                        "commit_message": line_commit["message"],
                    }
                )

            return json.dumps(
                {
                    "file": file_path,
                    "line_range": f"{start}-{end}",
                    "blame_data": blame_data,
                },
                indent=2,
            )

        except Exception as e:
            return json.dumps({"error": str(e)})

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
            # Get current file content
            current_content = self.get_file_content(file_path)
            if current_content.startswith("ERROR"):
                return json.dumps({"error": current_content})

            current_lines = current_content.split("\n")

            # Get commits in chronological order (oldest first)
            commits = list(
                reversed(list(self.repo.get_commits(path=file_path, sha=self.branch)))
            )

            results = {}

            for line_num in line_numbers:
                if line_num > len(current_lines):
                    results[str(line_num)] = {
                        "error": "Line number exceeds file length"
                    }
                    continue

                target_line = current_lines[line_num - 1].strip()

                # Search through commits chronologically to find when this line was added
                found_commit = self._find_line_introduction_commit(
                    file_path, line_num, target_line, commits
                )

                if found_commit:
                    results[str(line_num)] = {
                        "line_content": target_line,
                        "commit_sha": found_commit.sha[:7],
                        "full_sha": found_commit.sha,
                        "author": found_commit.commit.author.name,
                        "author_email": found_commit.commit.author.email,
                        "date": found_commit.commit.author.date.isoformat(),
                        "message": found_commit.commit.message.strip(),
                        "url": found_commit.html_url,
                    }
                else:
                    results[str(line_num)] = {
                        "line_content": target_line,
                        "error": "Could not determine when this line was added",
                    }

            return json.dumps(results, indent=2)

        except Exception as e:
            return json.dumps({"error": str(e)})

    # ============================================================
    # Helper Methods for Blame Functionality
    # ============================================================
    def _find_line_commit_real(
        self, file_path: str, line_number: int, commits, line_content: str
    ) -> dict:
        """Find which commit last modified a specific line by analyzing diffs."""
        try:
            # Look through commits from newest to oldest
            for commit in commits:
                # Check if this commit modified the file
                for file in commit.files:
                    if (
                        file.filename == file_path
                        and hasattr(file, "patch")
                        and file.patch
                    ):
                        # Check if this line was modified in this commit
                        if self._line_modified_in_patch(
                            file.patch, line_number, line_content
                        ):
                            return {
                                "sha": commit.sha[:7],
                                "author": commit.commit.author.name,
                                "email": commit.commit.author.email,
                                "date": commit.commit.author.date.isoformat(),
                                "message": commit.commit.message.strip(),
                            }

            # If no specific commit found, return the oldest commit that touched the file
            if commits:
                commit = commits[-1]  # Oldest commit
                return {
                    "sha": commit.sha[:7],
                    "author": commit.commit.author.name,
                    "email": commit.commit.author.email,
                    "date": commit.commit.author.date.isoformat(),
                    "message": commit.commit.message.strip(),
                }

        except Exception:
            pass

        return {
            "sha": "unknown",
            "author": "unknown",
            "email": "unknown",
            "date": "unknown",
            "message": "Could not determine commit",
        }

    def _find_line_introduction_commit(
        self, file_path: str, line_number: int, target_line: str, commits
    ):
        """Find the commit that first introduced a specific line."""
        try:
            for commit in commits:  # Already in chronological order (oldest first)
                for file in commit.files:
                    if (
                        file.filename == file_path
                        and hasattr(file, "patch")
                        and file.patch
                    ):
                        # Check if this line was added in this commit
                        if self._line_added_in_patch(file.patch, target_line):
                            return commit
            return None
        except Exception:
            return None

    def _line_modified_in_patch(
        self, patch: str, line_number: int, line_content: str
    ) -> bool:
        """Check if a specific line was modified in a patch."""
        try:
            lines = patch.split("\n")
            current_line_num = 0

            for line in lines:
                # Parse diff headers to track line numbers
                if line.startswith("@@"):
                    # Extract line number info: @@ -old_start,old_count +new_start,new_count @@
                    match = re.search(
                        r"@@\s*-\d+(?:,\d+)?\s*\+(\d+)(?:,\d+)?\s*@@", line
                    )
                    if match:
                        current_line_num = int(match.group(1)) - 1
                elif line.startswith("+") and not line.startswith("+++"):
                    current_line_num += 1
                    # Check if this added line matches our target
                    if (
                        current_line_num == line_number
                        and line_content.strip() in line[1:].strip()
                    ):
                        return True
                elif line.startswith("-") and not line.startswith("---"):
                    # Deleted line, don't increment line number
                    pass
                elif not line.startswith("\\"):
                    # Context line
                    current_line_num += 1

            return False
        except Exception:
            return False

    def _line_added_in_patch(self, patch: str, target_line: str) -> bool:
        """Check if a specific line was added in a patch."""
        try:
            lines = patch.split("\n")

            for line in lines:
                if line.startswith("+") and not line.startswith("+++"):
                    added_content = line[1:].strip()
                    if added_content and target_line.strip() in added_content:
                        return True

            return False
        except Exception:
            return False

    # ============================================================
    # TOOL 12: Analyze Function
    # ============================================================
    def analyze_function(self, file_path: str, function_name: str) -> str:
        """Extract and analyze a specific function from a file.

        Returns: JSON string with function details
        """
        try:
            content = self.get_file_content(file_path)
            if content.startswith("ERROR"):
                return json.dumps({"error": content})

            # Use AST parsing (implement in code_analyzer.py)
            from .code_analyzer import extract_function

            function_info = extract_function(content, function_name, file_path)
            return json.dumps(function_info, indent=2)
        except Exception as e:
            return json.dumps({"error": str(e)})

    # ============================================================
    # Helper Methods (Private)
    # ============================================================
    def _get_all_files(self, path: str = ""):
        """Recursively get all files in repository"""
        contents = self.repo.get_contents(path, ref=self.branch)
        files = []

        if not isinstance(contents, list):
            contents = [contents]

        for content in contents:
            if content.type == "dir":
                files.extend(self._get_all_files(content.path))
            else:
                files.append(content)

        return files

    def _parse_imports(self, content: str, file_path: str) -> List[str]:
        """Parse import statements (Python)"""
        imports = []

        # Python imports
        if file_path.endswith(".py"):
            import_pattern = r"^(?:from\s+([\w.]+)\s+import|import\s+([\w.]+))"
            matches = re.findall(import_pattern, content, re.MULTILINE)
            for match in matches:
                module = match[0] or match[1]
                imports.append(module)

        # TODO: Add parsers for JavaScript, Java, etc.
        return imports

    def _find_importers(self, file_path: str) -> List[str]:
        """Find files that import this file"""
        file_name = file_path.split("/")[-1].replace(".py", "")
        importers = []

        all_files = self._get_all_files()
        for file in all_files:
            if file.path.endswith(".py") and file.path != file_path:
                try:
                    content = self.get_file_content(file.path)
                    if file_name in content:
                        importers.append(file.path)
                except:
                    pass

        return importers[:20]  # Limit to avoid huge lists
