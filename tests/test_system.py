import pytest
import docker
import os
import sqlite3
from dotenv import load_dotenv  # <--- NEW IMPORT
from langchain_community.utilities import SQLDatabase

# Load environment to get the same DB as the App
load_dotenv()

# CONSTANTS
# Now the test uses the exact same DB defined in your .env
DB_URI = os.getenv("DATABASE_URL", "sqlite:///credit_union.db")
CONTAINER_NAME = "sandbox"


def test_database_connection():
    """1. Can we talk to the SQLite DB and see the tables?"""
    db = SQLDatabase.from_uri(DB_URI)
    tables = db.get_usable_table_names()

    print(f"\nFound tables: {tables}")

    assert "members" in tables, "Table 'members' is missing!"
    assert "loans" in tables, "Table 'loans' is missing!"
    assert "accounts" in tables, "Table 'accounts' is missing!"


def test_docker_infrastructure():
    """2. Is the Docker Engine running and is our container alive?"""
    client = docker.from_env()

    # Check if container exists
    try:
        container = client.containers.get(CONTAINER_NAME)
    except docker.errors.NotFound:
        pytest.fail(f"Container '{CONTAINER_NAME}' not found! Did you run the docker run command?")

    # Check if it's actually running
    assert container.status == "running", f"Container is in state: {container.status}, expected 'running'"


def test_docker_execution_logic():
    """3. Can the Docker container actually run Python code?"""
    client = docker.from_env()
    container = client.containers.get(CONTAINER_NAME)

    # Send a simple math calculation
    code = "print(10 + 10)"
    result = container.exec_run(cmd=["python", "-c", code], workdir="/workspace")

    output = result.output.decode("utf-8").strip()
    exit_code = result.exit_code

    assert exit_code == 0, f"Python script failed with error: {output}"
    assert output == "20", f"Expected '20', got '{output}'"


def test_chart_directory_permissions():
    """4. Can we write files to the charts folder?"""
    # Create the folder if it doesn't exist (simulating app start)
    if not os.path.exists("charts"):
        os.makedirs("charts")

    test_file = "charts/test_write.txt"

    # Try writing a file
    with open(test_file, "w") as f:
        f.write("test")

    assert os.path.exists(test_file)

    # Cleanup
    os.remove(test_file)