import streamlit as st
import os
import glob
import docker
from dotenv import load_dotenv
from typing import TypedDict, Literal

# LangChain / LangGraph Imports
from langchain_openai import ChatOpenAI
from langchain_community.utilities import SQLDatabase
from langchain_community.agent_toolkits.sql.toolkit import SQLDatabaseToolkit
from langchain_community.agent_toolkits.sql.base import create_sql_agent
from langchain.tools import tool
from langgraph.graph import StateGraph, END

# --- 1. CONFIGURATION & CONSTANTS ---
st.set_page_config(page_title="Credit Union AI Analyst", page_icon="🏦", layout="centered")

CHART_DIR = "charts"
DB_URI = "sqlite:///credit_union.db"
DOCKER_CONTAINER_NAME = "sandbox"
DOCKER_WORKDIR = "/workspace"

# Ensure charts directory exists
os.makedirs(CHART_DIR, exist_ok=True)

# Load Environment Variables
load_dotenv()


# --- 2. CORE LOGIC (Cached) ---
@st.cache_resource
def get_docker_container():
    """Connects to the running Docker container safely."""
    try:
        client = docker.from_env()
        container = client.containers.get(DOCKER_CONTAINER_NAME)
        return container
    except Exception as e:
        st.error(f"⚠️ Docker Error: Could not connect to container '{DOCKER_CONTAINER_NAME}'. Is it running?")
        st.stop()


@st.cache_resource
def build_engine():
    """Initializes LLM, DB, and Agents."""

    # 1. Setup Resources
    container = get_docker_container()
    db = SQLDatabase.from_uri(DB_URI)
    llm = ChatOpenAI(model="gpt-4o", temperature=0)
    sql_toolkit = SQLDatabaseToolkit(db=db, llm=llm)

    # 2. Define Custom Tools
    @tool
    def python_sandbox_tool(code: str) -> str:
        """Executes Python code in a Docker container for visualization."""
        try:
            # Execute code inside Docker
            result = container.exec_run(cmd=["python", "-c", code], workdir=DOCKER_WORKDIR)

            # FIX: Decode the bytes to string
            output = result.output.decode("utf-8")

            if result.exit_code != 0:
                return f"Execution Error:\n{output}"
            return output if output else "Code executed successfully (no stdout)."
        except Exception as e:
            return f"System Error: {str(e)}"

    # 3. Create Agents
    # Agent A: Pure SQL Analyst
    sql_agent = create_sql_agent(
        llm=llm,
        toolkit=sql_toolkit,
        verbose=True,
        agent_type="openai-tools",
        suffix="You are a strict Data Analyst. Answer using text and numbers only. Do not generate code."
    )

    # Agent B: Visualizer
    vis_agent = create_sql_agent(
        llm=llm,
        toolkit=sql_toolkit,
        verbose=True,
        agent_type="openai-tools",
        extra_tools=[python_sandbox_tool],
        suffix=f"""
            You are a Data Visualizer.
            1. Query data using SQL.
            2. Use 'python_sandbox_tool' to plot it using matplotlib/seaborn.
            3. ALWAYS save charts to the '{CHART_DIR}' folder inside the container.
            4. Generate a unique snake_case filename (e.g., '{CHART_DIR}/loan_dist_v1.png').
            5. DO NOT use 'final_chart.png'.
            6. Do not use plt.show().
        """
    )

    return sql_agent, vis_agent


# --- 3. GRAPH DEFINITION ---
class AgentState(TypedDict):
    question: str
    answer: str
    source: str


def create_graph(sql_agent, vis_agent):
    """Builds the LangGraph workflow."""

    def sql_node(state: AgentState):
        response = sql_agent.invoke(state["question"])
        return {"answer": response["output"], "source": "analyst"}

    def visualizer_node(state: AgentState):
        response = vis_agent.invoke(state["question"])
        return {"answer": response["output"], "source": "visualizer"}

    def route_logic(state) -> Literal["visualizer", "sql_analyst"]:
        q = state["question"].lower()
        keywords = ["chart", "plot", "graph", "visualize", "trend", "map"]
        if any(x in q for x in keywords):
            return "visualizer"
        return "sql_analyst"

    workflow = StateGraph(AgentState)
    workflow.add_node("sql_analyst", sql_node)
    workflow.add_node("visualizer", visualizer_node)

    workflow.set_conditional_entry_point(
        route_logic,
        {"sql_analyst": "sql_analyst", "visualizer": "visualizer"}
    )

    workflow.add_edge("sql_analyst", END)
    workflow.add_edge("visualizer", END)

    return workflow.compile()


# Initialize System
sql_agent, vis_agent = build_engine()
app_graph = create_graph(sql_agent, vis_agent)

# --- 4. STREAMLIT UI ---

st.title("🏦 Self-Serve Credit Union Analyst")

# Initialize Session State
if "messages" not in st.session_state:
    st.session_state.messages = []

# Display Chat History
for message in st.session_state.messages:
    with st.chat_message(message["role"]):
        st.markdown(message["content"])
        # Display Image if present in history
        if "image_path" in message and message["image_path"]:
            if os.path.exists(message["image_path"]):
                st.image(message["image_path"])

                # Download Button logic
                file_name = os.path.basename(message["image_path"])
                with open(message["image_path"], "rb") as file:
                    st.download_button(
                        label=f"⬇️ Download {file_name}",
                        data=file,
                        file_name=file_name,
                        mime="image/png",
                        key=f"hist_btn_{file_name}"
                    )

# Handle Input
if prompt := st.chat_input("Ask about members, loans, or trends..."):
    # 1. Add User Message
    st.session_state.messages.append({"role": "user", "content": prompt})
    with st.chat_message("user"):
        st.markdown(prompt)

    # 2. Run AI Logic
    with st.chat_message("assistant"):
        with st.spinner("Analyzing data..."):

            # Snapshot of existing charts to detect new ones
            existing_charts = set(glob.glob(f"{CHART_DIR}/*.png"))

            # Invoke Graph
            try:
                response = app_graph.invoke({"question": prompt})
                answer_text = response.get("answer", "No response generated.")
                source = response.get("source", "unknown")
            except Exception as e:
                answer_text = f"❌ An error occurred: {str(e)}"
                source = "error"

            # Detect if a new chart was created
            current_charts = set(glob.glob(f"{CHART_DIR}/*.png"))
            new_charts = list(current_charts - existing_charts)

            # Smart Detection: If we find a new file, grab it.
            # If multiple were made (rare), grab the last one.
            new_image_path = new_charts[0] if new_charts else None

            # 3. Display Response
            st.markdown(answer_text)

            if new_image_path:
                st.image(new_image_path)
                file_name = os.path.basename(new_image_path)
                with open(new_image_path, "rb") as file:
                    st.download_button(
                        label=f"⬇️ Download {file_name}",
                        data=file,
                        file_name=file_name,
                        mime="image/png",
                        key=f"new_btn_{file_name}"
                    )

            # 4. Save to History
            st.session_state.messages.append({
                "role": "assistant",
                "content": answer_text,
                "image_path": new_image_path
            })