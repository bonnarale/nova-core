"""Deployment manifest utilities."""

from __future__ import annotations

import json
import os
from typing import Any


def load_manifest(name: str, directory: str = "") -> dict[str, Any]:
    if not directory:
        directory = os.path.join(
            os.path.dirname(__file__), "..", "kubernetes"
        )
    path = os.path.join(directory, f"{name}.yml")
    if os.path.isfile(path):
        with open(path) as f:
            content = f.read()
        docs: list[dict[str, Any]] = []
        for doc in content.split("---"):
            doc = doc.strip()
            if doc:
                # Simple YAML-like parsing for key-value pairs
                docs.append({"raw": doc})
        return {"file": path, "documents": docs}
    return {"file": path, "documents": [], "error": "not found"}


def list_manifests(directory: str = "") -> list[str]:
    if not directory:
        directory = os.path.join(
            os.path.dirname(__file__), "..", "kubernetes"
        )
    if os.path.isdir(directory):
        return [
            f for f in os.listdir(directory)
            if f.endswith((".yml", ".yaml"))
        ]
    return []
