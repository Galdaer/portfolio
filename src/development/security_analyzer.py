"""
AST-based Security Analysis for Healthcare Code
Provides advanced security analysis using Abstract Syntax Tree parsing
"""

import ast
import logging
import re
from typing import List, Dict, Any, Set, Optional
from dataclasses import dataclass

logger = logging.getLogger(__name__)


@dataclass
class SecurityIssue:
    """Represents a security issue found in code"""
    severity: str  # 'critical', 'high', 'medium', 'low'
    category: str  # 'authentication', 'encryption', 'injection', etc.
    message: str
    line_number: int
    column: Optional[int] = None
    code_snippet: Optional[str] = None


class SecurityAnalyzer:
    """AST-based security analysis for healthcare code"""
    
    def __init__(self):
        self.logger = logging.getLogger(f"{__name__}.SecurityAnalyzer")
        self.issues: List[SecurityIssue] = []
        
        # Security patterns to detect
        self.dangerous_functions = {
            'eval', 'exec', 'compile', '__import__',
            'open', 'file', 'input', 'raw_input'
        }
        
        self.sql_keywords = {
            'select', 'insert', 'update', 'delete', 'drop', 
            'create', 'alter', 'truncate', 'grant', 'revoke'
        }
        
        self.crypto_weak_patterns = {
            'md5', 'sha1', 'des', 'rc4', 'md4'
        }
        
        self.secret_patterns = [
            r'api[_-]?key',
            r'secret[_-]?key',
            r'password',
            r'token',
            r'auth[_-]?token',
            r'private[_-]?key',
            r'access[_-]?key',
            r'secret[_-]?access'
        ]
    
    def analyze_code_security(self, code: str, filename: str = "<string>") -> Dict[str, Any]:
        """
        Analyze code for security issues using AST parsing
        
        Args:
            code: Python code to analyze
            filename: Name of the file being analyzed
            
        Returns:
            Dict containing security analysis results
        """
        self.issues = []
        
        try:
            tree = ast.parse(code, filename=filename)
            
            # Perform various security checks
            self._check_dangerous_functions(tree)
            self._check_sql_injection_patterns(tree)
            self._check_hardcoded_secrets(tree)
            self._check_weak_cryptography(tree)
            self._check_authentication_issues(tree)
            self._check_input_validation(tree)
            self._check_file_operations(tree)
            
        except SyntaxError as e:
            self.logger.warning(f"Failed to parse code for AST analysis: {e}")
            # Fallback to basic string analysis
            return self._basic_security_analysis(code)
        
        return self._format_results()
    
    def _check_dangerous_functions(self, tree: ast.AST):
        """Check for dangerous function usage"""
        for node in ast.walk(tree):
            if isinstance(node, ast.Call) and isinstance(node.func, ast.Name):
                if node.func.id in self.dangerous_functions:
                    severity = 'critical' if node.func.id in ['eval', 'exec'] else 'high'
                    self.issues.append(SecurityIssue(
                        severity=severity,
                        category='dangerous_functions',
                        message=f"Dangerous function '{node.func.id}' usage detected",
                        line_number=node.lineno,
                        column=node.col_offset
                    ))
    
    def _check_sql_injection_patterns(self, tree: ast.AST):
        """Check for potential SQL injection vulnerabilities"""
        for node in ast.walk(tree):
            # Check for string concatenation with SQL keywords
            if isinstance(node, ast.BinOp) and isinstance(node.op, ast.Add):
                if self._contains_sql_and_string_concat(node):
                    self.issues.append(SecurityIssue(
                        severity='high',
                        category='sql_injection',
                        message="Potential SQL injection: string concatenation with SQL keywords",
                        line_number=node.lineno,
                        column=node.col_offset
                    ))
            
            # Check for f-string with SQL keywords
            elif isinstance(node, ast.JoinedStr):
                if self._contains_sql_in_fstring(node):
                    self.issues.append(SecurityIssue(
                        severity='high',
                        category='sql_injection',
                        message="Potential SQL injection: f-string with SQL keywords",
                        line_number=node.lineno,
                        column=node.col_offset
                    ))
    
    def _check_hardcoded_secrets(self, tree: ast.AST):
        """Check for hardcoded secrets and credentials"""
        for node in ast.walk(tree):
            # Check string literals
            if isinstance(node, ast.Str) and self._looks_like_secret(node.s):
                self.issues.append(SecurityIssue(
                    severity='critical',
                    category='hardcoded_secrets',
                    message="Potential hardcoded secret detected",
                    line_number=node.lineno,
                    column=node.col_offset
                ))
            
            # Check variable assignments
            elif isinstance(node, ast.Assign):
                for target in node.targets:
                    if isinstance(target, ast.Name) and self._is_secret_variable_name(target.id):
                        if isinstance(node.value, ast.Str):
                            self.issues.append(SecurityIssue(
                                severity='critical',
                                category='hardcoded_secrets',
                                message=f"Hardcoded secret in variable '{target.id}'",
                                line_number=node.lineno,
                                column=node.col_offset
                            ))
    
    def _check_weak_cryptography(self, tree: ast.AST):
        """Check for weak cryptographic algorithms"""
        for node in ast.walk(tree):
            if isinstance(node, ast.Call):
                # Check function calls for weak crypto
                if isinstance(node.func, ast.Attribute):
                    func_name = node.func.attr.lower()
                    if any(weak in func_name for weak in self.crypto_weak_patterns):
                        self.issues.append(SecurityIssue(
                            severity='medium',
                            category='weak_cryptography',
                            message=f"Weak cryptographic algorithm detected: {func_name}",
                            line_number=node.lineno,
                            column=node.col_offset
                        ))
                
                # Check imports for weak crypto libraries
                elif isinstance(node.func, ast.Name):
                    if node.func.id.lower() in self.crypto_weak_patterns:
                        self.issues.append(SecurityIssue(
                            severity='medium',
                            category='weak_cryptography',
                            message=f"Weak cryptographic function: {node.func.id}",
                            line_number=node.lineno,
                            column=node.col_offset
                        ))
    
    def _check_authentication_issues(self, tree: ast.AST):
        """Check for authentication-related security issues"""
        for node in ast.walk(tree):
            # Check for password comparisons without hashing
            if isinstance(node, ast.Compare):
                if self._contains_password_comparison(node):
                    self.issues.append(SecurityIssue(
                        severity='high',
                        category='authentication',
                        message="Potential plaintext password comparison",
                        line_number=node.lineno,
                        column=node.col_offset
                    ))
    
    def _check_input_validation(self, tree: ast.AST):
        """Check for input validation issues"""
        for node in ast.walk(tree):
            # Check for direct user input usage without validation
            if isinstance(node, ast.Call) and isinstance(node.func, ast.Name):
                if node.func.id in ['input', 'raw_input']:
                    # Check if input is used directly in dangerous contexts
                    self.issues.append(SecurityIssue(
                        severity='medium',
                        category='input_validation',
                        message="User input should be validated before use",
                        line_number=node.lineno,
                        column=node.col_offset
                    ))
    
    def _check_file_operations(self, tree: ast.AST):
        """Check for unsafe file operations"""
        for node in ast.walk(tree):
            if isinstance(node, ast.Call) and isinstance(node.func, ast.Name):
                if node.func.id == 'open':
                    # Check for file operations without proper path validation
                    if len(node.args) > 0 and isinstance(node.args[0], ast.Name):
                        self.issues.append(SecurityIssue(
                            severity='medium',
                            category='file_operations',
                            message="File path should be validated to prevent path traversal",
                            line_number=node.lineno,
                            column=node.col_offset
                        ))
    
    def _contains_sql_and_string_concat(self, node: ast.BinOp) -> bool:
        """Check if binary operation contains SQL with string concatenation"""
        node_str = ast.dump(node).lower()
        return any(keyword in node_str for keyword in self.sql_keywords)
    
    def _contains_sql_in_fstring(self, node: ast.JoinedStr) -> bool:
        """Check if f-string contains SQL keywords"""
        for value in node.values:
            if isinstance(value, ast.Str):
                if any(keyword in value.s.lower() for keyword in self.sql_keywords):
                    return True
        return False
    
    def _looks_like_secret(self, value: str) -> bool:
        """Check if string looks like a hardcoded secret"""
        if len(value) < 8:
            return False
        
        value_lower = value.lower()
        return any(re.search(pattern, value_lower) for pattern in self.secret_patterns)
    
    def _is_secret_variable_name(self, name: str) -> bool:
        """Check if variable name suggests it contains a secret"""
        name_lower = name.lower()
        return any(re.search(pattern, name_lower) for pattern in self.secret_patterns)
    
    def _contains_password_comparison(self, node: ast.Compare) -> bool:
        """Check if comparison involves password variables"""
        # Check if any part of the comparison involves password-related variables
        all_names = []
        
        if isinstance(node.left, ast.Name):
            all_names.append(node.left.id)
        
        for comparator in node.comparators:
            if isinstance(comparator, ast.Name):
                all_names.append(comparator.id)
        
        return any('password' in name.lower() for name in all_names)
    
    def _basic_security_analysis(self, code: str) -> Dict[str, Any]:
        """Fallback basic security analysis using string matching"""
        issues = []
        code_lower = code.lower()
        
        if "password" in code_lower and "hash" not in code_lower:
            issues.append(SecurityIssue(
                severity='medium',
                category='authentication',
                message="Potential plaintext password usage",
                line_number=0
            ))
        
        if any(keyword in code_lower for keyword in self.sql_keywords) and "prepare" not in code_lower:
            issues.append(SecurityIssue(
                severity='medium',
                category='sql_injection',
                message="Potential SQL injection vulnerability",
                line_number=0
            ))
        
        return self._format_results(issues)
    
    def _format_results(self, issues: Optional[List[SecurityIssue]] = None) -> Dict[str, Any]:
        """Format analysis results"""
        if issues is None:
            issues = self.issues
        
        results = {
            'total_issues': len(issues),
            'issues_by_severity': {
                'critical': [issue for issue in issues if issue.severity == 'critical'],
                'high': [issue for issue in issues if issue.severity == 'high'],
                'medium': [issue for issue in issues if issue.severity == 'medium'],
                'low': [issue for issue in issues if issue.severity == 'low']
            },
            'issues_by_category': {},
            'all_issues': issues
        }
        
        # Group by category
        for issue in issues:
            if issue.category not in results['issues_by_category']:
                results['issues_by_category'][issue.category] = []
            results['issues_by_category'][issue.category].append(issue)
        
        return results
