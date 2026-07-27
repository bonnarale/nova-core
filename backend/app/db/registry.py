"""Repository registry for the Database Architecture."""

from __future__ import annotations

import logging
from typing import Any

logger = logging.getLogger(__name__)


class RepositoryRegistry:
    """Registry for all database repositories with indexing by name and domain."""

    def __init__(self) -> None:
        self._repositories: dict[str, Any] = {}
        self._domains: dict[str, list[str]] = {}

    def register(
        self,
        name: str,
        repository: Any,
        domain: str = "general",
    ) -> None:
        self._repositories[name] = repository
        if domain not in self._domains:
            self._domains[domain] = []
        self._domains[domain].append(name)
        logger.debug("Registered repository: %s (domain: %s)", name, domain)

    def get(self, name: str) -> Any | None:
        return self._repositories.get(name)

    def has(self, name: str) -> bool:
        return name in self._repositories

    def list_all(self) -> list[str]:
        return sorted(self._repositories.keys())

    def list_by_domain(self, domain: str) -> list[str]:
        return list(self._domains.get(domain, []))

    def list_domains(self) -> list[str]:
        return sorted(self._domains.keys())

    def unregister(self, name: str) -> bool:
        if name in self._repositories:
            del self._repositories[name]
            for domain_repos in self._domains.values():
                if name in domain_repos:
                    domain_repos.remove(name)
            return True
        return False

    def count(self) -> int:
        return len(self._repositories)

    def get_statistics(self) -> dict[str, Any]:
        return {
            "total": len(self._repositories),
            "domains": {d: len(r) for d, r in self._domains.items()},
            "repositories": list(self._repositories.keys()),
        }
