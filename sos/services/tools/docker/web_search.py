import os
import json
import sys
import argparse
from typing import Dict, Any, Optional

# Try imports for various providers
try:
    from tavily import TavilyClient
    TAVILY_AVAILABLE = True
except ImportError:
    TAVILY_AVAILABLE = False

try:
    from duckduckgo_search import DDGS
    DDGS_AVAILABLE = True
except ImportError:
    DDGS_AVAILABLE = False

def search_tavily(query: str, count: int, key: str) -> Dict[str, Any]:
    if not TAVILY_AVAILABLE:
        return {"error": "Tavily library not installed"}
    
    client = TavilyClient(api_key=key)
    try:
        response = client.search(
            query=query, 
            search_depth="basic", 
            max_results=count, 
            include_answer=True
        )
        results = [
            {"title": r.get("title"), "url": r.get("url"), "description": r.get("content")} 
            for r in response.get("results", [])
        ]
        return {
            "results": results,
            "answer": response.get("answer"),
            "provider": "Tavily"
        }
    except Exception as e:
        return {"error": str(e)}

def search_duckduckgo(query: str, count: int) -> Dict[str, Any]:
    if not DDGS_AVAILABLE:
        return {"error": "DuckDuckGo library not installed"}
    
    try:
        with DDGS() as ddgs:
            raw = list(ddgs.text(query, max_results=count))
            results = [
                {"title": r.get("title"), "url": r.get("href"), "description": r.get("body")} 
                for r in raw
            ]
            return {
                "results": results,
                "provider": "DuckDuckGo"
            }
    except Exception as e:
        return {"error": str(e)}

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("query", help="Search query")
    parser.add_argument("--count", type=int, default=5, help="Number of results")
    parser.add_argument("--provider", default="auto", help="Provider (tavily, ddg, auto)")
    args = parser.parse_args()

    # Provider Selection Logic
    provider = args.provider
    tavily_key = os.getenv("TAVILY_API_KEY")

    result = {"error": "No provider matched"}

    # specific provider requested
    if provider == "tavily":
        if not tavily_key:
            result = {"error": "Tavily key missing"}
        else:
            result = search_tavily(args.query, args.count, tavily_key)
    
    elif provider == "duckduckgo":
        result = search_duckduckgo(args.query, args.count)
    
    # Auto mode: Try Tavily -> Fallback to DDG
    elif provider == "auto":
        if tavily_key and TAVILY_AVAILABLE:
            result = search_tavily(args.query, args.count, tavily_key)
            if "error" in result:
                 # Fallback
                 result = search_duckduckgo(args.query, args.count)
                 result["note"] = "Fallback from Tavily"
        else:
            result = search_duckduckgo(args.query, args.count)
    
    # Dump result to stdout
    print(json.dumps(result))

if __name__ == "__main__":
    main()
