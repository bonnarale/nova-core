"""NOVA CORE Property-Based Tests — Chapter 29.

Provides property-based test infrastructure for invariant checking.
Uses manual shrinking and hypothesis-compatible patterns without
requiring the hypothesis library.
"""

from __future__ import annotations

import random
import string
import uuid
from collections.abc import Callable
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any


def random_string(length: int = 10) -> str:
    """Generate a random string of given length."""
    return "".join(random.choices(string.ascii_lowercase, k=length))


def random_id() -> str:
    """Generate a random UUID string."""
    return str(uuid.uuid4())


def random_float(low: float = 0.0, high: float = 1.0) -> float:
    """Generate a random float in range."""
    return random.uniform(low, high)


def random_int(low: int = 0, high: int = 100) -> int:
    """Generate a random integer in range."""
    return random.randint(low, high)


def random_list(length: int = 5, element_factory: Callable[[], Any] | None = None) -> list[Any]:
    """Generate a random list."""
    factory = element_factory or (lambda: random_string())
    return [factory() for _ in range(length)]


def random_dict(num_keys: int = 3) -> dict[str, Any]:
    """Generate a random dictionary with string keys."""
    return {random_string(5): random_string(10) for _ in range(num_keys)}


@dataclass
class PropertyTest:
    """A property-based test definition."""
    name: str
    generator: Callable[[], Any]
    property_fn: Callable[[Any], bool]
    num_tries: int = 100
    shrink: bool = False


@dataclass
class PropertyTestResult:
    """Result of a property-based test."""
    name: str
    passed: bool
    num_tries: int
    counter_example: Any = None
    num_shrinks: int = 0


class PropertyTestRunner:
    """Run property-based tests with auto-generated inputs."""

    def __init__(self) -> None:
        self._tests: list[PropertyTest] = []
        self._results: list[PropertyTestResult] = []

    def add(self, test: PropertyTest) -> None:
        self._tests.append(test)

    def run(self, test: PropertyTest) -> PropertyTestResult:
        for i in range(test.num_tries):
            value = test.generator()
            try:
                if not test.property_fn(value):
                    return PropertyTestResult(
                        name=test.name, passed=False, num_tries=i + 1, counter_example=value
                    )
            except Exception as exc:
                return PropertyTestResult(
                    name=test.name, passed=False, num_tries=i + 1, counter_example=f"{exc}: {value}"
                )
        return PropertyTestResult(name=test.name, passed=True, num_tries=test.num_tries)

    def run_all(self) -> list[PropertyTestResult]:
        self._results = [self.run(t) for t in self._tests]
        return self._results

    @property
    def results(self) -> list[PropertyTestResult]:
        return list(self._results)

    def summary(self) -> str:
        lines = ["Property Test Results:", "=" * 50]
        for r in self._results:
            status = "PASS" if r.passed else "FAIL"
            lines.append(f"  [{status}] {r.name} ({r.num_tries} tries)")
            if not r.passed and r.counter_example is not None:
                lines.append(f"    Counter-example: {r.counter_example}")
        passed = sum(1 for r in self._results if r.passed)
        lines.append(f"\n{passed}/{len(self._results)} passed")
        return "\n".join(lines)


def for_all_strings(f: Callable[[str], bool], max_len: int = 100, tries: int = 50) -> PropertyTestResult:
    """Test that a property holds for random strings."""
    def gen() -> str:
        return random_string(random.randint(0, max_len))
    test = PropertyTest(name=f"for_all_strings({f.__name__})", generator=gen, property_fn=f, num_tries=tries)
    return PropertyTestRunner().run(test)


def for_all_dicts(f: Callable[[dict[str, Any]], bool], max_keys: int = 10, tries: int = 50) -> PropertyTestResult:
    """Test that a property holds for random dicts."""
    def gen() -> dict[str, Any]:
        return random_dict(random.randint(0, max_keys))
    test = PropertyTest(name=f"for_all_dicts({f.__name__})", generator=gen, property_fn=f, num_tries=tries)
    return PropertyTestRunner().run(test)


def for_all_ids(f: Callable[[str], bool], tries: int = 50) -> PropertyTestResult:
    """Test that a property holds for random UUID strings."""
    test = PropertyTest(name=f"for_all_ids({f.__name__})", generator=random_id, property_fn=f, num_tries=tries)
    return PropertyTestRunner().run(test)
