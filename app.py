import streamlit as st
import os
import glob
import docker
import sys
import subprocess
from dotenv import load_dotenv
from typing import TypedDict, Literal

# LangChain / LangGraph Imports
from langchain_openai import ChatOpenAI
from langchain_community.utilities import SQLDatabase
from langchain_community.agent_toolkits.sql.toolkit import SQLDatabaseToolkit
from langchain_community.agent_toolkits.sql.base import create_sql_agent
from langchain.tools import tool
from langgraph.graph import StateGraph, END

from setup_db import create_dummy_db

# --- 1. CONFIGURATION & CONSTANTS ---
st.set_page_config(page_title="Credit Union AI Analyst", page_icon="🏦", layout="wide")

load_dotenv()

CHART_DIR = "charts"
DOCKER_CONTAINER_NAME = "sandbox"
DOCKER_WORKDIR = "/workspace"

# DATABASE SETUP (Agnostic)
default_db = "sqlite:///credit_union.db"
DB_URI = os.getenv("DATABASE_URL", default_db)

os.makedirs(CHART_DIR, exist_ok=True)

# Auto-initialize SQLite database if not present
if DB_URI.startswith("sqlite:///"):
    db_file = DB_URI.replace("sqlite:///", "")
    if not os.path.exists(db_file):
        create_dummy_db()


# --- 2. SIDEBAR CONFIGURATION ---
with st.sidebar:
    st.header("⚙️ Configuration")

    env_api_key = (
        os.getenv("OPENROUTER_API_KEY")
        or os.getenv("OPENAI_API_KEY")
        or os.getenv("LLM_API_KEY")
        or ""
    )
    env_base_url = (
        os.getenv("OPENROUTER_BASE_URL")
        or os.getenv("OPENAI_API_BASE")
        or os.getenv("LLM_BASE_URL")
        or ("https://openrouter.ai/api/v1" if ("sk-or-" in env_api_key or os.getenv("OPENROUTER_API_KEY")) else "")
    )
    env_model = (
        os.getenv("LLM_MODEL")
        or os.getenv("DEFAULT_MODEL")
        or ("openai/gpt-4o" if "openrouter" in env_base_url else "gpt-4o")
    )

    api_key_input = st.text_input(
        "OpenRouter / OpenAI API Key",
        value=env_api_key,
        type="password",
        help="Enter your OpenRouter key (sk-or-v1-...) or OpenAI key"
    )

    model_options = [
        "openai/gpt-4o",
        "openai/gpt-4o-mini",
        "anthropic/claude-3.5-sonnet",
        "google/gemini-2.5-flash",
        "meta-llama/llama-3.3-70b-instruct",
        "gpt-4o",
        "gpt-4o-mini"
    ]
    default_idx = model_options.index(env_model) if env_model in model_options else 0
    model_choice = st.selectbox("LLM Model", model_options, index=default_idx)

    base_url_input = st.text_input(
        "API Base URL",
        value=env_base_url if env_base_url else ("https://openrouter.ai/api/v1" if "sk-or-" in api_key_input else ""),
        help="Leave empty for OpenAI, or use https://openrouter.ai/api/v1 for OpenRouter"
    )

    st.markdown("---")
    st.subheader("💡 Example Questions")
    st.markdown("""
    - *How many members do we have?*
    - *What is the total loan amount by loan type?*
    - *Plot the distribution of loans by status.*
    - *Show a bar chart of average account balances by account type.*
    """)


# --- 3. CORE LOGIC ---
@st.cache_resource
def get_docker_container():
    """Connects to the running Docker container if available, or returns None."""
    try:
        client = docker.from_env()
        container = client.containers.get(DOCKER_CONTAINER_NAME)
        return container
    except Exception:
        return None


def get_llm(api_key: str, model: str, base_url: str):
    """Builds the ChatOpenAI client supporting OpenAI, OpenRouter, or custom providers."""
    if not api_key:
        return None

    if not base_url and "sk-or-" in api_key:
        base_url = "https://openrouter.ai/api/v1"

    default_headers = {}
    if base_url and "openrouter" in base_url:
        default_headers = {
            "HTTP-Referer": os.getenv("APP_URL", "https://railway.app"),
            "X-Title": "Credit Union AI Analyst"
        }

    return ChatOpenAI(
        model=model,
        temperature=0,
        api_key=api_key,
        base_url=base_url if base_url else None,
        default_headers=default_headers if default_headers else None
    )


def build_engine(api_key: str, model: str, base_url: str):
    """Initializes LLM, DB, and Agents."""
    llm = get_llm(api_key, model, base_url)
    if not llm:
        return None, None

    db = SQLDatabase.from_uri(DB_URI)
    sql_toolkit = SQLDatabaseToolkit(db=db, llm=llm)

    # Visualization execution tool
    @tool
    def python_sandbox_tool(code: str) -> str:
        """Executes Python code for visualization."""
        container = get_docker_container()
        if container:
            try:
                result = container.exec_run(cmd=["python", "-c", code], workdir=DOCKER_WORKDIR)
                output = result.output.decode("utf-8")
                if result.exit_code != 0:
                    return f"Execution Error:\n{output}"
                return output if output else "Code executed successfully (no stdout)."
            except Exception as e:
                return f"Docker Error: {str(e)}"
        else:
            try:
                result = subprocess.run(
                    [sys.executable, "-c", code],
                    cwd=os.getcwd(),
                    capture_output=True,
                    text=True,
                    timeout=30
                )
                if result.returncode != 0:
                    return f"Execution Error:\n{result.stderr}\n{result.stdout}"
                return result.stdout if result.stdout else "Code executed successfully (no stdout)."
            except Exception as e:
                return f"System Error: {str(e)}"

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
            3. ALWAYS save charts to the '{CHART_DIR}' folder.
            4. Generate a unique snake_case filename (e.g., '{CHART_DIR}/loan_dist_v1.png').
            5. DO NOT use 'final_chart.png'.
            6. Do not use plt.show().
        """
    )

    return sql_agent, vis_agent


# --- 4. GRAPH DEFINITION ---
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
        keywords = ["chart", "plot", "graph", "visualize", "trend", "map", "distribution", "bar", "histogram"]
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


# --- 5. STREAMLIT UI ---

st.title("🏦 Self-Serve Credit Union Analyst")
st.caption("Ask natural language questions to query member data, loans, and generate real-time visualizations.")

effective_api_key = api_key_input.strip()

if not effective_api_key:
    st.warning("👈 **Please provide an API Key** in the sidebar (or set `OPENROUTER_API_KEY` in Railway Variables) to start querying.")
    st.info("💡 You can get an API key at [openrouter.ai](https://openrouter.ai/) or [platform.openai.com](https://platform.openai.com/).")
else:
    # Initialize Engine & Graph
    try:
        sql_agent, vis_agent = build_engine(effective_api_key, model_choice, base_url_input.strip())
        app_graph = create_graph(sql_agent, vis_agent)
    except Exception as e:
        st.error(f"❌ Failed to initialize AI Agent: {str(e)}")
        app_graph = None

    # Initialize Session State
    if "messages" not in st.session_state:
        st.session_state.messages = []

    # Display Chat History
    for message in st.session_state.messages:
        with st.chat_message(message["role"]):
            st.markdown(message["content"])
            if "image_path" in message and message["image_path"]:
                if os.path.exists(message["image_path"]):
                    st.image(message["image_path"])
                    file_name = os.path.basename(message["image_path"])
                    with open(message["image_path"], "rb") as file:
                        st.download_button(
                            label=f"⬇️ Download {file_name}",
                            data=file,
                            file_name=file_name,
                            mime="image/png",
                            key=f"hist_btn_{file_name}_{st.session_state.messages.index(message)}"
                        )

    # Handle Input
    if prompt := st.chat_input("Ask about members, loans, or trends..."):
        if not app_graph:
            st.error("Agent engine is not ready. Please verify your API Key.")
        else:
            st.session_state.messages.append({"role": "user", "content": prompt})
            with st.chat_message("user"):
                st.markdown(prompt)

            with st.chat_message("assistant"):
                with st.spinner("Analyzing data..."):
                    existing_charts = set(glob.glob(f"{CHART_DIR}/*.png"))

                    try:
                        response = app_graph.invoke({"question": prompt})
                        answer_text = response.get("answer", "No response generated.")
                    except Exception as e:
                        answer_text = f"❌ An error occurred: {str(e)}"

                    current_charts = set(glob.glob(f"{CHART_DIR}/*.png"))
                    new_charts = list(current_charts - existing_charts)
                    new_image_path = new_charts[0] if new_charts else None

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

                    st.session_state.messages.append({
                        "role": "assistant",
                        "content": answer_text,
                        "image_path": new_image_path
                    })