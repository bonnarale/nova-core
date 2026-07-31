"""Plugin version manager — semver checking and compatibility."""

from __future__ import annotations

import re
from typing import NamedTuple


class SemVer(NamedTuple):
    major: int
    minor: int
    patch: int
    prerelease: str = ""

    def __str__(self) -> str:
        base = f"{self.major}.{self.minor}.{self.patch}"
        return f"{base}-{self.prerelease}" if self.prerelease else base

    def __ge__(self, other: object) -> bool:
        if not isinstance(other, SemVer):
            return NotImplemented
        return self._cmp_tuple() >= other._cmp_tuple()

    def __gt__(self, other: object) -> bool:
        if not isinstance(other, SemVer):
            return NotImplemented
        return self._cmp_tuple() > other._cmp_tuple()

    def __le__(self, other: object) -> bool:
        if not isinstance(other, SemVer):
            return NotImplemented
        return self._cmp_tuple() <= other._cmp_tuple()

    def __lt__(self, other: object) -> bool:
        if not isinstance(other, SemVer):
            return NotImplemented
        return self._cmp_tuple() < other._cmp_tuple()

    def _cmp_tuple(self) -> tuple[int, int, int, str]:
        return (self.major, self.minor, self.patch, self.prerelease)


_SEMVER_RE = re.compile(r"^(\d+)\.(\d+)\.(\d+)(?:-(.+))?$")


class VersionManager:
    """Manages plugin versioning and compatibility checks."""

    @staticmethod
    def parse(version_str: str) -> SemVer:
        match = _SEMVER_RE.match(version_str.strip())
        if not match:
            raise ValueError(f"Invalid semver: {version_str}")
        return SemVer(
            major=int(match.group(1)),
            minor=int(match.group(2)),
            patch=int(match.group(3)),
            prerelease=match.group(4) or "",
        )

    @staticmethod
    def is_compatible(actual: str, required_min: str = "", required_max: str = "") -> bool:
        try:
            actual_sv = VersionManager.parse(actual)
        except ValueError:
            return False
        if required_min:
            try:
                min_sv = VersionManager.parse(required_min)
                if actual_sv < min_sv:
                    return False
            except ValueError:
                return False
        if required_max:
            try:
                max_sv = VersionManager.parse(required_max)
                if actual_sv > max_sv:
                    return False
            except ValueError:
                return False
        return True

    @staticmethod
    def is_breaking_change(old_version: str, new_version: str) -> bool:
        try:
            old_sv = VersionManager.parse(old_version)
            new_sv = VersionManager.parse(new_version)
        except ValueError:
            return True
        return new_sv.major != old_sv.major

    @staticmethod
    def is_backward_compatible(old_version: str, new_version: str) -> bool:
        try:
            old_sv = VersionManager.parse(old_version)
            new_sv = VersionManager.parse(new_version)
        except ValueError:
            return False
        return new_sv.major == old_sv.major

    @staticmethod
    def sort_versions(versions: list[str]) -> list[str]:
        parsed = []
        for v in versions:
            try:
                parsed.append((VersionManager.parse(v), v))
            except ValueError:
                continue
        parsed.sort(key=lambda x: x[0])
        return [v for _, v in parsed]
