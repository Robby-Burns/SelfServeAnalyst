import operator
from typing import Annotated, TypedDict, Union
from dotenv import load_dotenv

# LangChain Imports (Only the ones we know work)
from langchain_openai import ChatOpenAI
from langchain_community.utilities import SQLDatabase
from langchain_community.agent_toolkits.sql.toolkit import SQLDatabaseToolkit
from langchain_community.agent_toolkits.sql.base import create_sql_agent
from langchain.tools import tool
from langgraph.graph import StateGraph, END

# Docker Setup
import docker

client = docker.from_env()
container = client.containers.get("sandbox")

load_dotenv()

# --- PART 1: DEFINE THE TOOLS ---

db = SQLDatabase.from_uri("sqlite:///credit_union.db")
llm = ChatOpenAI(model="gpt-4o", temperature=0)
sql_toolkit = SQLDatabaseToolkit(db=db, llm=llm)


@tool
def python_sandbox_tool(code: str) -> str:
    """Executes Python code in Docker. Use this ONLY for creating charts."""
    print(f"\n[VISUALIZER] Sending code to Docker...")
    try:
        exec_result = container.exec_run(cmd=["python", "-c", code], workdir="/workspace")
        output = exec_result.output.decode("utf-8")
        if exec_result.exit_code != 0:
            return f"Error: {output}"
        return output
    except Exception as e:
        return f"Docker Error: {e}"


# --- PART 2: DEFINE THE AGENTS (The Fix) ---

# Agent A: The Pure SQL Analyst
# We create this exactly like we did in Step 5
sql_analyst_executor = create_sql_agent(
    llm=llm,
    toolkit=sql_toolkit,
    verbose=True,
    agent_type="openai-tools",
    # We give it a specific persona
    suffix="You are a strict Data Analyst. Answer using text and numbers only."
)

# Agent B: The Visualizer
# We reuse create_sql_agent, but we INJECT the Python tool into it
visualizer_executor = create_sql_agent(
    llm=llm,
    toolkit=sql_toolkit,
    verbose=True,
    agent_type="openai-tools",
    extra_tools=[python_sandbox_tool],  # <--- This gives it the "Superpower"
    suffix="""
    You are a Data Visualizer. 
    1. Query data using SQL. 
    2. Use 'python_sandbox_tool' to plot it.
    3. ALWAYS save charts as 'final_chart.png'. Do not use plt.show().
    """
)


# --- PART 3: DEFINE THE GRAPH ---

class AgentState(TypedDict):
    question: str
    answer: str


def router_node(state: AgentState):
    """The Boss. Decides which path to take."""
    question = state["question"]
    print(f"\n[ROUTER] Analyzing request: '{question}'")

    # Simple keyword routing for reliability
    # In production, use the LLM to classify this
    classification = "SQL"
    if any(word in question.lower() for word in ["chart", "plot", "graph", "visualize"]):
        classification = "CHART"

    print(f"[ROUTER] Decision: {classification}")
    return {"classification": classification}


def sql_analyst_node(state: AgentState):
    print("--> Routing to SQL Analyst")
    response = sql_analyst_executor.invoke(state["question"])
    return {"answer": response["output"]}


def visualizer_node(state: AgentState):
    print("--> Routing to Visualizer")
    response = visualizer_executor.invoke(state["question"])
    return {"answer": response["output"]}


# --- PART 4: BUILD & COMPILE ---

workflow = StateGraph(AgentState)

workflow.add_node("sql_analyst", sql_analyst_node)
workflow.add_node("visualizer", visualizer_node)


def route_logic(state):
    # This logic runs AFTER the router_node implies the logic
    # But for LangGraph simple flow, we check the question again or pass state
    # To keep it simple, we duplicate the check here
    question = state["question"]
    if any(word in question.lower() for word in ["chart", "plot", "graph", "visualize"]):
        return "visualizer"
    else:
        return "sql_analyst"


workflow.set_conditional_entry_point(
    route_logic,
    {
        "sql_analyst": "sql_analyst",
        "visualizer": "visualizer"
    }
)

workflow.add_edge("sql_analyst", END)
workflow.add_edge("visualizer", END)

app = workflow.compile()

# --- PART 5: RUN IT ---

print("--- CREDIT UNION MULTI-AGENT TEAM ---")
print("Ask a question (SQL) or request a Chart (Visualizer).")

while True:
    user_input = input("\n> ")
    if user_input.lower() in ["quit", "exit"]: break

    result = app.invoke({"question": user_input})
    print(f"\nFINAL ANSWER: {result['answer']}")