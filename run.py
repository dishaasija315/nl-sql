"""
Unified Command-Line Runner for NL-to-SQL Business Analyst Agent.
Supports launching CLI agent, FastAPI backend server, Streamlit frontend, and Pytest.
"""

import sys
import subprocess
import argparse


def run_cli():
    """Launch the interactive terminal agent."""
    from app.agent.graph import run_agent

    print("=" * 65)
    print("NL-to-SQL Business Analyst Agent (CLI)")
    print("=" * 65)
    print("Type your business question below. Type 'exit' or 'quit' to stop.\n")

    while True:
        try:
            question = input("\nQuestion: ").strip()
            if not question:
                continue
            if question.lower() in ("exit", "quit", "q"):
                print("\nGoodbye!")
                break

            print("\nProcessing...")
            result = run_agent(question)

            print("\n" + "-" * 65)
            print("Executive Summary:")
            print(result.get("answer") or "No answer could be generated.")
            print("-" * 65)
            print(f"Generated SQL:\n{result.get('sql_query')}")
            print(f"Results Count: {len(result.get('rows', []))} row(s)")
            if result.get("error"):
                print(f"Error: {result.get('error')}")
            print("-" * 65)

        except KeyboardInterrupt:
            print("\nSession ended.")
            break
        except Exception as e:
            print(f"\nError: {e}")


def run_api(host="0.0.0.0", port=8001, reload=True):
    """Launch the FastAPI backend server using uvicorn."""
    import uvicorn
    print(f"Starting FastAPI server on http://{host}:{port} ...")
    uvicorn.run("app.main:app", host=host, port=port, reload=reload)


def run_frontend():
    """Launch the Streamlit dashboard."""
    print("Starting Streamlit Frontend...")
    cmd = [sys.executable, "-m", "streamlit", "run", "frontend/streamlit_app.py"]
    subprocess.run(cmd)


def run_tests():
    """Run pytest test suite."""
    print("Running Pytest Test Suite...")
    cmd = [sys.executable, "-m", "pytest", "-v", "tests/"]
    subprocess.run(cmd)


def run_check():
    """Check database connectivity and print live schema."""
    from app.database.connection import test_connection
    from app.database.schema import get_database_schema

    print("Testing Database Connection...")
    if test_connection():
        print("\nIntrospected Live Schema:")
        print(get_database_schema(force_refresh=True))
    else:
        print("Could not connect to PostgreSQL. Check your Docker container and .env settings.")


def main():
    parser = argparse.ArgumentParser(
        description="NL-to-SQL Business Analyst CLI Launcher"
    )
    parser.add_argument(
        "command",
        choices=["cli", "api", "frontend", "test", "check"],
        nargs="?",
        default="cli",
        help="Command to run: 'cli' (default), 'api', 'frontend', 'test', 'check'",
    )
    parser.add_argument("--port", type=int, default=8001, help="Port for API server")
    parser.add_argument("--host", type=str, default="0.0.0.0", help="Host for API server")

    args = parser.parse_args()

    if args.command == "cli":
        run_cli()
    elif args.command == "api":
        run_api(host=args.host, port=args.port)
    elif args.command == "frontend":
        run_frontend()
    elif args.command == "test":
        run_tests()
    elif args.command == "check":
        run_check()


if __name__ == "__main__":
    main()
