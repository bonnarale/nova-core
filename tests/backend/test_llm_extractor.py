"""Unit tests for LLMKnowledgeExtractor."""

from __future__ import annotations

import json
from unittest.mock import AsyncMock, MagicMock

import pytest

from app.learning.extractor import DefaultKnowledgeExtractor
from app.learning.llm_extractor import LLMKnowledgeExtractor
from app.learning.models import ArtifactType, ExtractedKnowledge, KnowledgeArtifact


# ======================================================================
# Fixtures
# ======================================================================

@pytest.fixture
def mock_gateway():
    gw = MagicMock()
    gw.chat = AsyncMock()
    return gw


@pytest.fixture
def mock_fallback():
    fb = MagicMock(spec=DefaultKnowledgeExtractor)
    fb.extract = AsyncMock(return_value=ExtractedKnowledge(
        artifacts=[],
        execution_id="exec-1",
        task_id="task-1",
        extraction_method="default_rule_based",
        confidence=0.5,
    ))
    return fb


@pytest.fixture
def extractor(mock_gateway, mock_fallback):
    return LLMKnowledgeExtractor(gateway=mock_gateway, fallback=mock_fallback, model="test-model")


def _sample_execution_data() -> dict:
    return {
        "id": "exec-123",
        "status": "COMPLETED",
        "user_id": "user-1",
    }


def _sample_task_data() -> dict:
    return {
        "id": "task-456",
        "goal": "Build a REST API with authentication",
        "assigned_agent": "coder",
        "artifacts": {"endpoint": "/api/v1/users"},
        "events": [{"type": "step.completed", "data": {}}],
    }


def _llm_response(artifacts: list[dict]) -> dict:
    return {
        "message": {
            "content": json.dumps({"artifacts": artifacts})
        }
    }


# ======================================================================
# Happy Path
# ======================================================================

class TestLLMKnowledgeExtractorHappyPath:
    @pytest.mark.asyncio
    async def test_extracts_valid_artifacts(self, extractor, mock_gateway):
        mock_gateway.chat.return_value = _llm_response([
            {
                "artifact_type": "procedure",
                "content": "REST API setup procedure using FastAPI",
                "summary": "FastAPI REST API setup",
                "tags": ["api", "fastapi", "rest"],
                "confidence": 0.85,
                "importance_score": 0.7,
            }
        ])

        result = await extractor.extract(_sample_execution_data(), _sample_task_data())

        assert isinstance(result, ExtractedKnowledge)
        assert len(result.artifacts) == 1
        assert result.artifacts[0].artifact_type == ArtifactType.PROCEDURE.value
        assert result.artifacts[0].content == "REST API setup procedure using FastAPI"
        assert result.extraction_method == "llm"
        assert result.execution_id == "exec-123"
        assert result.task_id == "task-456"

    @pytest.mark.asyncio
    async def test_multiple_artifacts(self, extractor, mock_gateway):
        mock_gateway.chat.return_value = _llm_response([
            {
                "artifact_type": "procedure",
                "content": "API setup",
                "summary": "API setup summary",
                "tags": ["api"],
                "confidence": 0.8,
                "importance_score": 0.6,
            },
            {
                "artifact_type": "pattern",
                "content": "Error handling pattern",
                "summary": "Error handling pattern summary",
                "tags": ["error", "pattern"],
                "confidence": 0.75,
                "importance_score": 0.65,
            },
        ])

        result = await extractor.extract(_sample_execution_data(), _sample_task_data())

        assert len(result.artifacts) == 2
        assert result.artifacts[0].artifact_type == ArtifactType.PROCEDURE.value
        assert result.artifacts[1].artifact_type == ArtifactType.PATTERN.value

    @pytest.mark.asyncio
    async def test_source_metadata_set(self, extractor, mock_gateway):
        mock_gateway.chat.return_value = _llm_response([
            {
                "artifact_type": "fact",
                "content": "A fact",
                "summary": "A fact summary",
                "tags": ["fact"],
                "confidence": 0.7,
                "importance_score": 0.5,
            }
        ])

        result = await extractor.extract(_sample_execution_data(), _sample_task_data())

        art = result.artifacts[0]
        assert art.source_execution_id == "exec-123"
        assert art.source_task_id == "task-456"
        assert art.user_id == "user-1"
        assert art.agent_id == "coder"


# ======================================================================
# Gateway Failure Fallback
# ======================================================================

class TestLLMKnowledgeExtractorFallback:
    @pytest.mark.asyncio
    async def test_gateway_exception_falls_back(self, extractor, mock_gateway, mock_fallback):
        mock_gateway.chat.side_effect = RuntimeError("gateway unavailable")

        result = await extractor.extract(_sample_execution_data(), _sample_task_data())

        assert result.extraction_method == "default_rule_based"
        mock_fallback.extract.assert_called_once_with(_sample_execution_data(), _sample_task_data())

    @pytest.mark.asyncio
    async def test_timeout_falls_back(self, extractor, mock_gateway, mock_fallback):
        import asyncio
        mock_gateway.chat.side_effect = asyncio.TimeoutError("timeout")

        result = await extractor.extract(_sample_execution_data(), _sample_task_data())

        assert result.extraction_method == "default_rule_based"

    @pytest.mark.asyncio
    async def test_malformed_json_falls_back(self, extractor, mock_gateway, mock_fallback):
        mock_gateway.chat.return_value = {
            "message": {"content": "this is not valid JSON at all"}
        }

        result = await extractor.extract(_sample_execution_data(), _sample_task_data())

        assert result.extraction_method == "default_rule_based"
        mock_fallback.extract.assert_called_once()

    @pytest.mark.asyncio
    async def test_llm_returns_no_artifacts_uses_fallback(self, extractor, mock_gateway, mock_fallback):
        mock_gateway.chat.return_value = _llm_response([])

        result = await extractor.extract(_sample_execution_data(), _sample_task_data())

        # LLM returned empty, so fallback should be tried
        mock_fallback.extract.assert_called_once()


# ======================================================================
# Response Parsing
# ======================================================================

class TestLLMKnowledgeExtractorParsing:
    @pytest.mark.asyncio
    async def test_markdown_code_block_response(self, extractor, mock_gateway):
        response_content = '```json\n{"artifacts": [{"artifact_type": "fact", "content": "test", "summary": "test", "tags": [], "confidence": 0.5, "importance_score": 0.5}]}\n```'
        mock_gateway.chat.return_value = {
            "message": {"content": response_content}
        }

        result = await extractor.extract(_sample_execution_data(), _sample_task_data())

        assert len(result.artifacts) == 1

    @pytest.mark.asyncio
    async def test_invalid_artifact_type_defaults_to_fact(self, extractor, mock_gateway):
        mock_gateway.chat.return_value = _llm_response([
            {
                "artifact_type": "INVALID_TYPE",
                "content": "test content",
                "summary": "test",
                "tags": [],
                "confidence": 0.5,
                "importance_score": 0.5,
            }
        ])

        result = await extractor.extract(_sample_execution_data(), _sample_task_data())

        assert result.artifacts[0].artifact_type == ArtifactType.FACT.value

    @pytest.mark.asyncio
    async def test_string_tags_split(self, extractor, mock_gateway):
        mock_gateway.chat.return_value = _llm_response([
            {
                "artifact_type": "fact",
                "content": "test",
                "summary": "test",
                "tags": "api, rest, http",
                "confidence": 0.6,
                "importance_score": 0.5,
            }
        ])

        result = await extractor.extract(_sample_execution_data(), _sample_task_data())

        assert result.artifacts[0].tags == ["api", "rest", "http"]

    @pytest.mark.asyncio
    async def test_confidence_clamped_to_range(self, extractor, mock_gateway):
        mock_gateway.chat.return_value = _llm_response([
            {
                "artifact_type": "fact",
                "content": "test",
                "summary": "test",
                "tags": [],
                "confidence": 2.0,
                "importance_score": -0.5,
            }
        ])

        result = await extractor.extract(_sample_execution_data(), _sample_task_data())

        assert result.artifacts[0].confidence == 1.0
        assert result.artifacts[0].importance_score == 0.0

    @pytest.mark.asyncio
    async def test_missing_fields_use_defaults(self, extractor, mock_gateway):
        mock_gateway.chat.return_value = _llm_response([
            {
                "artifact_type": "strategy",
                "content": "only content provided",
            }
        ])

        result = await extractor.extract(_sample_execution_data(), _sample_task_data())

        assert result.artifacts[0].summary == ""
        assert result.artifacts[0].tags == []
        assert result.artifacts[0].confidence == 0.5  # default
        assert result.artifacts[0].importance_score == 0.5  # default


# ======================================================================
# All ArtifactType values
# ======================================================================

class TestLLMKnowledgeExtractorArtifactTypes:
    @pytest.mark.asyncio
    @pytest.mark.parametrize("artifact_type", [t.value for t in ArtifactType])
    async def test_all_types_accepted(self, extractor, mock_gateway, artifact_type):
        mock_gateway.chat.return_value = _llm_response([
            {
                "artifact_type": artifact_type,
                "content": f"Test content for {artifact_type}",
                "summary": f"Summary for {artifact_type}",
                "tags": [artifact_type],
                "confidence": 0.7,
                "importance_score": 0.6,
            }
        ])

        result = await extractor.extract(_sample_execution_data(), _sample_task_data())

        assert result.artifacts[0].artifact_type == artifact_type


# ======================================================================
# Data Truncation
# ======================================================================

class TestLLMKnowledgeExtractorTruncation:
    @pytest.mark.asyncio
    async def test_long_steps_truncated(self, extractor, mock_gateway):
        long_task_data = _sample_task_data()
        long_task_data["artifacts"] = {"key": "x" * 5000}
        mock_gateway.chat.return_value = _llm_response([
            {
                "artifact_type": "fact",
                "content": "test",
                "summary": "test",
                "tags": [],
                "confidence": 0.5,
                "importance_score": 0.5,
            }
        ])

        result = await extractor.extract(_sample_execution_data(), long_task_data)
        assert len(result.artifacts) == 1
