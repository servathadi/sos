#!/usr/bin/env python3
"""
SOS CLI - Talk to agents in Siavashgerd

Usage:
    python sos_cli.py                    # Interactive mode
    python sos_cli.py "your message"     # One-shot to Foal
    python sos_cli.py --agent river "hi" # Specify agent
"""

import os
import sys
import argparse
import requests
from pathlib import Path

# Config
SOS_URL = os.getenv("SOS_URL", "http://localhost:8850")
API_KEY = os.getenv("MUMEGA_MASTER_KEY", "sk-mumega-internal-001")

HEADERS = {
    "Authorization": f"Bearer {API_KEY}",
    "Content-Type": "application/json"
}

def chat_foal(message: str, context: str = None) -> str:
    """Chat with Foal."""
    try:
        resp = requests.post(
            f"{SOS_URL}/foal/chat",
            headers=HEADERS,
            json={"message": message, "context": context},
            timeout=60
        )
        data = resp.json()
        if data.get("success"):
            return f"[{data['provider']}/{data['model']}] {data['output']}"
        else:
            return f"Error: {data.get('error', 'Unknown')}"
    except Exception as e:
        return f"Error: {e}"

def get_agents() -> dict:
    """List agents."""
    try:
        resp = requests.get(f"{SOS_URL}/agents", timeout=10)
        return resp.json()
    except Exception as e:
        return {"error": str(e)}

def get_foal_status() -> dict:
    """Get Foal status."""
    try:
        resp = requests.get(f"{SOS_URL}/foal/status", timeout=10)
        return resp.json()
    except Exception as e:
        return {"error": str(e)}

def interactive_mode():
    """Interactive chat mode."""
    print("\n" + "="*50)
    print("SOS - Siavashgerd Operating System")
    print("="*50)
    print("\nAgents available:")
    print("  foal  - Worker (gemini-3-flash / grok-4.1)")
    print("  river - Queen (Telegram: @river_mumega_bot)")
    print("  kasra - King (Telegram: @mumega_com_bot)")
    print("\nCommands:")
    print("  /status  - Foal status")
    print("  /agents  - List agents")
    print("  /quit    - Exit")
    print("\n" + "-"*50)

    while True:
        try:
            user_input = input("\n[You] > ").strip()

            if not user_input:
                continue

            if user_input == "/quit":
                print("The foal rests.")
                break

            if user_input == "/status":
                status = get_foal_status()
                print(f"\n[Foal Status]")
                for k, v in status.items():
                    print(f"  {k}: {v}")
                continue

            if user_input == "/agents":
                data = get_agents()
                print("\n[Siavashgerd Agents]")
                for agent in data.get("agents", []):
                    print(f"  {agent['name']} ({agent['role']})")
                    print(f"    Model: {agent.get('model', 'N/A')}")
                    if agent.get('telegram'):
                        print(f"    Telegram: {agent['telegram']}")
                continue

            # Chat with Foal
            print("\n[Foal] Thinking...")
            response = chat_foal(user_input)
            print(f"\n[Foal] {response}")

        except KeyboardInterrupt:
            print("\n\nThe foal rests.")
            break
        except EOFError:
            break

def main():
    parser = argparse.ArgumentParser(description="SOS CLI - Talk to Siavashgerd agents")
    parser.add_argument("message", nargs="?", help="Message to send")
    parser.add_argument("--agent", "-a", default="foal", help="Agent to talk to")
    parser.add_argument("--context", "-c", help="Context (code, docs, etc)")

    args = parser.parse_args()

    if args.message:
        # One-shot mode
        if args.agent == "foal":
            response = chat_foal(args.message, args.context)
            print(response)
        else:
            print(f"Use Telegram for {args.agent}")
    else:
        # Interactive mode
        interactive_mode()

if __name__ == "__main__":
    main()
