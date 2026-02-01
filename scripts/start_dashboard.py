#!/usr/bin/env python3
"""
Start the dashboard server.
"""
import sys
sys.path.insert(0, '.')

from bot.dashboard import run_dashboard

if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="Start Quant Scalping Bot Dashboard")
    parser.add_argument("--host", default="127.0.0.1", help="Host to bind to")
    parser.add_argument("--port", type=int, default=8000, help="Port to listen on")

    args = parser.parse_args()

    print("=" * 60)
    print("🤖 Quant Scalping Bot Dashboard")
    print("=" * 60)
    print()
    print(f"Starting server on http://{args.host}:{args.port}")
    print("Press Ctrl+C to stop")
    print()

    run_dashboard(host=args.host, port=args.port)
