#!/usr/bin/env python3
"""
Sovereign OS (SOS) CLI - The Thin Client 🌊

A lightweight interface to the Sovereign Swarm.
Connects to a local or remote SOS Engine to manage your Agent, Wallet, and Guild Identity.

Usage:
    ./sos_cli.py chat "Hello River"
    ./sos_cli.py status
    ./sos_cli.py wallet balance
    ./sos_cli.py identity mint --role Knight

Dependencies:
    pip install httpx rich
"""

import argparse
import asyncio
import json
import os
import sys
import time
from typing import Optional, Dict, Any

try:
    import httpx
except ImportError:
    print("❌ Error: 'httpx' is required. Run: pip install httpx")
    sys.exit(1)

try:
    from rich.console import Console
    from rich.markdown import Markdown
    from rich.panel import Panel
    from rich.table import Table
    from rich.live import Live
    console = Console()
except ImportError:
    class Console:
        def print(self, *args, **kwargs): print(*args)
        def input(self, prompt): return input(prompt)
    console = Console()
    def Markdown(x): return x
    def Panel(x, **kwargs): return x
    def Table(**kwargs): return "Table"

# Configuration
DEFAULT_HOST = os.getenv("SOS_ENGINE_URL", "http://localhost:8020")
AGENT_ID = os.getenv("SOS_AGENT_ID", "user_cli")

class SOSClient:
    def __init__(self, host: str, agent_id: str):
        self.host = host.rstrip("/")
        self.agent_id = agent_id
        self.client = httpx.AsyncClient(timeout=30.0)

    async def check_health(self):
        try:
            resp = await self.client.get(f"{self.host}/health")
            resp.raise_for_status()
            data = resp.json()
            
            # Display Health
            console.print(Panel(f"[bold green]Connected to {self.host}[/bold green]\n" 
                              f"Version: {data.get('version')}\n" 
                              f"Uptime: {data.get('uptime_seconds', 0):.1f}s",
                              title="SOS Link Established"))
            return True
        except Exception as e:
            console.print(f"[bold red]❌ Connection Failed:[/bold red] {e}")
            return False

    async def chat(self, message: str, model: str = None, stream: bool = True):
        url = f"{self.host}/chat"
        # If no model provided, engine will use default
        payload = {
            "message": message,
            "agent_id": self.agent_id,
            "stream": stream,
            "tools_enabled": True
        }
        if model:
            payload["model"] = model

        try:
            if stream:
                async with self.client.stream("POST", url, json=payload) as response:
                    print("", end="", flush=True) # visual separator
                    full_text = ""
                    async for chunk in response.aiter_text():
                        full_text += chunk
                        # Simple streaming output
                        sys.stdout.write(chunk)
                        sys.stdout.flush()
                    print("\n")
            else:
                resp = await self.client.post(url, json=payload)
                data = resp.json()
                console.print(Markdown(data.get("content", "")))
                
                if data.get("tool_calls"):
                    console.print(Panel(str(data["tool_calls"]), title="🛠️ Tools Used", border_style="yellow"))

        except Exception as e:
            console.print(f"[bold red]Chat Error:[/bold red] {e}")

    async def get_balance(self):
        # Requires Economy Service on separate port or routed via Engine
        # For Phase 3, we assume Engine routes it, or we hit Economy directly
        # Let's try direct economy port 8002 (standard) or via Engine router if implemented
        # Currently engine app.py doesn't route balance, so we hit economy directly for demo
        try:
            # TODO: Add routing to Engine for this
            console.print("[dim]Checking Economy Service directly (Port 8002)...[/dim]")
            resp = await self.client.get(f"http://localhost:8002/balance/{self.agent_id}")
            data = resp.json()
            console.print(Panel(f"[bold gold1]{data.get('balance')} RU[/bold gold1]", title="Wallet Balance"))
        except:
            console.print("[yellow]Economy Service unreachable.[/yellow]")

    async def mint_identity(self, role: str):
        try:
            # Identity Service on 8004? Or routed?
            # We haven't built the router yet, so direct hit for demo
            url = "http://localhost:8004/mint"
            resp = await self.client.post(url, json={"agent_id": self.agent_id, "role": role})
            data = resp.json()
            console.print(Panel(json.dumps(data, indent=2), title="🆔 Guild Pass Minted", border_style="cyan"))
        except Exception as e:
             console.print(f"[red]Minting failed: {e}[/red]")

async def main():
    parser = argparse.ArgumentParser(description="Sovereign OS Thin Client")
    parser.add_argument("command", choices=["chat", "status", "wallet", "identity"], help="Command to run")
    parser.add_argument("args", nargs="*", help="Arguments for the command")
    parser.add_argument("--host", default=DEFAULT_HOST, help="SOS Engine URL")
    parser.add_argument("--agent", default=AGENT_ID, help="Agent ID")
    parser.add_argument("--model", default=None, help="AI Model ID")
    
    args = parser.parse_args()
    
    client = SOSClient(args.host, args.agent)
    
    if args.command == "status":
        await client.check_health()
        
    elif args.command == "chat":
        if not args.args:
            console.print("[red]Please provide a message.[/red]")
            return
        message = " ".join(args.args)
        await client.chat(message, model=args.model)
        
    elif args.command == "wallet":
        await client.get_balance()
        
    elif args.command == "identity":
        subcmd = args.args[0] if args.args else "view"
        if subcmd == "mint":
            await client.mint_identity(role="Knight")
        else:
            console.print("Usage: identity mint")

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        pass
