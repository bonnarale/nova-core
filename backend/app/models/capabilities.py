"""Capabilities for providers and models."""

from dataclasses import dataclass, field
from enum import Enum
from typing import Optional


class ModelCapability(str, Enum):
    """Capabilities that a model can have."""

    CHAT = "chat"
    COMPLETION = "completion"
    EMBEDDING = "embedding"
    VISION = "vision"
    AUDIO = "audio"
    FUNCTION_CALLING = "function_calling"
    STREAMING = "streaming"
    TOOL_USE = "tool_use"
    JSON_MODE = "json_mode"
    SYSTEM_PROMPT = "system_prompt"


class ProviderCapability(str, Enum):
    """Capabilities that a provider can have."""

    CHAT = "chat"
    COMPLETION = "completion"
    EMBEDDING = "embedding"
    VISION = "vision"
    AUDIO = "audio"
    FUNCTION_CALLING = "function_calling"
    STREAMING = "streaming"
    TOOL_USE = "tool_use"
    JSON_MODE = "json_mode"
    BATCH = "batch"
    MODERATION = "moderation"
    FINE_TUNING = "fine_tuning"
    RANKING = "ranking"


@dataclass
class ProviderCapabilities:
    """Capabilities of a model provider."""

    supported: list[ProviderCapability] = field(default_factory=list)
    max_concurrent_requests: int = 10
    max_tokens_per_request: int = 4096
    max_requests_per_minute: int = 60
    supports_streaming: bool = True
    supports_caching: bool = True
    supports_retry: bool = True
    supports_circuit_breaker: bool = True
    rate_limit_delay: float = 0.0

    def supports(self, capability: ProviderCapability) -> bool:
        """Check if provider supports a capability."""
        return capability in self.supported

    def get_max_tokens(self) -> int:
        """Get maximum tokens per request."""
        return self.max_tokens_per_request

    def get_rate_limit_delay(self) -> float:
        """Get rate limit delay in seconds."""
        return self.rate_limit_delay


@dataclass
class ModelCapabilities:
    """Capabilities of a specific model."""

    model_id: str
    provider: str
    supported: list[ModelCapability] = field(default_factory=list)
    max_context_length: int = 4096
    max_output_tokens: int = 4096
    supports_streaming: bool = True
    supports_json_mode: bool = False
    supports_function_calling: bool = False
    supports_vision: bool = False
    supports_tools: bool = False
    cost_per_1k_input_tokens: float = 0.0
    cost_per_1k_output_tokens: float = 0.0
    average_latency_ms: float = 1000.0

    def supports(self, capability: ModelCapability) -> bool:
        """Check if model supports a capability."""
        return capability in self.supported

    def estimate_cost(self, input_tokens: int, output_tokens: int) -> float:
        """Estimate cost for a request."""
        input_cost = (input_tokens / 1000.0) * self.cost_per_1k_input_tokens
        output_cost = (output_tokens / 1000.0) * self.cost_per_1k_output_tokens
        return input_cost + output_cost

    def estimate_latency(self, token_count: int) -> float:
        """Estimate latency in milliseconds based on token count."""
        base_latency = self.average_latency_ms
        token_factor = token_count / self.max_context_length
        return base_latency * (1.0 + token_factor)
