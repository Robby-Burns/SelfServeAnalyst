import os
import sys
from streamlit.web import cli as stcli
from setup_db import create_dummy_db

if __name__ == "__main__":
    # Ensure database exists
    if not os.path.exists("credit_union.db"):
        create_dummy_db()

    port = os.environ.get("PORT", "8501")
    sys.argv = [
        "streamlit",
        "run",
        "app.py",
        f"--server.port={port}",
        "--server.address=0.0.0.0",
        "--server.headless=true",
        "--browser.gatherUsageStats=false",
    ]
    sys.exit(stcli.main())
