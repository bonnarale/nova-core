"""Abstract base classes for the Autonomy subsystem."""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Any


class AutonomyProvider(ABC):
    """Base interface for the autonomous engine."""

    @abstractmethod
    async def evaluate_objectives(self) -> list[dict[str, Any]]:
        ...

    @abstractmethod
    async def propose_plan(self, objective_id: str) -> dict[str, Any]:
        ...

    @abstractmethod
    async def evaluate_execution(self, execution_id: str) -> dict[str, Any]:
        ...

    @abstractmethod
    async def reflect_on_results(self, results: dict[str, Any]) -> dict[str, Any]:
        ...

    @abstractmethod
    async def recommend_improvements(self) -> list[dict[str, Any]]:
        ...

    @abstractmethod
    async def adapt_strategy(self, strategy_type: str, context: dict[str, Any]) -> dict[str, Any]:
        ...


class PolicyProvider(ABC):
    """Base interface for policy evaluation."""

    @abstractmethod
    def evaluate(self, action: dict[str, Any], context: dict[str, Any]) -> bool:
        ...

    @abstractmethod
    def get_level(self) -> str:
        ...

    @abstractmethod
    def get_constraints(self) -> dict[str, Any]:
        ...


class ReflectionProvider(ABC):
    """Base interface for reflection operations."""

    @abstractmethod
    async def review_execution(self, execution_id: str, results: dict[str, Any]) -> dict[str, Any]:
        ...

    @abstractmethod
    async def analyze_failure(self, execution_id: str, error: str) -> dict[str, Any]:
        ...

    @abstractmethod
    async def analyze_success(self, execution_id: str, results: dict[str, Any]) -> dict[str, Any]:
        ...

    @abstractmethod
    async def extract_lessons(self, analyses: list[dict[str, Any]]) -> list[dict[str, Any]]:
        ...


class StrategyProvider(ABC):
    """Base interface for adaptive strategies."""

    @abstractmethod
    def select_strategy(self, context: dict[str, Any]) -> str:
        ...

    @abstractmethod
    def adapt(self, strategy: str, feedback: dict[str, Any]) -> str:
        ...

    @abstractmethod
    def get_available_strategies(self) -> list[str]:
        ...


class EvaluatorProvider(ABC):
    """Base interface for evaluation operations."""

    @abstractmethod
    def evaluate_objective(self, objective: dict[str, Any]) -> dict[str, Any]:
        ...

    @abstractmethod
    def score_completion(self, objective: dict[str, Any], results: dict[str, Any]) -> float:
        ...

    @abstractmethod
    def rank_objectives(self, objectives: list[dict[str, Any]]) -> list[dict[str, Any]]:
        ...


class ApprovalProvider(ABC):
    """Base interface for approval operations."""

    @abstractmethod
    async def request_approval(self, recommendation: dict[str, Any]) -> dict[str, Any]:
        ...

    @abstractmethod
    def is_auto_approved(self, recommendation: dict[str, Any]) -> bool:
        ...

    @abstractmethod
    def approve(self, recommendation_id: str, approver: str = "system") -> bool:
        ...

    @abstractmethod
    def reject(self, recommendation_id: str, reason: str = "") -> bool:
        ...
