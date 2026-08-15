import ast
import re
import os
from typing import Dict, Any, List, Tuple


SUPPORTED_EXTENSIONS = {
    ".py", ".sql", ".dax", ".js", ".ts", ".jsx", ".tsx",
    ".cpp", ".c", ".h", ".hpp", ".json", ".txt"
}

IGNORED_PATTERNS = {
    ".git", "node_modules", "__pycache__", ".venv", "venv",
    ".env", "package-lock.json", "yarn.lock", ".ds_store",
    "dist", "build", ".pytest_cache", ".idea", ".vscode"
}


class CodeAnalyzer:
    """
    In-memory static code analyzer.
    Analyzes complexity, security patterns, and maintainability without retaining source code.
    Generates canonical 7-section Markdown reports and metrics.
    """

    @staticmethod
    def is_analyzable_file(filepath: str) -> bool:
        """Returns True if the file path is a supported source file and not ignored."""
        normalized = filepath.replace("\\", "/").lower()
        parts = normalized.split("/")

        # Check ignored path segments or filenames
        for part in parts:
            if part in IGNORED_PATTERNS or part.startswith("."):
                if part not in (".sql", ".py", ".dax", ".js", ".ts", ".jsx", ".tsx", ".cpp", ".c", ".h", ".hpp", ".json", ".txt"):
                    return False

        _, ext = os.path.splitext(normalized)
        return ext in SUPPORTED_EXTENSIONS

    @staticmethod
    def analyze_source_code(code_text: str, filename: str = "snippet.py") -> Dict[str, Any]:
        """
        Analyzes source code in-memory and immediately returns structured metrics.
        No source code is persisted to long-term storage.
        """
        lines = code_text.splitlines()
        total_loc = len(lines)
        blank_lines = sum(1 for line in lines if not line.strip())
        comment_lines = sum(1 for line in lines if line.strip().startswith(("#", "//", "/*", "*", "--")))
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
            # Fallback regex parsing for multi-language support (JS, TS, Python, SQL, C++, DAX, etc.)
            functions_count = len(re.findall(r"\b(def|function|fn|func)\s+\w+", code_text))
            classes_count = len(re.findall(r"\b(class|struct|interface)\s+\w+", code_text))
            complexity_score += len(re.findall(r"\b(if|for|while|catch|switch|case)\b", code_text, re.IGNORECASE)) * 0.5

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
        elif filename.endswith(".json"):
            lang = "JSON Data Structure"
        elif filename.endswith(".txt"):
            lang = "Text / Documentation"

        # Extract Dependencies / Imports
        dependencies = []
        if lang == "Python":
            deps = re.findall(r"^(?:from\s+([\w\.]+)\s+import|import\s+([\w\.]+))", code_text, re.MULTILINE)
            dependencies = [d[0] or d[1] for d in deps if d[0] or d[1]]
        elif lang in ("JavaScript/TypeScript", "C++"):
            deps = re.findall(r"(?:require\(['\"]([^'\"]+)['\"]|import\s+.*?from\s+['\"]([^'\"]+)['\"]|#include\s+[<\"']([^>\'\"]+)[>\"'])", code_text)
            dependencies = [d[0] or d[1] or d[2] for d in deps if any(d)]
        elif lang == "SQL":
            dependencies = ["Database Engine (ANSI SQL / Dialect)"]
        elif lang == "DAX":
            dependencies = ["Power BI / SSAS Data Model Engine"]

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
            business_logic.append(f"Executes core domain logic for {filename} across {total_loc} lines.")

        # Best Practices Breakdown
        best_practices = {
            "readability": "Clear naming conventions and structured modular definitions." if comment_lines > 2 else "Recommendation: Add additional inline comments explaining business calculations.",
            "performance": "Optimized execution flow." if complexity_score < 10 else f"High complexity score ({complexity_score}). Consider refactoring nested branching.",
            "error_handling": "Exception safety checks present." if ("try" in lower_code or "except" in lower_code or "ifblank" in lower_code or "coalesce" in lower_code) else "Ensure edge cases, null values, and missing attributes are safely handled.",
            "security": "No dangerous dynamic execution patterns detected." if not any(f["category"] == "Security" for f in findings) else "Critical security items detected — see findings list.",
            "maintainability": f"Manageable footprint ({total_loc} lines of code)." if total_loc <= 300 else "File length exceeds 300 lines; recommend modular refactoring."
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

        metrics = {
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

        metrics["markdown_report"] = CodeAnalyzer.generate_markdown_report(metrics)
        return metrics

    @staticmethod
    def generate_markdown_report(metrics: Dict[str, Any]) -> str:
        """
        Generates the canonical 7-section structured Markdown report matching the reference demo format.
        """
        filename = metrics.get("filename", "source_file")
        lang = metrics.get("language", "General")
        total_loc = metrics.get("total_loc", 0)
        code_loc = metrics.get("code_loc", 0)
        complexity = metrics.get("complexity_score", 1.0)
        quality_score = metrics.get("quality_score", 100)
        grade = metrics.get("grade", "A")

        md = []
        md.append(f"# Documentation Report for\n`{filename}`\n")
        md.append(f"**Score:** {quality_score}/100 &nbsp;|&nbsp; **Grade:** {grade} &nbsp;|&nbsp; **Language:** {lang}\n")

        # 1. Overview
        md.append("## 1. Overview\n")
        md.append(f"This source file (`{filename}`) contains **{total_loc}** total lines of code (**{code_loc}** executable). ")
        md.append(f"It executes in a **{lang}** environment with a cyclomatic complexity index of **{complexity}**.\n")

        # 2. Business Logic
        md.append("## 2. Business Logic\n")
        b_logic = metrics.get("business_logic", [])
        if b_logic:
            for bl in b_logic:
                md.append(f"- {bl}")
        else:
            md.append(f"- Implements algorithmic calculations and domain workflows for `{filename}`.")
        md.append("")

        # 3. Inputs
        md.append("## 3. Inputs\n")
        inputs = metrics.get("inputs", [])
        if inputs:
            md.append("| Name | Type | Description |")
            md.append("| :--- | :--- | :--- |")
            for inp in inputs:
                md.append(f"| {inp.get('name', 'Param')} | {inp.get('type', 'Param')} | {inp.get('description', '')} |")
        else:
            md.append("No explicit function arguments or filter parameters detected.\n")
        md.append("")

        # 4. Outputs
        md.append("## 4. Outputs\n")
        outputs = metrics.get("outputs", [])
        if outputs:
            md.append("| Name | Type | Description |")
            md.append("| :--- | :--- | :--- |")
            for out in outputs:
                md.append(f"| {out.get('name', 'Output')} | {out.get('type', 'Type')} | {out.get('description', '')} |")
        else:
            md.append("Standard direct execution returns.\n")
        md.append("")

        # 5. Dependencies
        md.append("## 5. Dependencies\n")
        deps = metrics.get("dependencies", [])
        if deps:
            for d in deps:
                md.append(f"- `{d}`")
        else:
            md.append("- No external module imports detected.")
        md.append("")

        # 6. Data Relationships (SQL/DAX only)
        if lang in ("SQL", "DAX"):
            md.append("## 6. Data Relationships (SQL/DAX only)\n")
            tables = metrics.get("tables_referenced", [])
            joins = metrics.get("joins", [])
            if tables:
                md.append(f"**Referenced Tables:** {', '.join([f'`{t}`' for t in tables])}\n")
            if joins:
                md.append("**Join Conditions:**\n")
                for j in joins:
                    md.append(f"- **{j.get('join_type', 'JOIN')}** `{j.get('table')}` on `{j.get('condition')}`")
            if not tables and not joins:
                md.append("Direct data entity queries without explicit joins.\n")
            md.append("")

        # 7. Best Practices Review
        md.append("## 7. Best Practices Review\n")
        bp = metrics.get("best_practices", {})
        md.append(f"### Readability and Naming Conventions\n{bp.get('readability', 'Standard formatting.')}\n")
        md.append(f"### Performance Optimization\n{bp.get('performance', 'Standard execution complexity.')}\n")
        md.append(f"### Error Handling\n{bp.get('error_handling', 'Standard exception safeguards.')}\n")
        md.append(f"### Security Considerations\n{bp.get('security', 'No critical risks identified.')}\n")
        md.append(f"### Maintainability\n{bp.get('maintainability', 'Modular footprint.')}\n")

        findings = metrics.get("findings", [])
        if findings:
            md.append("### Identified Security & Quality Findings\n")
            for f in findings:
                md.append(f"- **[{f.get('severity')}] {f.get('category')}**: {f.get('message')}")
            md.append("")

        return "\n".join(md)
