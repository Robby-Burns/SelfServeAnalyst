#!/bin/sh
set -e

# Setup database if missing
if [ ! -f "credit_union.db" ]; then
    echo "Initializing database..."
    python setup_db.py
fi

# Ensure PORT is defined (defaults to 8501 if unset)
PORT="${PORT:-8501}"
echo "Starting Streamlit on port $PORT..."

exec streamlit run app.py \
    --server.port="$PORT" \
    --server.address=0.0.0.0 \
    --server.headless=true \
    --server.enableCORS=false \
    --server.enableXsrfProtection=false \
    --browser.gatherUsageStats=false
