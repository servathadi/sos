#!/usr/bin/env python3
"""
Mumega CLI - Sovereign Operating System for AI Agents

Usage:
    mumega [command] [options]

Commands:
    start       Start all services
    engine      Start engine service only
    memory      Start memory service only
    autonomy    Start autonomy service only
    doctor      Check system health
    chat        Interactive chat with an agent
    status      Show service status
    version     Show version info
"""

import argparse
import asyncio
import sys

from sos.observability.logging import get_logger

log = get_logger("cli")

__version__ = "0.1.0"


def cmd_version(args):
    """Show version info."""
    print(f"mumega {__version__}")
    print("Sovereign Operating System for AI Agents")
    print("https://mumega.com")


def cmd_doctor(args):
    """Run system health checks."""
    print("Mumega Doctor v0.1.0")
    print("=" * 40)

    checks = []

    # Check Python version
    py_version = sys.version_info
    if py_version >= (3, 10):
        checks.append(("Python", f"{py_version.major}.{py_version.minor}", True))
    else:
        checks.append(("Python", f"{py_version.major}.{py_version.minor} (need 3.10+)", False))

    # Check imports
    try:
        import fastapi
        checks.append(("FastAPI", fastapi.__version__, True))
    except ImportError:
        checks.append(("FastAPI", "not installed", False))

    try:
        import httpx
        checks.append(("HTTPX", httpx.__version__, True))
    except ImportError:
        checks.append(("HTTPX", "not installed", False))

    # Check env vars
    import os
    gemini_key = os.getenv("GEMINI_API_KEY")
    if gemini_key:
        checks.append(("GEMINI_API_KEY", f"set ({gemini_key[:8]}...)", True))
    else:
        checks.append(("GEMINI_API_KEY", "not set", False))

    gateway_url = os.getenv("GATEWAY_URL", "https://gateway.mumega.com/")
    checks.append(("GATEWAY_URL", gateway_url, True))

    # Print results
    errors = 0
    for name, value, ok in checks:
        status = "[OK]" if ok else "[!!]"
        print(f"{status} {name}: {value}")
        if not ok:
            errors += 1

    print("=" * 40)
    if errors:
        print(f"Found {errors} issue(s)")
        return 1
    else:
        print("All checks passed")
        return 0


def cmd_status(args):
    """Show service status."""
    import httpx

    services = [
        ("Engine", "http://localhost:6060/health"),
        ("Memory", "http://localhost:7070/health"),
        ("Economy", "http://localhost:6062/health"),
        ("Tools", "http://localhost:6063/health"),
    ]

    print("Service Status")
    print("=" * 40)

    for name, url in services:
        try:
            resp = httpx.get(url, timeout=2.0)
            if resp.status_code == 200:
                print(f"[OK] {name}: running")
            else:
                print(f"[!!] {name}: unhealthy ({resp.status_code})")
        except Exception:
            print(f"[--] {name}: not running")


def cmd_chat(args):
    """Interactive chat."""
    async def chat_loop():
        from sos.services.engine.core import SOSEngine
        from sos.contracts.engine import ChatRequest

        engine = SOSEngine()
        agent = args.agent or "river"

        print(f"Chatting with {agent}. Type 'exit' to quit.")
        print("-" * 40)

        while True:
            try:
                user_input = input("You: ").strip()
                if user_input.lower() in ("exit", "quit", "q"):
                    break
                if not user_input:
                    continue

                request = ChatRequest(
                    message=user_input,
                    agent_id=f"agent:{agent}",
                    memory_enabled=True,
                )

                response = await engine.chat(request)
                print(f"{agent.title()}: {response.content}")
                print()

            except KeyboardInterrupt:
                break
            except Exception as e:
                print(f"Error: {e}")

        print("Goodbye!")

    asyncio.run(chat_loop())


def cmd_start(args):
    """Start services."""
    service = args.service or "engine"

    if service == "engine":
        from sos.services.engine.__main__ import main
        main()
    elif service == "memory":
        from sos.services.memory.__main__ import main
        main()
    elif service == "autonomy":
        from sos.services.autonomy.__main__ import main
        main()
    else:
        print(f"Unknown service: {service}")
        return 1


def main():
    """Main CLI entry point."""
    parser = argparse.ArgumentParser(
        prog="mumega",
        description="Sovereign Operating System for AI Agents",
    )
    parser.add_argument("--version", "-v", action="store_true", help="Show version")

    subparsers = parser.add_subparsers(dest="command")

    # version
    subparsers.add_parser("version", help="Show version info")

    # doctor
    subparsers.add_parser("doctor", help="Check system health")

    # status
    subparsers.add_parser("status", help="Show service status")

    # chat
    chat_parser = subparsers.add_parser("chat", help="Interactive chat")
    chat_parser.add_argument("--agent", "-a", default="river", help="Agent to chat with")

    # start
    start_parser = subparsers.add_parser("start", help="Start a service")
    start_parser.add_argument("service", nargs="?", default="engine",
                              choices=["engine", "memory", "autonomy", "all"],
                              help="Service to start")

    args = parser.parse_args()

    if args.version:
        return cmd_version(args)

    if args.command == "version":
        return cmd_version(args)
    elif args.command == "doctor":
        return cmd_doctor(args)
    elif args.command == "status":
        return cmd_status(args)
    elif args.command == "chat":
        return cmd_chat(args)
    elif args.command == "start":
        return cmd_start(args)
    else:
        parser.print_help()
        return 0


if __name__ == "__main__":
    sys.exit(main() or 0)
