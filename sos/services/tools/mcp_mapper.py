"""
MCP Mapper: Bridges Mirror Tools to Vertex AI
"""
import sys
import logging
from typing import List, Dict

# Add mirror to path
sys.path.append("/home/mumega/mirror")

log = logging.getLogger("mcp_mapper")

def get_vertex_tools() -> List[Dict]:
    """
    Imports RiverModel, extracts tools, and returns list of dicts.
    NOTE: These are now used for PROMPT GENERATION, not SDK binding.
    """
    try:
        from river_mcp_server import RiverModel
        try:
            river = RiverModel()
            genai_tools = river._define_tools()
        except Exception as e:
            log.warning(f"Could not instantiate RiverModel: {e}")
            return _fallback_tools()

        tools_list = []
        if genai_tools:
            for tool in genai_tools:
                for func in tool.function_declarations:
                    # Simplify schema for the prompt
                    params = {}
                    if hasattr(func.parameters, 'properties'):
                        for key, val in func.parameters.properties.items():
                            params[key] = val.description
                    
                    tool_def = {
                        "name": func.name,
                        "description": func.description,
                        "usage": f'{func.name}({", ".join(params.keys())})'
                    }
                    tools_list.append(tool_def)
                    
        return tools_list

    except Exception as e:
        log.error(f"MCP Mapper failed: {e}")
        return _fallback_tools()

def _fallback_tools() -> List[Dict]:
    """Critical tools if bridge fails."""
    return [
        {"name": "run_python", "description": "Execute Python code", "usage": "run_python(code)"},
        {"name": "web_search", "description": "Search the web", "usage": "web_search(query)"}
    ]
