#!/bin/bash
# Quick dashboard launcher

echo "=========================================="
echo "🤖 Quant Scalping Bot - Dashboard"
echo "=========================================="
echo ""

cd "$(dirname "$0")/.."
source venv/bin/activate 2>/dev/null

echo "🚀 Starting dashboard..."
echo ""
echo "Dashboard URL: http://127.0.0.1:8000"
echo "API Docs:     http://127.0.0.1:8000/docs"
echo ""
echo "Press Ctrl+C to stop"
echo ""
echo "=========================================="

python3 scripts/start_dashboard.py
