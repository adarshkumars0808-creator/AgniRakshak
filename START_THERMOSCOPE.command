#!/bin/bash

cd "$(dirname "$0")"

echo "=============================================="
echo "        THERMOSCOPE - STARTING"
echo "=============================================="
echo ""

echo "[1/2] Starting Backend API..."
uvicorn src.api:app --host 127.0.0.1 --port 8000 > /tmp/thermoscope_backend.log 2>&1 &
BACKEND_PID=$!

sleep 3

echo "[2/2] Starting Dashboard..."
streamlit run src/dashboard.py --server.address 127.0.0.1 --server.port 8501 > /tmp/thermoscope_dashboard.log 2>&1 &
DASHBOARD_PID=$!

sleep 5

echo ""
echo "=============================================="
echo "       THERMOSCOPE IS RUNNING"
echo "=============================================="
echo ""
echo "Backend:   http://127.0.0.1:8000"
echo "Dashboard: http://127.0.0.1:8501"
echo ""
echo "Opening dashboard..."
echo ""

open "http://127.0.0.1:8501"

echo "=============================================="
echo "Keep this window open while using Thermoscope."
echo "Press CTRL+C to stop."
echo "=============================================="

trap 'echo ""; echo "Stopping Thermoscope..."; kill $BACKEND_PID $DASHBOARD_PID 2>/dev/null; exit 0' INT TERM

wait
