# 🏦 Self-Serve Credit Union AI Analyst

A secure, multi-agent AI platform that allows non-technical users to query financial data and generate visualizations using natural language.

## 🏗 Architecture

This project uses a **Multi-Agent Architecture** orchestrated by **LangGraph**:

1.  **Router:** Classifies user intent (Data Query vs. Visualization).
2.  **SQL Agent:** specialized in writing/executing SQL queries.
3.  **Visualizer Agent:** specialized in writing Python code for charts.
4.  **Docker Sandbox:** A secure, isolated environment where the AI executes code to prevent Remote Code Execution (RCE) risks on the host machine.

## 🚀 Features

- **Natural Language SQL:** Ask "How many members have a mortgage?" and get a precise number.
- **Auto-Visualization:** Ask "Plot the distribution of loan types" and get a generated PNG chart.
- **Secure Execution:** All Python code runs inside a Docker container.
- **Dynamic UI:** Built with Streamlit for a chat-like experience.

## 🛠️ Installation

### Prerequisites
- Python 3.10+
- Docker Desktop (Running)
- OpenAI API Key

### 1. Clone & Setup
```bash
git clone [https://github.com/YOUR_USERNAME/SelfServeAnalyst.git](https://github.com/YOUR_USERNAME/SelfServeAnalyst.git)
cd SelfServeAnalyst

# Create Virtual Env
python -m venv .venv
source .venv/bin/activate  # On Windows: .venv\Scripts\activate

# Install Dependencies
pip install -r requirements.txt