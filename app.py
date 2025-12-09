import uvicorn
import argparse
import sys
import os

def main():
    parser = argparse.ArgumentParser(description="VantaSys - System Monitoring Dashboard")
    parser.add_argument("--host", default="127.0.0.1", help="Host to bind (default: 127.0.0.1)")
    parser.add_argument("--port", type=int, default=6767, help="Port to bind (default: 6767)")
    parser.add_argument("--reload", action="store_true", help="Enable auto-reload (dev mode)")
    
    args = parser.parse_args()

    # Ensure backend module is in path
    current_dir = os.path.dirname(os.path.abspath(__file__))
    sys.path.append(current_dir)

    print(f"Starting VantaSys on http://{args.host}:{args.port}")
    if args.reload:
        print("Auto-reload enabled")

    try:
        uvicorn.run(
            "backend.api:app",
            host=args.host,
            port=args.port,
            reload=args.reload,
            log_level="info"
        )
    except KeyboardInterrupt:
        print("Stopping VantaSys...")

if __name__ == "__main__":
    main()
