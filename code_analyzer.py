import ast
import re
from typing import Dict, Any, List


class CodeAnalyzer:
    """
    In-memory static code analyzer.
    Analyzes complexity, security patterns, and maintainability without retaining source code.
    """

    @staticmethod
    def analyze_source_code(code_text: str, filename: str = "snippet.py") -> Dict[str, Any]:
        """
        Analyzes source code in-memory and immediately returns structured metrics.
        No source code is persisted to long-term storage.
        """
        lines = code_text.splitlines()
        total_loc = len(lines)
        blank_lines = sum(1 for line in lines if not line.strip())
        comment_lines = sum(1 for line in lines if line.strip().startswith(("#", "//", "/*", "*")))
        code_loc = max(0, total_loc - blank_lines - comment_lines)

        functions_count = 0
        classes_count = 0
        ast_parsed = False
        complexity_score = 1.0

        # Try AST parsing for Python files
        try:
            tree = ast.parse(code_text)
            ast_parsed = True
            for node in ast.walk(tree):
                if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
                    functions_count += 1
                elif isinstance(node, ast.ClassDef):
                    classes_count += 1
                elif isinstance(node, (ast.If, ast.For, ast.While, ast.ExceptHandler, ast.With)):
                    complexity_score += 0.5
        except Exception:
            # Fallback regex parsing for multi-language support (JS, TS, Python, etc.)
            functions_count = len(re.findall(r"\b(def|function|fn|func)\s+\w+", code_text))
            classes_count = len(re.findall(r"\b(class|struct|interface)\s+\w+", code_text))
            complexity_score += len(re.findall(r"\b(if|for|while|catch|switch|case)\b", code_text)) * 0.5

        # Security & Code Smell Checks
        findings: List[Dict[str, str]] = []

        # 1. Hardcoded secrets / API keys
        if re.search(r"(?i)(api[_-]?key|secret|password|token)\s*=\s*['\"][a-zA-Z0-9_\-]{8,}['\"]", code_text):
            findings.append({
                "severity": "HIGH",
                "category": "Security",
                "message": "Potential hardcoded secret or API credential detected in source code."
            })

        # 2. Insecure code execution
        if re.search(r"\b(eval|exec|os\.system|subprocess\.Popen\(.*shell\s*=\s*True)\b", code_text):
            findings.append({
                "severity": "HIGH",
                "category": "Security",
                "message": "Dangerous dynamic execution pattern (eval/exec/shell=True) detected."
            })

        # 3. SQL Injection pattern
        if re.search(r"(?i)(SELECT|INSERT|UPDATE|DELETE).*\+.*(?:request|params|input)", code_text):
            findings.append({
                "severity": "HIGH",
                "category": "Security",
                "message": "Potential raw SQL string concatenation without parameterized queries."
            })

        # 4. Long function / complexity
        if total_loc > 300:
            findings.append({
                "severity": "MEDIUM",
                "category": "Maintainability",
                "message": f"Module length ({total_loc} lines) exceeds maintainability recommendations (>300 lines)."
            })

        # 5. Low comment ratio
        if total_loc > 30 and (comment_lines / max(1, total_loc)) < 0.05:
            findings.append({
                "severity": "LOW",
                "category": "Documentation",
                "message": "Low inline documentation/comment ratio (<5% of code)."
            })

        # Calculate Overall Quality Score (0 to 100)
        base_score = 100
        for f in findings:
            if f["severity"] == "HIGH":
                base_score -= 20
            elif f["severity"] == "MEDIUM":
                base_score -= 10
            elif f["severity"] == "LOW":
                base_score -= 5

        quality_score = max(10, min(100, base_score))

        grade = "A+"
        if quality_score >= 90:
            grade = "A"
        elif quality_score >= 80:
            grade = "B"
        elif quality_score >= 70:
            grade = "C"
        elif quality_score >= 60:
            grade = "D"
        else:
            grade = "F"

        return {
            "filename": filename,
            "total_loc": total_loc,
            "code_loc": code_loc,
            "comment_lines": comment_lines,
            "blank_lines": blank_lines,
            "functions_count": functions_count,
            "classes_count": classes_count,
            "complexity_score": round(complexity_score, 1),
            "quality_score": quality_score,
            "grade": grade,
            "findings": findings,
            "ast_parsed": ast_parsed
        }
