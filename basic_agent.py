import os
from dotenv import load_dotenv
from langchain_openai import ChatOpenAI
from langchain_community.utilities import SQLDatabase
from langchain_community.agent_toolkits.sql.toolkit import SQLDatabaseToolkit
from langchain_community.agent_toolkits.sql.base import create_sql_agent
from langchain_experimental.tools import PythonREPLTool  # <--- NEW IMPORT

# 1. Init
load_dotenv()
db = SQLDatabase.from_uri("sqlite:///credit_union.db")
llm = ChatOpenAI(model="gpt-4o", temperature=0)

# 2. Setup Tools
sql_toolkit = SQLDatabaseToolkit(db=db, llm=llm)
python_tool = PythonREPLTool()  # <--- This is the "Safety Hazard" (Local execution)

# 3. Create the "Dual-Brain" Agent
# We add python_tool to 'extra_tools' so it has both SQL and Python powers.
agent_executor = create_sql_agent(
    llm=llm,
    toolkit=sql_toolkit,
    verbose=True,
    agent_type="openai-tools",
    extra_tools=[python_tool],  # <--- Giving it the power to code
    suffix="""
    If the user asks for a chart or graph:
    1. Query the data using SQL.
    2. Use the 'python_repl_ast' tool to draw the plot using matplotlib.
    3. Save the image as 'chart.png' in the current directory.
    4. Do not try to show the plot, just save it.
    """
)

# 4. The Loop
print("--- CREDIT UNION AI ANALYST (SQL + PYTHON) ---")
print("I can now Query Data AND Generate Charts.")
print("WARNING: Running in Unsafe Local Mode.")

while True:
    user_input = input("\n> ")
    if user_input.lower() in ["exit", "quit"]:
        break

    try:
        response = agent_executor.invoke(user_input)
        print(f"\nANSWER: {response['output']}")
    except Exception as e:
        print(f"Error: {e}")