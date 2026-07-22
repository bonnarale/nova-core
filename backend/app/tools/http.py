"""HttpTool — make HTTP requests."""

from __future__ import annotations

from typing import Any

from app.tools.base import Tool, ToolParam, ToolSpec
from app.tools.result import ToolResult


class HttpTool(Tool):
    """Make HTTP requests — GET, POST, PUT, DELETE, PATCH, HEAD."""

    @property
    def spec(self) -> ToolSpec:
        return ToolSpec(
            name="http",
            description="Make HTTP requests to external APIs and services.",
            category="network",
            timeout_default=30.0,
            retry_default=1,
            permission_level="read",
            parameters=[
                ToolParam(name="method", type="string", required=True, description="HTTP method: GET, POST, PUT, DELETE, PATCH, HEAD"),
                ToolParam(name="url", type="string", required=True, description="Request URL"),
                ToolParam(name="headers", type="dict", required=False, description="HTTP headers"),
                ToolParam(name="body", type="string", required=False, description="Request body (for POST/PUT/PATCH)"),
                ToolParam(name="params", type="dict", required=False, description="Query parameters"),
                ToolParam(name="timeout", type="integer", required=False, description="Request timeout in seconds"),
            ],
        )

    async def run(self, params: dict[str, Any]) -> ToolResult:
        method = params["method"].upper()
        url = params["url"]

        if method not in ("GET", "POST", "PUT", "DELETE", "PATCH", "HEAD"):
            return ToolResult.error_result("http", f"Unsupported HTTP method: {method}")

        try:
            import httpx
        except ImportError:
            try:
                import urllib.request
                import urllib.parse
                return await self._run_stdlib(method, url, params)
            except Exception as exc:
                return ToolResult.error_result("http", f"No HTTP client available: {exc}")

        try:
            timeout_val = params.get("timeout", self.spec.timeout_default)
            async with httpx.AsyncClient(timeout=timeout_val) as client:
                response = await client.request(
                    method=method,
                    url=url,
                    headers=params.get("headers"),
                    content=params.get("body"),
                    params=params.get("params"),
                )
                content_type = response.headers.get("content-type", "")
                if "application/json" in content_type:
                    try:
                        data = response.json()
                    except Exception:
                        data = response.text
                else:
                    data = response.text

                return ToolResult(
                    success=True,
                    data={
                        "status_code": response.status_code,
                        "headers": dict(response.headers),
                        "body": data,
                    },
                )
        except Exception as exc:
            return ToolResult.error_result("http", f"HTTP request failed: {exc}")

    async def _run_stdlib(self, method: str, url: str, params: dict[str, Any]) -> ToolResult:
        import urllib.request
        import urllib.parse

        if params.get("params"):
            url = f"{url}?{urllib.parse.urlencode(params['params'])}"

        req = urllib.request.Request(
            url,
            data=params.get("body", "").encode() if params.get("body") else None,
            headers=params.get("headers", {}),
            method=method,
        )

        try:
            with urllib.request.urlopen(req, timeout=params.get("timeout", 30)) as resp:
                body = resp.read().decode("utf-8", errors="replace")
                try:
                    import json
                    data = json.loads(body)
                except Exception:
                    data = body
                return ToolResult(
                    success=True,
                    data={
                        "status_code": resp.status,
                        "headers": dict(resp.headers),
                        "body": data,
                    },
                )
        except Exception as exc:
            return ToolResult.error_result("http", f"HTTP request failed: {exc}")
