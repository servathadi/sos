from __future__ import annotations

import json
import os
import shlex
import sys
import tempfile
import time
from pathlib import Path
from typing import Any, Dict, List, Optional

import httpx
from fastapi import FastAPI, HTTPException, Request
from fastapi.responses import JSONResponse, PlainTextResponse
from pydantic import BaseModel, Field

from sos import __version__
from sos.contracts.tools import BUILTIN_TOOLS, ToolCategory, ToolDefinition
from sos.execution import SandboxPolicy, run_subprocess
from sos.kernel import CapabilityAction, Config
from sos.observability.logging import clear_context, get_logger, set_agent_context
from sos.observability.metrics import MetricsRegistry, render_prometheus
from sos.observability.tracing import TRACE_ID_HEADER, SPAN_ID_HEADER, TraceContext
from sos.plugins.registry import LoadedPlugin, PluginRegistry
from sos.plugins.manifest import verify_plugin_manifest_signature
from sos.services.common.auth import get_capability_from_request, require_capability
from sos.services.common.capability import CapabilityModel

SERVICE_NAME = "tools"
_START_TIME = time.time()

log = get_logger(SERVICE_NAME, min_level=os.getenv("SOS_LOG_LEVEL", "info"))

metrics = MetricsRegistry()
REQUEST_COUNT = metrics.counter(
    name="sos_requests_total",
    description="Total requests",
    label_names=("service", "status"),
)
REQUEST_DURATION = metrics.histogram(
    name="sos_request_duration_seconds",
    description="Request duration",
    label_names=("service",),
)


def _tool_to_dict(tool: ToolDefinition) -> Dict[str, Any]:
    return {
        "name": tool.name,
        "description": tool.description,
        "category": tool.category.value,
        "parameters": tool.parameters,
        "returns": tool.returns,
        "required_capability": tool.required_capability,
        "rate_limit": tool.rate_limit,
        "timeout_seconds": tool.timeout_seconds,
        "sandbox_required": tool.sandbox_required,
        "metadata": tool.metadata,
    }


class MCPServerModel(BaseModel):
    name: str
    url: str
    transport: str = "http"  # http | stdio | sse
    metadata: Dict[str, Any] = Field(default_factory=dict)
    capability: Optional[CapabilityModel] = None


class MCPServerInfoModel(BaseModel):
    name: str
    url: str
    transport: str
    status: str = "unknown"
    tools: List[str] = Field(default_factory=list)
    metadata: Dict[str, Any] = Field(default_factory=dict)


class MCPDiscoverRequestModel(BaseModel):
    tools: List[Dict[str, Any]] = Field(default_factory=list)
    capability: Optional[CapabilityModel] = None


_MCP_SERVERS: Dict[str, MCPServerInfoModel] = {}
_MCP_SERVER_TOOLS: Dict[str, Dict[str, ToolDefinition]] = {}

_PLUGINS: Dict[str, LoadedPlugin] = {}
_PLUGIN_TOOLS: Dict[str, Dict[str, ToolDefinition]] = {}
_PLUGIN_SIGNATURE_VERIFIED: Dict[str, bool] = {}
_PLUGIN_POLICY_RESULTS: Dict[str, Dict[str, Any]] = {}


class PluginInstallRequestModel(BaseModel):
    cid: str
    capability: Optional[CapabilityModel] = None


class PluginInfoModel(BaseModel):
    cid: str
    name: str
    version: str
    author: str
    trust_level: str
    description: str = ""
    tools: List[str] = Field(default_factory=list)
    signature: Optional[str] = None
    signature_verified: bool = False
    entrypoints: Dict[str, str] = Field(default_factory=dict)
    policy: Optional[Dict[str, Any]] = None


def _all_tools() -> List[ToolDefinition]:
    tools_by_name: Dict[str, ToolDefinition] = {t.name: t for t in BUILTIN_TOOLS}
    for server_tools in _MCP_SERVER_TOOLS.values():
        for tool in server_tools.values():
            tools_by_name.setdefault(tool.name, tool)
    for plugin_tools in _PLUGIN_TOOLS.values():
        for tool in plugin_tools.values():
            tools_by_name.setdefault(tool.name, tool)
    return list(tools_by_name.values())


def _tool_definition_from_payload(server_name: str, payload: Dict[str, Any]) -> ToolDefinition:
    name = payload.get("name")
    if not isinstance(name, str) or not name.strip():
        raise HTTPException(status_code=400, detail="invalid_tool_name")

    description = payload.get("description") or ""
    if not isinstance(description, str):
        description = str(description)

    category_raw = payload.get("category") or "custom"
    try:
        category = ToolCategory(str(category_raw))
    except ValueError:
        raise HTTPException(status_code=400, detail="invalid_tool_category")

    parameters = payload.get("parameters") or {"type": "object", "properties": {}}
    if not isinstance(parameters, dict):
        raise HTTPException(status_code=400, detail="invalid_tool_parameters")

    returns = payload.get("returns") or ""
    if not isinstance(returns, str):
        returns = str(returns)

    required_capability = payload.get("required_capability") or payload.get("requiredCapability") or "tool:execute"
    if not isinstance(required_capability, str):
        required_capability = str(required_capability)

    full_name = f"mcp.{server_name}.{name.strip()}"
    payload_metadata = payload.get("metadata") if isinstance(payload.get("metadata"), dict) else {}
    metadata = {
        **payload_metadata,
        "provider": "mcp",
        "server": server_name,
        "original_name": name.strip(),
    }

    timeout_seconds = payload.get("timeout_seconds") or payload.get("timeoutSeconds") or 30
    try:
        timeout_seconds = int(timeout_seconds)
    except Exception as e:
        raise HTTPException(status_code=400, detail="invalid_tool_timeout_seconds") from e

    sandbox_required = payload.get("sandbox_required")
    if sandbox_required is None:
        sandbox_required = True

    return ToolDefinition(
        name=full_name,
        description=description,
        category=category,
        parameters=parameters,
        returns=returns,
        required_capability=required_capability,
        rate_limit=payload.get("rate_limit") or payload.get("rateLimit"),
        timeout_seconds=timeout_seconds,
        sandbox_required=bool(sandbox_required),
        metadata=metadata,
    )

def _tool_definition_from_plugin(plugin: LoadedPlugin, payload: Dict[str, Any]) -> ToolDefinition:
    name = payload.get("name")
    if not isinstance(name, str) or not name.strip():
        raise HTTPException(status_code=400, detail="invalid_tool_name")

    description = payload.get("description") or ""
    if not isinstance(description, str):
        description = str(description)

    category_raw = payload.get("category") or "custom"
    try:
        category = ToolCategory(str(category_raw))
    except ValueError:
        raise HTTPException(status_code=400, detail="invalid_tool_category")

    parameters = payload.get("parameters") or {"type": "object", "properties": {}}
    if not isinstance(parameters, dict):
        raise HTTPException(status_code=400, detail="invalid_tool_parameters")

    returns = payload.get("returns") or ""
    if not isinstance(returns, str):
        returns = str(returns)

    required_capability = payload.get("required_capability") or payload.get("requiredCapability") or "tool:execute"
    if not isinstance(required_capability, str):
        required_capability = str(required_capability)

    full_name = f"plugin.{plugin.manifest.name}.{name.strip()}"
    payload_metadata = payload.get("metadata") if isinstance(payload.get("metadata"), dict) else {}
    metadata = {
        **payload_metadata,
        "provider": "plugin",
        "plugin_cid": plugin.cid,
        "plugin_name": plugin.manifest.name,
        "plugin_version": plugin.manifest.version,
        "original_name": name.strip(),
    }

    timeout_seconds = payload.get("timeout_seconds") or payload.get("timeoutSeconds") or 30
    try:
        timeout_seconds = int(timeout_seconds)
    except Exception as e:
        raise HTTPException(status_code=400, detail="invalid_tool_timeout_seconds") from e

    sandbox_required = payload.get("sandbox_required")
    if sandbox_required is None:
        sandbox_required = True

    return ToolDefinition(
        name=full_name,
        description=description,
        category=category,
        parameters=parameters,
        returns=returns,
        required_capability=required_capability,
        rate_limit=payload.get("rate_limit") or payload.get("rateLimit"),
        timeout_seconds=timeout_seconds,
        sandbox_required=bool(sandbox_required),
        metadata=metadata,
    )


def _env_truthy(name: str, default: str = "0") -> bool:
    return os.getenv(name, default).strip().lower() in {"1", "true", "yes", "on"}


def _tool_execution_enabled() -> bool:
    if _env_truthy("SOS_TOOLS_EXECUTION_ENABLED", "0"):
        return True
    try:
        return Config.load().is_feature_enabled("tool_execution")
    except Exception:
        return False


def _plugins_execution_enabled() -> bool:
    return _env_truthy("SOS_PLUGINS_EXECUTION_ENABLED", "0")


def _parse_policy_commands(raw: str) -> List[str]:
    raw = raw.strip()
    if not raw:
        return []
    if raw.startswith("["):
        payload = json.loads(raw)
        if not isinstance(payload, list):
            raise ValueError("SOS_PLUGINS_POLICY_COMMANDS must be a list")
        return [str(cmd).strip() for cmd in payload if str(cmd).strip()]
    return [cmd.strip() for cmd in raw.split(";") if cmd.strip()]


def _load_plugin_policy_commands() -> List[str]:
    file_path = os.getenv("SOS_PLUGINS_POLICY_COMMANDS_FILE", "").strip()
    if file_path:
        lines = Path(file_path).expanduser().read_text(encoding="utf-8").splitlines()
        return [line.strip() for line in lines if line.strip()]
    raw = os.getenv("SOS_PLUGINS_POLICY_COMMANDS", "")
    if not raw.strip():
        return []
    return _parse_policy_commands(raw)


def _plugin_policy_config() -> Dict[str, Any]:
    return {
        "timeout_seconds": float(os.getenv("SOS_PLUGINS_POLICY_TIMEOUT_SECONDS", "30") or 30),
        "output_limit": int(os.getenv("SOS_PLUGINS_POLICY_OUTPUT_LIMIT", "2000") or 2000),
        "enforce": os.getenv("SOS_PLUGINS_POLICY_ENFORCE"),
        "commands": _load_plugin_policy_commands(),
    }


def _run_plugin_policy_gate(plugin: LoadedPlugin) -> Dict[str, Any]:
    cfg = _plugin_policy_config()
    commands: List[str] = cfg["commands"]
    if not commands:
        return {"passed": True, "issues": [], "command_results": []}

    issues: List[str] = []
    results: List[Dict[str, Any]] = []
    output_limit: int = cfg["output_limit"]

    for command in commands:
        started = time.perf_counter()
        try:
            args = shlex.split(command)
        except ValueError:
            issues.append(f"Invalid policy command: {command}")
            results.append({"command": command, "error": "invalid_command"})
            continue

        policy = SandboxPolicy(
            timeout_seconds=float(cfg["timeout_seconds"]),
            env_allowlist=[],
            extra_env={
                "SOS_PLUGIN_CID": plugin.cid,
                "SOS_PLUGIN_NAME": plugin.manifest.name,
                "SOS_PLUGIN_VERSION": plugin.manifest.version,
                "SOS_PLUGIN_DIR": str(plugin.files_dir),
            },
        )
        result = run_subprocess(args, policy=policy, cwd=plugin.files_dir)
        duration_ms = int((time.perf_counter() - started) * 1000)

        entry = {
            "command": command,
            "success": result.success,
            "exit_code": result.exit_code,
            "stdout": (result.stdout or "")[:output_limit],
            "stderr": (result.stderr or "")[:output_limit],
            "duration_ms": duration_ms,
            "error": result.error,
        }
        results.append(entry)
        if not result.success:
            issues.append(f"Policy command failed: {command}")

    passed = not issues
    return {"passed": passed, "issues": issues, "command_results": results}


def _allowed_path_roots() -> List[Path]:
    raw = os.getenv("SOS_TOOL_ALLOWED_ROOTS", "").strip()
    if raw:
        roots = [Path(p.strip()).expanduser().resolve() for p in raw.split(",") if p.strip()]
        if roots:
            return roots
    return [Config.load().paths.home.resolve()]


def _resolve_tool_path(path_str: str) -> Path:
    base_dir = Path(os.getenv("SOS_TOOL_BASE_DIR", str(Config.load().paths.home))).expanduser().resolve()
    p = Path(path_str).expanduser()
    if not p.is_absolute():
        p = base_dir / p
    return p.resolve()


def _ensure_within_allowed_roots(path: Path, roots: List[Path]) -> None:
    for root in roots:
        if root == path or root in path.parents:
            return
    raise HTTPException(status_code=403, detail="path_outside_allowed_roots")


def _plugin_info(plugin: LoadedPlugin, *, signature_verified: bool) -> PluginInfoModel:
    tools = []
    tool_map = _PLUGIN_TOOLS.get(plugin.cid) or {}
    tools = sorted(tool_map.keys())
    return PluginInfoModel(
        cid=plugin.cid,
        name=plugin.manifest.name,
        version=plugin.manifest.version,
        author=plugin.manifest.author,
        trust_level=plugin.manifest.trust_level,
        description=plugin.manifest.description,
        tools=tools,
        signature=plugin.manifest.signature,
        signature_verified=signature_verified,
        entrypoints=dict(plugin.manifest.entrypoints),
        policy=_PLUGIN_POLICY_RESULTS.get(plugin.cid),
    )


def _verify_plugin_manifest_if_configured(plugin: LoadedPlugin) -> bool:
    require_sigs = _env_truthy("SOS_PLUGINS_REQUIRE_SIGNATURES", "0")
    verify_key_hex = os.getenv("SOS_PLUGINS_VERIFY_KEY_HEX")
    if require_sigs and not verify_key_hex:
        raise HTTPException(status_code=500, detail="plugin_verify_key_not_configured")

    if not verify_key_hex:
        return False
    if not require_sigs and not plugin.manifest.signature:
        return False

    try:
        verify_key = bytes.fromhex(verify_key_hex)
    except ValueError:
        raise HTTPException(status_code=500, detail="invalid_plugin_verify_key_hex")

    ok, reason = verify_plugin_manifest_signature(plugin.manifest, verify_key)
    if not ok:
        raise HTTPException(status_code=401, detail=reason)
    return True


def _load_plugin_tools(plugin: LoadedPlugin) -> Dict[str, ToolDefinition]:
    tools_relpath = plugin.manifest.entrypoints.get("tools")
    if not tools_relpath:
        return {}

    tools_path = (plugin.files_dir / tools_relpath).resolve()
    if plugin.files_dir.resolve() not in tools_path.parents and tools_path != plugin.files_dir.resolve():
        raise HTTPException(status_code=400, detail="invalid_tools_entrypoint_path")

    if not tools_path.exists():
        raise HTTPException(status_code=404, detail="plugin_tools_file_not_found")

    try:
        data = json.loads(tools_path.read_text(encoding="utf-8"))
    except Exception as e:
        raise HTTPException(status_code=400, detail="invalid_plugin_tools_json") from e

    if not isinstance(data, list):
        raise HTTPException(status_code=400, detail="invalid_plugin_tools_list")

    tools: Dict[str, ToolDefinition] = {}
    for item in data:
        if not isinstance(item, dict):
            raise HTTPException(status_code=400, detail="invalid_plugin_tool_item")
        tool = _tool_definition_from_plugin(plugin, item)
        tools[tool.name] = tool

    return tools


def _execute_plugin_tool(plugin: LoadedPlugin, *, tool: ToolDefinition, arguments: Dict[str, Any]) -> Dict[str, Any]:
    executor = plugin.manifest.entrypoints.get("execute")
    if not executor:
        raise HTTPException(status_code=501, detail="plugin_executor_not_configured")

    if executor.startswith("python:"):
        rel = executor.split(":", 1)[1].strip()
        script_path = (plugin.files_dir / rel).resolve()
        if plugin.files_dir.resolve() not in script_path.parents and script_path != plugin.files_dir.resolve():
            raise HTTPException(status_code=400, detail="invalid_plugin_executor_path")
        if not script_path.exists():
            raise HTTPException(status_code=404, detail="plugin_executor_not_found")

        request_payload = {
            "tool": tool.metadata.get("original_name") or tool.name,
            "arguments": arguments,
            "plugin": {
                "cid": plugin.cid,
                "name": plugin.manifest.name,
                "version": plugin.manifest.version,
            },
        }
        input_text = json.dumps(request_payload, separators=(",", ":"), sort_keys=True)
        policy = SandboxPolicy(
            timeout_seconds=float(tool.timeout_seconds),
            env_allowlist=[],
            extra_env={
                "SOS_PLUGIN_CID": plugin.cid,
                "SOS_PLUGIN_NAME": plugin.manifest.name,
                "SOS_PLUGIN_VERSION": plugin.manifest.version,
            },
        )
        result = run_subprocess([sys.executable, str(script_path)], policy=policy, cwd=plugin.files_dir, input_text=input_text)

        stdout = result.stdout.strip()
        if stdout:
            try:
                return json.loads(stdout)
            except Exception:
                # Allow plugins to print logs; parse last non-empty line as JSON.
                for line in reversed([l for l in stdout.splitlines() if l.strip()]):
                    try:
                        return json.loads(line)
                    except Exception:
                        continue

        raise HTTPException(status_code=502, detail="invalid_plugin_response")

    raise HTTPException(status_code=400, detail="unsupported_plugin_executor")


class ExecuteToolRequestModel(BaseModel):
    arguments: Dict[str, Any] = Field(default_factory=dict)
    agent_id: Optional[str] = None
    capability: Optional[CapabilityModel] = None


app = FastAPI(title="SOS Tools Service", version=__version__)


@app.middleware("http")
async def _observability_middleware(request: Request, call_next):
    ctx = TraceContext.from_headers(dict(request.headers))
    ctx.activate()

    if agent_id := request.headers.get("X-SOS-Agent-ID"):
        set_agent_context(agent_id)

    status_label = "success"
    with REQUEST_DURATION.labels(service=SERVICE_NAME).time():
        try:
            response = await call_next(request)
            status_label = "success" if response.status_code < 400 else "error"
        except Exception as e:
            status_label = "error"
            log.error("Unhandled exception", error=str(e), path=str(request.url.path))
            response = JSONResponse(status_code=500, content={"detail": "internal_error"})

    REQUEST_COUNT.labels(service=SERVICE_NAME, status=status_label).inc()
    response.headers[TRACE_ID_HEADER] = ctx.trace_id
    response.headers[SPAN_ID_HEADER] = ctx.span_id
    clear_context()
    return response


@app.get("/health")
async def health() -> Dict[str, Any]:
    return {
        "status": "ok",
        "version": __version__,
        "service": SERVICE_NAME,
        "uptime_seconds": time.time() - _START_TIME,
        "checks": {
            "registry": "ok",
            "mcp": "ok",
        },
        "stats": {
            "tools": len(_all_tools()),
            "mcp_servers": len(_MCP_SERVERS),
            "plugins": len(_PLUGINS),
        },
    }


@app.get("/metrics")
async def metrics_endpoint():
    return PlainTextResponse(
        render_prometheus(metrics),
        media_type="text/plain; version=0.0.4",
    )


@app.get("/tools")
async def list_tools() -> List[Dict[str, Any]]:
    return [_tool_to_dict(t) for t in _all_tools()]


@app.get("/tools/{tool_name}")
async def get_tool(tool_name: str) -> Dict[str, Any]:
    tool = next((t for t in _all_tools() if t.name == tool_name), None)
    if not tool:
        raise HTTPException(status_code=404, detail="tool_not_found")
    return _tool_to_dict(tool)


@app.get("/plugins")
async def list_plugins() -> List[Dict[str, Any]]:
    infos: List[PluginInfoModel] = []
    for cid, plugin in _PLUGINS.items():
        infos.append(_plugin_info(plugin, signature_verified=_PLUGIN_SIGNATURE_VERIFIED.get(cid, False)))
    infos.sort(key=lambda p: p.name)
    return [p.model_dump() for p in infos]


@app.post("/plugins")
async def install_plugin(request: PluginInstallRequestModel) -> PluginInfoModel:
    require_capability(
        request.capability,
        action=CapabilityAction.TOOL_REGISTER,
        resource=f"plugin:{request.cid}",
    )

    if request.cid in _PLUGINS:
        raise HTTPException(status_code=409, detail="plugin_already_installed")

    registry = PluginRegistry()
    try:
        plugin = registry.load(request.cid)
    except FileNotFoundError as e:
        raise HTTPException(status_code=404, detail="plugin_not_found") from e

    signature_verified = _verify_plugin_manifest_if_configured(plugin)
    plugin_tools = _load_plugin_tools(plugin)
    policy_result = _run_plugin_policy_gate(plugin)

    enforce_raw = os.getenv("SOS_PLUGINS_POLICY_ENFORCE")
    enforce = None if enforce_raw is None else _env_truthy("SOS_PLUGINS_POLICY_ENFORCE", "0")
    if enforce is None:
        enforce = True  # if commands are configured, enforce by default
    if enforce and not bool(policy_result.get("passed", False)):
        raise HTTPException(status_code=403, detail="plugin_policy_failed")

    _PLUGINS[request.cid] = plugin
    _PLUGIN_TOOLS[request.cid] = plugin_tools
    _PLUGIN_SIGNATURE_VERIFIED[request.cid] = signature_verified
    _PLUGIN_POLICY_RESULTS[request.cid] = policy_result
    return _plugin_info(plugin, signature_verified=signature_verified)


@app.get("/plugins/{cid}")
async def get_plugin(cid: str) -> PluginInfoModel:
    plugin = _PLUGINS.get(cid)
    if not plugin:
        raise HTTPException(status_code=404, detail="plugin_not_found")
    return _plugin_info(plugin, signature_verified=_PLUGIN_SIGNATURE_VERIFIED.get(cid, False))


@app.delete("/plugins/{cid}")
async def uninstall_plugin(cid: str, http_request: Request) -> Dict[str, Any]:
    require_capability(
        get_capability_from_request(http_request),
        action=CapabilityAction.TOOL_REGISTER,
        resource=f"plugin:{cid}",
    )

    existed = cid in _PLUGINS
    _PLUGINS.pop(cid, None)
    _PLUGIN_TOOLS.pop(cid, None)
    _PLUGIN_SIGNATURE_VERIFIED.pop(cid, None)
    _PLUGIN_POLICY_RESULTS.pop(cid, None)
    return {"deleted": existed}


@app.get("/mcp/servers")
async def list_mcp_servers() -> List[Dict[str, Any]]:
    servers = list(_MCP_SERVERS.values())
    servers.sort(key=lambda s: s.name)
    return [s.model_dump() for s in servers]


@app.post("/mcp/servers")
async def register_mcp_server(request: MCPServerModel) -> MCPServerInfoModel:
    require_capability(
        request.capability,
        action=CapabilityAction.TOOL_REGISTER,
        resource=f"mcp:server/{request.name}",
    )

    if request.name in _MCP_SERVERS:
        raise HTTPException(status_code=409, detail="mcp_server_already_registered")

    info = MCPServerInfoModel(
        name=request.name,
        url=request.url,
        transport=request.transport,
        status="registered",
        tools=[],
        metadata=request.metadata,
    )
    _MCP_SERVERS[request.name] = info
    _MCP_SERVER_TOOLS.setdefault(request.name, {})
    return info


@app.get("/mcp/servers/{server_name}")
async def get_mcp_server(server_name: str) -> MCPServerInfoModel:
    server = _MCP_SERVERS.get(server_name)
    if not server:
        raise HTTPException(status_code=404, detail="mcp_server_not_found")
    return server


@app.delete("/mcp/servers/{server_name}")
async def unregister_mcp_server(server_name: str, http_request: Request) -> Dict[str, Any]:
    require_capability(
        get_capability_from_request(http_request),
        action=CapabilityAction.TOOL_REGISTER,
        resource=f"mcp:server/{server_name}",
    )

    existed = server_name in _MCP_SERVERS
    _MCP_SERVERS.pop(server_name, None)
    _MCP_SERVER_TOOLS.pop(server_name, None)
    return {"deleted": existed}


@app.post("/mcp/servers/{server_name}/discover")
async def discover_mcp_tools(server_name: str, request: MCPDiscoverRequestModel) -> List[Dict[str, Any]]:
    require_capability(
        request.capability,
        action=CapabilityAction.TOOL_REGISTER,
        resource=f"mcp:server/{server_name}/discover",
    )

    server = _MCP_SERVERS.get(server_name)
    if not server:
        raise HTTPException(status_code=404, detail="mcp_server_not_found")

    mode = os.getenv("SOS_MCP_DISCOVERY_MODE", "manual").strip().lower()
    if mode == "manual":
        if not request.tools:
            raise HTTPException(status_code=400, detail="missing_tools")
        discovered = [_tool_definition_from_payload(server_name, p) for p in request.tools]
    elif mode == "http":
        if os.getenv("SOS_MCP_DISCOVERY_ENABLED", "0").strip().lower() not in {"1", "true", "yes", "on"}:
            raise HTTPException(status_code=501, detail="mcp_discovery_disabled")
        if server.transport != "http":
            raise HTTPException(status_code=400, detail="unsupported_mcp_transport")
        timeout = float(os.getenv("SOS_MCP_DISCOVERY_TIMEOUT_SECONDS", "1.0"))
        async with httpx.AsyncClient(timeout=timeout) as client:
            resp = await client.get(f"{server.url.rstrip('/')}/tools")
            resp.raise_for_status()
            data = resp.json()
        if not isinstance(data, list):
            raise HTTPException(status_code=400, detail="invalid_mcp_tool_list")
        discovered = [_tool_definition_from_payload(server_name, p) for p in data]
    else:
        raise HTTPException(status_code=400, detail="invalid_mcp_discovery_mode")

    tools_by_name: Dict[str, ToolDefinition] = {t.name: t for t in discovered}
    _MCP_SERVER_TOOLS[server_name] = tools_by_name
    server.tools = sorted(tools_by_name.keys())
    server.status = "discovered"
    return [_tool_to_dict(t) for t in tools_by_name.values()]


@app.post("/tools/{tool_name}/execute")
async def execute_tool(tool_name: str, request: ExecuteToolRequestModel, http_request: Request) -> Dict[str, Any]:
    tool = next((t for t in _all_tools() if t.name == tool_name), None)
    if not tool:
        raise HTTPException(status_code=404, detail="tool_not_found")

    try:
        required_action = CapabilityAction(tool.required_capability)
    except ValueError:
        raise HTTPException(status_code=500, detail="unknown_tool_required_capability")

    resource = f"tool:{tool.name}"
    resolved_path: Optional[Path] = None
    if required_action in {CapabilityAction.FILE_READ, CapabilityAction.FILE_WRITE}:
        path = request.arguments.get("path")
        if not isinstance(path, str) or not path:
            raise HTTPException(status_code=400, detail="missing_path_argument")
        resolved_path = _resolve_tool_path(path)
        _ensure_within_allowed_roots(resolved_path, _allowed_path_roots())
        resource = f"file:{resolved_path}"

    actor_id = request.agent_id or http_request.headers.get("X-SOS-Agent-ID")
    require_capability(
        request.capability,
        action=required_action,
        resource=resource,
        expected_subject=actor_id,
    )

    provider = tool.metadata.get("provider")
    if provider == "mcp":
        raise HTTPException(status_code=501, detail="mcp_tool_execution_not_implemented")

    if provider == "plugin":
        if not _tool_execution_enabled() or not _plugins_execution_enabled():
            raise HTTPException(status_code=501, detail="plugin_execution_not_enabled")

        plugin_cid = tool.metadata.get("plugin_cid")
        if not isinstance(plugin_cid, str) or not plugin_cid:
            raise HTTPException(status_code=500, detail="plugin_cid_missing")
        plugin = _PLUGINS.get(plugin_cid)
        if not plugin:
            raise HTTPException(status_code=500, detail="plugin_not_loaded")

        return _execute_plugin_tool(plugin, tool=tool, arguments=request.arguments)

    if not _tool_execution_enabled():
        raise HTTPException(status_code=501, detail="tool_execution_not_implemented")

    if tool.name == "read_file":
        if resolved_path is None:
            raise HTTPException(status_code=500, detail="resolved_path_missing")
        encoding = request.arguments.get("encoding") or "utf-8"
        if not isinstance(encoding, str) or not encoding:
            raise HTTPException(status_code=400, detail="invalid_encoding")
        try:
            content = resolved_path.read_text(encoding=encoding)
        except FileNotFoundError as e:
            raise HTTPException(status_code=404, detail="file_not_found") from e
        except Exception as e:
            raise HTTPException(status_code=400, detail="file_read_error") from e
        log.info("Tool executed", tool=tool.name, success=True)
        return {"success": True, "output": content}

    if tool.name == "write_file":
        if resolved_path is None:
            raise HTTPException(status_code=500, detail="resolved_path_missing")
        content = request.arguments.get("content")
        if not isinstance(content, str):
            raise HTTPException(status_code=400, detail="missing_content_argument")
        encoding = request.arguments.get("encoding") or "utf-8"
        if not isinstance(encoding, str) or not encoding:
            raise HTTPException(status_code=400, detail="invalid_encoding")
        try:
            resolved_path.parent.mkdir(parents=True, exist_ok=True)
            resolved_path.write_text(content, encoding=encoding)
        except Exception as e:
            raise HTTPException(status_code=400, detail="file_write_error") from e
        log.info("Tool executed", tool=tool.name, success=True)
        return {"success": True, "output": True}

    if tool.name == "execute_code":
        language = request.arguments.get("language") or "python"
        code = request.arguments.get("code")
        if not isinstance(language, str) or not language:
            raise HTTPException(status_code=400, detail="missing_language_argument")
        if not isinstance(code, str):
            raise HTTPException(status_code=400, detail="missing_code_argument")
        if language != "python":
            raise HTTPException(status_code=400, detail="unsupported_language")

        with tempfile.TemporaryDirectory(prefix="sos_sandbox_") as tmp:
            tmp_dir = Path(tmp)
            script = tmp_dir / "main.py"
            script.write_text(code, encoding="utf-8")
            policy = SandboxPolicy(timeout_seconds=float(tool.timeout_seconds))
            result = run_subprocess([sys.executable, str(script)], policy=policy, cwd=tmp_dir)

        log.info("Tool executed", tool=tool.name, success=result.success, duration_ms=result.duration_ms)
        return {
            "success": result.success,
            "output": result.stdout,
            "error": result.stderr or result.error,
            "duration_ms": result.duration_ms,
        }

    raise HTTPException(status_code=501, detail="tool_execution_not_implemented")
