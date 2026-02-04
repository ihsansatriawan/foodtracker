#!/usr/bin/env python3
"""
Run the Food Tracker Dashboard.

Usage:
    python run_dashboard.py [--host HOST] [--port PORT]
"""

import argparse
import uvicorn


def main():
    parser = argparse.ArgumentParser(description="Run Food Tracker Dashboard")
    parser.add_argument("--host", default="0.0.0.0", help="Host to bind to")
    parser.add_argument("--port", type=int, default=8080, help="Port to bind to")
    parser.add_argument("--reload", action="store_true", help="Enable auto-reload")
    args = parser.parse_args()

    print(f"Starting Food Tracker Dashboard at http://{args.host}:{args.port}")
    print("Press Ctrl+C to stop")

    uvicorn.run(
        "dashboard.main:app",
        host=args.host,
        port=args.port,
        reload=args.reload
    )


if __name__ == "__main__":
    main()
