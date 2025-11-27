# System Card: Self-Serve Credit Union Analyst

## Model Details
- **Orchestration Framework:** LangGraph (Multi-Agent Architecture)
- **Underlying LLM:** OpenAI GPT-4o (Temperature=0 for deterministic code generation)
- **Code Execution:** Docker Container (Debian-based Python 3.9 image)

## Intended Use
This system is designed to act as a "Self-Serve Analyst" for non-technical stakeholders in a financial context.
- **SQL Agent:** Answers questions about member demographics, loan counts, and account balances by querying a read-only SQLite database.
- **Visualization Agent:** Generates Python code (Matplotlib/Seaborn) to create charts and graphs based on database data.

## Safety & Security Architecture
This project mitigates the risks of LLM-generated code via a "Sandbox Pattern":
1.  **Box 1 (The Brain):** The LLM generates code but cannot execute it.
2.  **Box 2 (The Sandbox):** A Docker container isolated from the host machine executes the code.
3.  **Volume Mounting:** Only the specific `/charts` directory is accessible for writing output.

## Limitations
- **Data Scope:** The agent can only answer questions answerable by the current database schema (`Members`, `Loans`, `Accounts`).
- **Visuals:** Currently supports static image generation (.png). Interactive dashboards are not yet supported.
- **Hallucination:** While low (due to Temperature=0), the agent may occasionally misinterpret complex SQL logic.

## Ethical Considerations
- **PII:** The current database contains synthetic (fake) data. In a production environment, strict PII masking would be required before passing schema info to the LLM.