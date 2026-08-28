#!/bin/bash

PROJECT="$HOME/SIH_ALL/AgniRakshak"
PYTHON="/opt/anaconda3/bin/python"
UVICORN="/opt/anaconda3/bin/uvicorn"
STREAMLIT="/opt/anaconda3/bin/streamlit"

cd "$PROJECT"

# Start backend only if it is not already running
if ! pgrep -f "uvicorn src.api:app" >/dev/null 2>&1; then
    nohup "$UVICORN" src.api:app --host 127.0.0.1 --port 8000 \
        > /tmp/thermoscope_api.log 2>&1 &
fi

# Start dashboard only if it is not already running
if ! pgrep -f "streamlit run src/dashboard.py" >/dev/null 2>&1; then
    nohup "$STREAMLIT" run src/dashboard.py \
        --server.headless true \
        --server.address 127.0.0.1 \
        --server.port 8501 \
        > /tmp/thermoscope_dashboard.log 2>&1 &
fi

# Wait until dashboard is ready
for i in {1..60}; do
    if curl -s http://127.0.0.1:8501/_stcore/health >/dev/null 2>&1; then
        open "http://127.0.0.1:8501"
        exit 0
    fi
    sleep 0.5
done

open "http://127.0.0.1:8501"
