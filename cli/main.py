from __future__ import annotations

import json
import sys
from typing import Any

from cli.commands import COMMANDS
from cli.config import CLIConfig, load_config
from cli.auth import resolve_auth

__version__ = "0.1.0"


def _print_json(data: Any) -> None:
    print(json.dumps(data, indent=2, default=str))


def _print_table(items: list[dict[str, Any]], columns: list[str] | None = None) -> None:
    if not items:
        print("No results.")
        return
    cols = columns or list(items[0].keys())
    widths = {col: max(len(col), max((len(str(item.get(col, ""))) for item in items), default=0)) for col in cols}
    header = "  ".join(f"{col:<{widths[col]}}" for col in cols)
    print(header)
    print("  ".join("-" * widths[col] for col in cols))
    for item in items:
        row = "  ".join(f"{str(item.get(col, '')):<{widths[col]}}" for col in cols)
        print(row)


def run_command(args: list[str]) -> None:
    if not args or args[0] in ("-h", "--help"):
        _print_help()
        return

    cmd_name = args[0]
    cmd_args = args[1:]

    if cmd_name == "version":
        print(f"nova-core-cli {__version__}")
        return

    if cmd_name == "config":
        _handle_config(cmd_args)
        return

    if cmd_name not in COMMANDS:
        print(f"Unknown command: {cmd_name}", file=sys.stderr)
        print(f"Run 'nova --help' for usage.", file=sys.stderr)
        sys.exit(1)

    config = load_config()
    auth_headers = resolve_auth(config)
    handler = COMMANDS[cmd_name]
    handler(cmd_args, config, auth_headers)


def _print_help() -> None:
    print("NOVA CORE CLI — command-line interface for the NOVA CORE AI operating system\n")
    print("Usage: nova <command> [options]\n")
    print("Commands:")
    print("  health          Check API health status")
    print("  chat            Send a chat request to a model")
    print("  execute         Execute a task through the kernel")
    print("  workflow        Manage and execute workflows")
    print("  scheduler       Manage scheduled jobs")
    print("  memory          Query conversation memory")
    print("  goals           Manage goals for a user")
    print("  tasks           Manage tasks")
    print("  agents          Manage and interact with agents")
    print("  plugins         Manage plugins")
    print("  models          List and interact with models")
    print("  tools           Manage and execute tools")
    print("  observability   View metrics, traces, and logs")
    print("  deployment      View deployment status")
    print("  version         Show CLI version")
    print("  config          Manage CLI configuration")
    print("\nGlobal Options:")
    print("  --base-url URL  Override API base URL")
    print("  --api-key KEY   Use API key authentication")
    print("  --token TOKEN   Use bearer token authentication")
    print("  --json          Output raw JSON")
    print("  -h, --help      Show this help message")


def _handle_config(args: list[str]) -> None:
    from cli.config import get_config_path
    if not args or args[0] == "show":
        config = load_config()
        _print_json({"base_url": config.base_url, "has_api_key": bool(config.api_key), "has_token": bool(config.bearer_token)})
    elif args[0] == "path":
        print(get_config_path())
    else:
        print(f"Unknown config subcommand: {args[0]}", file=sys.stderr)


def main() -> None:
    try:
        run_command(sys.argv[1:])
    except KeyboardInterrupt:
        print("\nAborted.", file=sys.stderr)
        sys.exit(130)
    except Exception as exc:
        print(f"Error: {exc}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
