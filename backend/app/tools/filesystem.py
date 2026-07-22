"""FilesystemTool — read, write, list, delete files and directories."""

from __future__ import annotations

import os
import shutil
from pathlib import Path

from app.tools.base import Tool, ToolParam, ToolSpec
from app.tools.result import ToolResult


class FilesystemTool(Tool):
    """Read, write, list, delete files and directories."""

    @property
    def spec(self) -> ToolSpec:
        return ToolSpec(
            name="filesystem",
            description="Read, write, list, and delete files and directories on the local filesystem.",
            category="system",
            timeout_default=30.0,
            retry_default=1,
            permission_level="write",
            parameters=[
                ToolParam(name="operation", type="string", required=True, description="One of: read, write, list, delete, exists, mkdir, copy, move"),
                ToolParam(name="path", type="string", required=True, description="Absolute file or directory path"),
                ToolParam(name="content", type="string", required=False, description="Content to write (for write operation)"),
                ToolParam(name="destination", type="string", required=False, description="Destination path (for copy/move operations)"),
                ToolParam(name="recursive", type="boolean", required=False, description="List/delete recursively (default: false)"),
            ],
        )

    async def run(self, params: dict[str, Any]) -> ToolResult:
        operation = params["operation"]
        path = params["path"]

        try:
            if operation == "read":
                return await self._read(path)
            elif operation == "write":
                return await self._write(path, params.get("content", ""))
            elif operation == "list":
                return await self._list(path, params.get("recursive", False))
            elif operation == "delete":
                return await self._delete(path, params.get("recursive", False))
            elif operation == "exists":
                return self._exists(path)
            elif operation == "mkdir":
                return await self._mkdir(path)
            elif operation == "copy":
                return await self._copy(path, params.get("destination", ""))
            elif operation == "move":
                return await self._move(path, params.get("destination", ""))
            else:
                return ToolResult.error_result(
                    "filesystem",
                    f"Unknown operation: {operation}",
                )
        except PermissionError as exc:
            return ToolResult.error_result("filesystem", f"Permission denied: {exc}")
        except FileNotFoundError as exc:
            return ToolResult.error_result("filesystem", str(exc))
        except Exception as exc:
            return ToolResult.error_result("filesystem", f"Filesystem error: {exc}")

    async def _read(self, path: str) -> ToolResult:
        p = Path(path)
        if not p.exists():
            return ToolResult.error_result("filesystem", f"File not found: {path}")
        if not p.is_file():
            return ToolResult.error_result("filesystem", f"Not a file: {path}")
        content = p.read_text(encoding="utf-8")
        return ToolResult(success=True, data={"path": path, "content": content, "size": len(content)})

    async def _write(self, path: str, content: str) -> ToolResult:
        p = Path(path)
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text(content, encoding="utf-8")
        return ToolResult(success=True, data={"path": path, "bytes_written": len(content)})

    async def _list(self, path: str, recursive: bool = False) -> ToolResult:
        p = Path(path)
        if not p.exists():
            return ToolResult.error_result("filesystem", f"Path not found: {path}")
        if not p.is_dir():
            return ToolResult.error_result("filesystem", f"Not a directory: {path}")

        if recursive:
            entries = [str(f) for f in p.rglob("*")]
        else:
            entries = [str(f) for f in p.iterdir()]

        return ToolResult(success=True, data={"path": path, "entries": entries, "count": len(entries)})

    async def _delete(self, path: str, recursive: bool = False) -> ToolResult:
        p = Path(path)
        if not p.exists():
            return ToolResult.error_result("filesystem", f"Path not found: {path}")
        if p.is_file():
            p.unlink()
        elif p.is_dir():
            if recursive:
                shutil.rmtree(p)
            else:
                p.rmdir()
        return ToolResult(success=True, data={"path": path, "deleted": True})

    def _exists(self, path: str) -> ToolResult:
        p = Path(path)
        return ToolResult(success=True, data={"path": path, "exists": p.exists(), "is_file": p.is_file(), "is_dir": p.is_dir()})

    async def _mkdir(self, path: str) -> ToolResult:
        p = Path(path)
        p.mkdir(parents=True, exist_ok=True)
        return ToolResult(success=True, data={"path": path, "created": True})

    async def _copy(self, source: str, destination: str) -> ToolResult:
        src = Path(source)
        dst = Path(destination)
        if not src.exists():
            return ToolResult.error_result("filesystem", f"Source not found: {source}")
        dst.parent.mkdir(parents=True, exist_ok=True)
        if src.is_file():
            shutil.copy2(src, dst)
        else:
            shutil.copytree(src, dst)
        return ToolResult(success=True, data={"source": source, "destination": destination})

    async def _move(self, source: str, destination: str) -> ToolResult:
        src = Path(source)
        dst = Path(destination)
        if not src.exists():
            return ToolResult.error_result("filesystem", f"Source not found: {source}")
        dst.parent.mkdir(parents=True, exist_ok=True)
        shutil.move(str(src), str(dst))
        return ToolResult(success=True, data={"source": source, "destination": destination})
