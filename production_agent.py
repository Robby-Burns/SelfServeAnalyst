import docker
import re
from dotenv import load_dotenv
from langchain_openai import ChatOpenAI
from langchain_community.utilities import SQLDatabase
from langchain_community.agent_toolkits.sql.toolkit import SQLDatabaseToolkit
from langchain_community.agent_toolkits.sql.base import create_sql_agent
from langchain.tools import tool

# 1. SETUP
load_dotenv()
client = docker.from_env()
container = client.containers.get("sandbox")  # Connects to our running Docker container

db = SQLDatabase.from_uri("sqlite:///credit_union.db")
llm = ChatOpenAI(model="gpt-4o", temperature=0)


# 2. DEFINE THE SAFE TOOL
@tool
def python_sandbox_tool(code: str) -> str:
    """
    Executes Python code inside a secure Docker container.
    Use this tool for math, data analysis, or generating charts.
    Files saved to the current directory will be visible to the user.
    """
    print(f"\n[SANDBOX] Executing code in Docker:\n{code}\n")

    # Run the code inside the container
    # We wrap it in a try/except block inside the container execution to capture errors
    exec_result = container.exec_run(
        cmd=["python", "-c", code],
        workdir="/workspace"
    )

    output = exec_result.output.decode("utf-8")

    if exec_result.exit_code != 0:
        return f"Error executing code: {output}"
    return output


# 3. CONFIGURE THE AGENT
sql_toolkit = SQLDatabaseToolkit(db=db, llm=llm)

# We combine SQL tools + our new Docker Tool
tools = sql_toolkit.get_tools() + [python_sandbox_tool]

# We need a customized system prompt to tell the agent how to use the Docker tool
system_message = """
You are a Senior Financial Analyst for a Credit Union. 
You have access to a SQL database and a Python Sandbox environment.

RULES:
1. For simple data retrieval ("How many members?"), use SQL.
2. For complex math or visualizations ("Plot the loan types"), use the 'python_sandbox_tool'.
3. When creating charts using Python:
   - Use 'matplotlib.pyplot'.
   - ALWAYS save the figure using `plt.savefig('filename.png')`.
   - Do NOT use `plt.show()`.
   - Inform the user that the file has been saved.
"""

agent_executor = create_sql_agent(
    llm=llm,
    toolkit=sql_toolkit,
    extra_tools=[python_sandbox_tool],
    system_message=system_message,
    verbose=True,
    agent_type="openai-tools",
)

# 4. THE INTERACTIVE LOOP
print("--- CREDIT UNION AI ANALYST (SECURE MODE) ---")
print("Environment: Docker Sandbox Active")
print("Type 'exit' to quit.")

while True:
    user_input = input("\n> ")
    if user_input.lower() in ["exit", "quit"]:
        break

    try:
        response = agent_executor.invoke(user_input)
        print(f"\nANSWER: {response['output']}")
    except Exception as e:
        print(f"Error: {e}")