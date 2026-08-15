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

        # Language Detection
        lang = "Python"
        lower_code = code_text.lower()
        if filename.endswith(".sql") or "select " in lower_code or "from " in lower_code or "insert into " in lower_code:
            lang = "SQL"
        elif filename.endswith(".dax") or "calculate(" in lower_code or "summarize(" in lower_code:
            lang = "DAX"
        elif filename.endswith((".js", ".ts", ".jsx", ".tsx")):
            lang = "JavaScript/TypeScript"
        elif filename.endswith((".cpp", ".c", ".h", ".hpp")):
            lang = "C++"

        # Extract Dependencies / Imports
        dependencies = []
        if lang == "Python":
            dependencies = re.findall(r"^(?:from\s+([\w\.]+)\s+import|import\s+([\w\.]+))", code_text, re.MULTILINE)
            dependencies = [d[0] or d[1] for d in dependencies if d[0] or d[1]]
        elif lang in ("JavaScript/TypeScript", "C++"):
            dependencies = re.findall(r"(?:require\(['\"]([^'\"]+)['\"]|import\s+.*?from\s+['\"]([^'\"]+)['\"]|#include\s+[<\"']([^>\'\"]+)[>\"'])", code_text)
            dependencies = [d[0] or d[1] or d[2] for d in dependencies if any(d)]
        elif lang == "SQL":
            dependencies = ["Database Engine", "RDBMS Dialect / ANSI SQL"]

        # Extract SQL / DAX Tables & Relationships
        tables_referenced = []
        joins = []
        if lang in ("SQL", "DAX"):
            tables_referenced = list(set(re.findall(r"\bFROM\s+([A-Za-z0-9_]+)|\bJOIN\s+([A-Za-z0-9_]+)", code_text, re.IGNORECASE)))
            tables_referenced = [t[0] or t[1] for t in tables_referenced if t[0] or t[1]]
            join_matches = re.findall(r"((?:INNER|LEFT|RIGHT|FULL|CROSS)?\s*JOIN\s+([A-Za-z0-9_]+)\s+(?:AS\s+)?([A-Za-z0-9_]+)?\s+ON\s+([^;\n\r]+))", code_text, re.IGNORECASE)
            for jm in join_matches:
                joins.append({"join_type": jm[0].split()[0], "table": jm[1], "condition": jm[3].strip()})

        # Extract Inputs & Outputs
        inputs = []
        outputs = []
        if lang == "Python":
            fn_matches = re.findall(r"def\s+([a-zA-Z_]\w*)\s*\(([^)]*)\)", code_text)
            for fn_name, args in fn_matches:
                arg_list = [a.strip() for a in args.split(",") if a.strip() and a.strip() != "self"]
                inputs.append({"name": f"{fn_name}() parameters", "type": "Function Args", "description": ", ".join(arg_list) if arg_list else "None"})
            ret_matches = re.findall(r"return\s+([^#\n]+)", code_text)
            for ret in ret_matches[:5]:
                outputs.append({"name": "Return Value", "type": "Expression", "description": ret.strip()})
        elif lang == "SQL":
            select_cols = re.findall(r"SELECT\s+(.*?)\s+FROM", code_text, re.IGNORECASE | re.DOTALL)
            if select_cols:
                cols = [c.strip() for c in re.split(r",(?![^(]*\))", select_cols[0]) if c.strip()]
                for c in cols[:8]:
                    outputs.append({"name": c, "type": "Column/Metric", "description": "Projected query attribute"})
            where_params = re.findall(r"(?:WHERE|AND|OR)\s+([A-Za-z0-9_\.]+\s*(?:>=|<=|=|>|<|LIKE|IN)\s*[^;\n\r]+)", code_text, re.IGNORECASE)
            for wp in where_params[:5]:
                inputs.append({"name": "Filter Parameter", "type": "Predicate", "description": wp.strip()})

        # Business Logic Extraction
        business_logic = []
        if "delinquent" in lower_code or "pastdue" in lower_code:
            business_logic.append("Credit Union Delinquency & Aging: Classifies loan accounts by delinquency buckets (30/60/90+ days).")
        if "interest" in lower_code or "balance" in lower_code or "dividend" in lower_code:
            business_logic.append("Financial Ledger Calculations: Computes interest balances, fee accruals, or member dividend payouts.")
        if "risk" in lower_code or "score" in lower_code or "dti" in lower_code:
            business_logic.append("Underwriting & Risk Evaluation: Assesses debt-to-income (DTI) metrics and member prime/sub-prime status.")
        if not business_logic:
            business_logic.append(f"Executes domain logic for {filename} across {total_loc} lines with {functions_count} functions.")

        # Best Practices Breakdown
        best_practices = {
            "readability": "Clear naming conventions and structured modular definitions." if comment_lines > 2 else "Recommendation: Add additional inline comments explaining business calculations.",
            "performance": "Optimized execution flow." if complexity_score < 10 else f"High complexity score ({complexity_score}). Consider refactoring nested branching.",
            "error_handling": "Exception safety checks present." if ("try" in lower_code or "except" in lower_code or "ifblank" in lower_code or "coalesce" in lower_code) else "Ensure edge cases, null values, and missing attributes are safely handled.",
            "security": "No dangerous dynamic patterns found." if not any(f["category"] == "Security" for f in findings) else "Critical security items detected — see findings list.",
            "maintainability": f"Manageable footprint ({total_loc} lines of code)." if total_loc <= 300 else "File length exceeds 300 lines; recommend separating into discrete services."
        }

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
            "language": lang,
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
            "ast_parsed": ast_parsed,
            "dependencies": dependencies,
            "tables_referenced": tables_referenced,
            "joins": joins,
            "inputs": inputs,
            "outputs": outputs,
            "business_logic": business_logic,
            "best_practices": best_practices
        }
