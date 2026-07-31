from __future__ import annotations

import json
import sys
from typing import Any, Callable

from cli.config import CLIConfig


def _print_json(data: Any) -> None:
    print(json.dumps(data, indent=2, default=str))


async def _async_request(config: CLIConfig, method: str, path: str, body: Any = None, params: dict[str, Any] | None = None) -> Any:
    import httpx
    headers = {"Content-Type": "application/json"}
    if config.bearer_token:
        headers["Authorization"] = f"Bearer {config.bearer_token}"
    elif config.api_key:
        headers["X-API-Key"] = config.api_key

    async with httpx.AsyncClient(base_url=config.base_url, timeout=config.timeout, headers=headers, verify=config.verify_ssl) as client:
        resp = await client.request(method, path, json=body, params=params)
        if resp.status_code >= 400:
            print(f"API Error ({resp.status_code}): {resp.text}", file=sys.stderr)
            sys.exit(1)
        return resp.json() if resp.content else {}


def _run_async(coro: Any) -> Any:
    import asyncio
    return asyncio.run(coro)


def cmd_health(args: list[str], config: CLIConfig, headers: dict[str, str]) -> None:
    data = _run_async(_async_request(config, "GET", "/health"))
    _print_json(data)


def cmd_chat(args: list[str], config: CLIConfig, headers: dict[str, str]) -> None:
    if not args:
        print("Usage: nova chat <message> [--model MODEL]", file=sys.stderr)
        sys.exit(1)
    message = args[0]
    model = "default"
    for i, arg in enumerate(args):
        if arg == "--model" and i + 1 < len(args):
            model = args[i + 1]
    body = {"model": model, "messages": [{"role": "user", "content": message}]}
    data = _run_async(_async_request(config, "POST", "/models/chat", body))
    if "response" in data:
        print(data["response"].get("content", json.dumps(data["response"], default=str)))
    else:
        _print_json(data)


def cmd_execute(args: list[str], config: CLIConfig, headers: dict[str, str]) -> None:
    if not args:
        print("Usage: nova execute <task> [--agent AGENT_ID]", file=sys.stderr)
        sys.exit(1)
    task = args[0]
    agent_id = "default"
    for i, arg in enumerate(args):
        if arg == "--agent" and i + 1 < len(args):
            agent_id = args[i + 1]
    body = {"task": task, "agent_id": agent_id}
    data = _run_async(_async_request(config, "POST", "/kernel/execute", body))
    _print_json(data)


def cmd_workflow(args: list[str], config: CLIConfig, headers: dict[str, str]) -> None:
    sub = args[0] if args else "list"
    if sub == "list":
        data = _run_async(_async_request(config, "GET", "/workflows"))
        _print_json(data)
    elif sub == "create" and len(args) > 1:
        data = _run_async(_async_request(config, "POST", "/workflows", {"name": args[1]}))
        _print_json(data)
    elif sub == "execute" and len(args) > 1:
        data = _run_async(_async_request(config, "POST", "/workflows/executions", {"workflow_id": args[1]}))
        _print_json(data)
    elif sub == "health":
        data = _run_async(_async_request(config, "GET", "/workflows/health"))
        _print_json(data)
    else:
        print("Usage: nova workflow [list|create|execute|health] [args...]", file=sys.stderr)


def cmd_scheduler(args: list[str], config: CLIConfig, headers: dict[str, str]) -> None:
    sub = args[0] if args else "list"
    if sub == "list":
        data = _run_async(_async_request(config, "GET", "/scheduler/jobs"))
        _print_json(data)
    elif sub == "create" and len(args) > 1:
        data = _run_async(_async_request(config, "POST", "/scheduler/jobs", {"name": args[1]}))
        _print_json(data)
    elif sub == "statistics":
        data = _run_async(_async_request(config, "GET", "/scheduler/statistics"))
        _print_json(data)
    elif sub == "health":
        data = _run_async(_async_request(config, "GET", "/scheduler/health"))
        _print_json(data)
    else:
        print("Usage: nova scheduler [list|create|statistics|health] [args...]", file=sys.stderr)


def cmd_memory(args: list[str], config: CLIConfig, headers: dict[str, str]) -> None:
    if not args:
        print("Usage: nova memory <session_id>", file=sys.stderr)
        sys.exit(1)
    data = _run_async(_async_request(config, "GET", f"/memory/{args[0]}"))
    _print_json(data)


def cmd_goals(args: list[str], config: CLIConfig, headers: dict[str, str]) -> None:
    if len(args) < 2:
        print("Usage: nova goals <user_id> [list|create]", file=sys.stderr)
        sys.exit(1)
    user_id = args[0]
    sub = args[1] if len(args) > 1 else "list"
    if sub == "list":
        data = _run_async(_async_request(config, "GET", f"/goals/{user_id}"))
        _print_json(data)
    elif sub == "create" and len(args) > 2:
        data = _run_async(_async_request(config, "POST", f"/goals/{user_id}", {"title": args[2]}))
        _print_json(data)
    else:
        print("Usage: nova goals <user_id> [list|create <title>]", file=sys.stderr)


def cmd_tasks(args: list[str], config: CLIConfig, headers: dict[str, str]) -> None:
    sub = args[0] if args else "list"
    if sub == "list":
        data = _run_async(_async_request(config, "GET", "/tasks"))
        _print_json(data)
    elif sub == "create" and len(args) > 1:
        data = _run_async(_async_request(config, "POST", "/tasks", {"goal": args[1]}))
        _print_json(data)
    elif sub == "get" and len(args) > 1:
        data = _run_async(_async_request(config, "GET", f"/tasks/{args[1]}"))
        _print_json(data)
    else:
        print("Usage: nova tasks [list|create <goal>|get <id>]", file=sys.stderr)


def cmd_agents(args: list[str], config: CLIConfig, headers: dict[str, str]) -> None:
    sub = args[0] if args else "list"
    if sub == "list":
        data = _run_async(_async_request(config, "GET", "/agents"))
        _print_json(data)
    elif sub == "health":
        data = _run_async(_async_request(config, "GET", "/agents/health"))
        _print_json(data)
    elif sub == "capabilities":
        data = _run_async(_async_request(config, "GET", "/agents/capabilities"))
        _print_json(data)
    elif sub == "metrics":
        data = _run_async(_async_request(config, "GET", "/agents/runtime/metrics"))
        _print_json(data)
    else:
        print("Usage: nova agents [list|health|capabilities|metrics]", file=sys.stderr)


def cmd_plugins(args: list[str], config: CLIConfig, headers: dict[str, str]) -> None:
    sub = args[0] if args else "list"
    if sub == "list":
        data = _run_async(_async_request(config, "GET", "/plugins/"))
        _print_json(data)
    elif sub == "health":
        data = _run_async(_async_request(config, "GET", "/plugins/health"))
        _print_json(data)
    elif sub == "statistics":
        data = _run_async(_async_request(config, "GET", "/plugins/statistics"))
        _print_json(data)
    else:
        print("Usage: nova plugins [list|health|statistics]", file=sys.stderr)


def cmd_models(args: list[str], config: CLIConfig, headers: dict[str, str]) -> None:
    sub = args[0] if args else "list"
    if sub == "list":
        data = _run_async(_async_request(config, "GET", "/models/list"))
        _print_json(data)
    elif sub == "health":
        data = _run_async(_async_request(config, "GET", "/models/health"))
        _print_json(data)
    elif sub == "providers":
        data = _run_async(_async_request(config, "GET", "/models/providers"))
        _print_json(data)
    elif sub == "metrics":
        data = _run_async(_async_request(config, "GET", "/models/metrics"))
        _print_json(data)
    else:
        print("Usage: nova models [list|health|providers|metrics]", file=sys.stderr)


def cmd_tools(args: list[str], config: CLIConfig, headers: dict[str, str]) -> None:
    sub = args[0] if args else "list"
    if sub == "list":
        data = _run_async(_async_request(config, "GET", "/tools"))
        _print_json(data)
    elif sub == "metrics":
        data = _run_async(_async_request(config, "GET", "/tools/metrics"))
        _print_json(data)
    else:
        print("Usage: nova tools [list|metrics]", file=sys.stderr)


def cmd_observability(args: list[str], config: CLIConfig, headers: dict[str, str]) -> None:
    sub = args[0] if args else "health"
    if sub == "health":
        data = _run_async(_async_request(config, "GET", "/observability/health"))
        _print_json(data)
    elif sub == "metrics":
        data = _run_async(_async_request(config, "GET", "/observability/metrics"))
        _print_json(data)
    elif sub == "traces":
        limit = 50
        for i, arg in enumerate(args):
            if arg == "--limit" and i + 1 < len(args):
                limit = int(args[i + 1])
        data = _run_async(_async_request(config, "GET", "/observability/traces", params={"limit": limit}))
        _print_json(data)
    elif sub == "logs":
        data = _run_async(_async_request(config, "GET", "/observability/logs"))
        _print_json(data)
    elif sub == "alerts":
        data = _run_async(_async_request(config, "GET", "/observability/alerts"))
        _print_json(data)
    else:
        print("Usage: nova observability [health|metrics|traces|logs|alerts]", file=sys.stderr)


def cmd_deployment(args: list[str], config: CLIConfig, headers: dict[str, str]) -> None:
    sub = args[0] if args else "health"
    if sub == "health":
        data = _run_async(_async_request(config, "GET", "/deployment/health"))
        _print_json(data)
    elif sub == "readiness":
        data = _run_async(_async_request(config, "GET", "/deployment/readiness"))
        _print_json(data)
    elif sub == "liveness":
        data = _run_async(_async_request(config, "GET", "/deployment/liveness"))
        _print_json(data)
    elif sub == "configuration":
        data = _run_async(_async_request(config, "GET", "/deployment/configuration"))
        _print_json(data)
    elif sub == "diagnostics":
        data = _run_async(_async_request(config, "GET", "/deployment/diagnostics"))
        _print_json(data)
    elif sub == "metrics":
        data = _run_async(_async_request(config, "GET", "/deployment/metrics"))
        _print_json(data)
    else:
        print("Usage: nova deployment [health|readiness|liveness|configuration|diagnostics|metrics]", file=sys.stderr)


COMMANDS: dict[str, Callable[[list[str], CLIConfig, dict[str, str]], None]] = {
    "health": cmd_health,
    "chat": cmd_chat,
    "execute": cmd_execute,
    "workflow": cmd_workflow,
    "scheduler": cmd_scheduler,
    "memory": cmd_memory,
    "goals": cmd_goals,
    "tasks": cmd_tasks,
    "agents": cmd_agents,
    "plugins": cmd_plugins,
    "models": cmd_models,
    "tools": cmd_tools,
    "observability": cmd_observability,
    "deployment": cmd_deployment,
}
