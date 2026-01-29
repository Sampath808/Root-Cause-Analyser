"""Code analysis utilities for parsing and understanding code structure."""

import ast
import re
from typing import Dict, List, Optional, Any

def extract_function(content: str, function_name: str, file_path: str) -> Dict[str, Any]:
    """Extract and analyze a specific function from code content.
    
    Args:
        content: File content as string
        function_name: Name of function to extract
        file_path: Path to the file (for context)
        
    Returns:
        Dictionary with function information
    """
    try:
        if file_path.endswith('.py'):
            return _extract_python_function(content, function_name)
        elif file_path.endswith(('.js', '.ts')):
            return _extract_javascript_function(content, function_name)
        else:
            return _extract_generic_function(content, function_name)
    except Exception as e:
        return {
            'error': f'Failed to analyze function: {str(e)}',
            'function_name': function_name,
            'file_path': file_path
        }

def _extract_python_function(content: str, function_name: str) -> Dict[str, Any]:
    """Extract Python function using AST parsing."""
    try:
        tree = ast.parse(content)
        
        for node in ast.walk(tree):
            if isinstance(node, ast.FunctionDef) and node.name == function_name:
                # Get function source
                lines = content.split('\n')
                start_line = node.lineno
                end_line = node.end_lineno if hasattr(node, 'end_lineno') else start_line + 10
                
                function_source = '\n'.join(lines[start_line-1:end_line])
                
                # Extract parameters
                params = []
                for arg in node.args.args:
                    params.append(arg.arg)
                
                # Extract docstring
                docstring = ast.get_docstring(node)
                
                # Find function calls within this function
                calls = []
                for child in ast.walk(node):
                    if isinstance(child, ast.Call):
                        if isinstance(child.func, ast.Name):
                            calls.append(child.func.id)
                        elif isinstance(child.func, ast.Attribute):
                            calls.append(child.func.attr)
                
                return {
                    'function_name': function_name,
                    'start_line': start_line,
                    'end_line': end_line,
                    'parameters': params,
                    'docstring': docstring,
                    'source_code': function_source,
                    'function_calls': list(set(calls)),
                    'complexity_estimate': len(calls) + len(params)
                }
        
        return {
            'error': f'Function "{function_name}" not found',
            'function_name': function_name
        }
        
    except SyntaxError as e:
        return {
            'error': f'Syntax error in Python code: {str(e)}',
            'function_name': function_name
        }

def _extract_javascript_function(content: str, function_name: str) -> Dict[str, Any]:
    """Extract JavaScript/TypeScript function using regex patterns."""
    # Pattern for function declarations and expressions
    patterns = [
        rf'function\s+{function_name}\s*\([^)]*\)\s*\{{[^}}]*\}}',
        rf'const\s+{function_name}\s*=\s*\([^)]*\)\s*=>\s*\{{[^}}]*\}}',
        rf'{function_name}\s*:\s*function\s*\([^)]*\)\s*\{{[^}}]*\}}',
        rf'{function_name}\s*\([^)]*\)\s*\{{[^}}]*\}}'  # Method in class
    ]
    
    for pattern in patterns:
        match = re.search(pattern, content, re.DOTALL | re.MULTILINE)
        if match:
            function_source = match.group(0)
            lines = content.split('\n')
            
            # Find line numbers
            start_pos = match.start()
            start_line = content[:start_pos].count('\n') + 1
            end_line = start_line + function_source.count('\n')
            
            # Extract parameters (simplified)
            param_match = re.search(r'\(([^)]*)\)', function_source)
            params = []
            if param_match:
                param_str = param_match.group(1)
                if param_str.strip():
                    params = [p.strip().split(':')[0].strip() for p in param_str.split(',')]
            
            return {
                'function_name': function_name,
                'start_line': start_line,
                'end_line': end_line,
                'parameters': params,
                'source_code': function_source,
                'language': 'javascript'
            }
    
    return {
        'error': f'Function "{function_name}" not found',
        'function_name': function_name
    }

def _extract_generic_function(content: str, function_name: str) -> Dict[str, Any]:
    """Generic function extraction for other languages."""
    lines = content.split('\n')
    matches = []
    
    for i, line in enumerate(lines, 1):
        if function_name in line and any(keyword in line.lower() for keyword in ['def', 'function', 'func', 'method']):
            matches.append({
                'line_number': i,
                'line_content': line.strip(),
                'context': lines[max(0, i-3):min(len(lines), i+10)]
            })
    
    if matches:
        return {
            'function_name': function_name,
            'matches': matches,
            'language': 'generic'
        }
    
    return {
        'error': f'Function "{function_name}" not found',
        'function_name': function_name
    }

def analyze_imports(content: str, file_path: str) -> Dict[str, List[str]]:
    """Analyze import statements in a file."""
    imports = {
        'standard_library': [],
        'third_party': [],
        'local': []
    }
    
    if file_path.endswith('.py'):
        imports.update(_analyze_python_imports(content))
    elif file_path.endswith(('.js', '.ts')):
        imports.update(_analyze_javascript_imports(content))
    
    return imports

def _analyze_python_imports(content: str) -> Dict[str, List[str]]:
    """Analyze Python imports."""
    imports = {
        'standard_library': [],
        'third_party': [],
        'local': []
    }
    
    try:
        tree = ast.parse(content)
        
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                for alias in node.names:
                    imports['third_party'].append(alias.name)
            elif isinstance(node, ast.ImportFrom):
                if node.module:
                    if node.level > 0:  # Relative import
                        imports['local'].append(node.module)
                    else:
                        imports['third_party'].append(node.module)
    except:
        # Fallback to regex if AST fails
        import_lines = re.findall(r'^(?:from\s+([\w.]+)\s+import|import\s+([\w.]+))', content, re.MULTILINE)
        for match in import_lines:
            module = match[0] or match[1]
            imports['third_party'].append(module)
    
    return imports

def _analyze_javascript_imports(content: str) -> Dict[str, List[str]]:
    """Analyze JavaScript/TypeScript imports."""
    imports = {
        'standard_library': [],
        'third_party': [],
        'local': []
    }
    
    # ES6 imports
    import_patterns = [
        r'import\s+.*\s+from\s+[\'"]([^\'"]+)[\'"]',
        r'import\s+[\'"]([^\'"]+)[\'"]',
        r'require\s*\(\s*[\'"]([^\'"]+)[\'"]\s*\)'
    ]
    
    for pattern in import_patterns:
        matches = re.findall(pattern, content)
        for match in matches:
            if match.startswith('.'):
                imports['local'].append(match)
            else:
                imports['third_party'].append(match)
    
    return imports

def get_complexity_metrics(content: str, file_path: str) -> Dict[str, Any]:
    """Calculate basic complexity metrics for a file."""
    lines = content.split('\n')
    
    metrics = {
        'total_lines': len(lines),
        'code_lines': len([line for line in lines if line.strip() and not line.strip().startswith('#')]),
        'comment_lines': len([line for line in lines if line.strip().startswith('#')]),
        'blank_lines': len([line for line in lines if not line.strip()]),
        'functions': 0,
        'classes': 0
    }
    
    if file_path.endswith('.py'):
        try:
            tree = ast.parse(content)
            for node in ast.walk(tree):
                if isinstance(node, ast.FunctionDef):
                    metrics['functions'] += 1
                elif isinstance(node, ast.ClassDef):
                    metrics['classes'] += 1
        except:
            pass
    
    return metrics