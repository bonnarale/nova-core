"""LLM-powered knowledge extractor with rule-based fallback.

Implements the KnowledgeExtractor ABC using ModelGateway.chat() for
higher-quality knowledge extraction, with automatic fallback to
DefaultKnowledgeExtractor on failure.
"""

from __future__ import annotations

import json
import logging
from typing import Any

from app.learning.base import KnowledgeExtractor
from app.learning.extractor import DefaultKnowledgeExtractor
from app.learning.models import ArtifactType, ExtractedKnowledge, KnowledgeArtifact

logger = logging.getLogger(__name__)

_VALID_ARTIFACT_TYPES = [t.value for t in ArtifactType]

_EXTRACTION_PROMPT = """You are a knowledge extraction assistant. Given execution data from a completed task, extract reusable knowledge artifacts.

Execution data:
- Goal: {goal}
- Status: {status}
- Steps executed: {steps}
- Events: {events}

Extract knowledge artifacts as a JSON array. Each artifact must have:
- "artifact_type": one of [{valid_types}]
- "content": detailed description of the knowledge (string)
- "summary": one-line summary (string)
- "tags": relevant tags (list of strings)
- "confidence": how confident you are in this knowledge (0.0-1.0)
- "importance_score": how important this knowledge is (0.0-1.0)

Respond with ONLY a JSON object in this format:
{{"artifacts": [list of artifact objects]}}

If no meaningful knowledge can be extracted, return:
{{"artifacts": []}}

Response:"""


class LLMKnowledgeExtractor(KnowledgeExtractor):
    """Extracts knowledge from execution data via LLM with fallback.

    Falls back to ``DefaultKnowledgeExtractor`` when:
    - ModelGateway raises an exception or times out
    - LLM response cannot be parsed as valid JSON
    - Pydantic validation of artifacts fails
    """

    def __init__(
        self,
        gateway: Any,
        fallback: KnowledgeExtractor | None = None,
        model: str = "qwen2.5-coder:7b",
    ) -> None:
        self._gateway = gateway
        self._fallback = fallback or DefaultKnowledgeExtractor()
        self._model = model

    async def extract(
        self,
        execution_data: dict[str, Any],
        task_data: dict[str, Any] | None = None,
    ) -> ExtractedKnowledge:
        """Extract knowledge via LLM, falling back to rule-based on failure."""
        try:
            result = await self._extract_via_llm(execution_data, task_data)
            if result.artifacts:
                return result

            # LLM returned no artifacts — try fallback for additional extraction
            logger.debug("LLM extraction returned no artifacts, trying fallback")
            return await self._fallback.extract(execution_data, task_data)

        except Exception as exc:
            logger.debug("LLM knowledge extraction failed: %s — falling back", exc)
            return await self._fallback.extract(execution_data, task_data)

    async def _extract_via_llm(
        self,
        execution_data: dict[str, Any],
        task_data: dict[str, Any] | None,
    ) -> ExtractedKnowledge:
        """Send extraction prompt to gateway and parse response."""
        task = task_data or {}
        goal = task.get("goal", execution_data.get("goal", ""))
        status = execution_data.get("status", task.get("status", ""))
        steps = json.dumps(task.get("artifacts", {}), indent=2, ensure_ascii=False)
        events = json.dumps(task.get("events", [])[:10], indent=2, ensure_ascii=False)

        prompt = _EXTRACTION_PROMPT.format(
            goal=goal,
            status=status,
            steps=steps[:2000],  # Truncate to avoid token overflow
            events=events[:2000],
            valid_types=", ".join(_VALID_ARTIFACT_TYPES),
        )

        response = await self._gateway.chat(
            model=self._model,
            messages=[{"role": "user", "content": prompt}],
            use_cache=False,  # Don't cache extraction results
        )

        content = self._extract_response_content(response)
        artifacts = self._parse_artifacts(content)

        execution_id = execution_data.get("id", "")
        task_id = task.get("id", "")
        user_id = task.get("user_id") or execution_data.get("user_id")
        agent_id = task.get("assigned_agent") or execution_data.get("agent_id")

        # Set source metadata on all artifacts
        for art in artifacts:
            art.source_execution_id = execution_id
            art.source_task_id = task_id
            art.user_id = user_id
            art.agent_id = agent_id

        confidence = (
            sum(a.confidence for a in artifacts) / len(artifacts)
            if artifacts
            else 0.0
        )

        return ExtractedKnowledge(
            artifacts=artifacts,
            execution_id=execution_id,
            task_id=task_id,
            extraction_method="llm",
            confidence=round(confidence, 3),
        )

    @staticmethod
    def _extract_response_content(response: dict[str, Any]) -> str:
        """Extract text content from gateway response."""
        if "message" in response:
            msg = response["message"]
            if isinstance(msg, dict):
                return msg.get("content", "")
            return str(msg)
        if "content" in response:
            return str(response["content"])
        if "choices" in response:
            choices = response["choices"]
            if choices and isinstance(choices[0], dict):
                return choices[0].get("message", {}).get("content", "")
        return str(response)

    @staticmethod
    def _parse_artifacts(content: str) -> list[KnowledgeArtifact]:
        """Parse LLM response into KnowledgeArtifact objects."""
        text = content.strip()

        # Handle markdown code blocks
        if text.startswith("```"):
            lines = text.split("\n")
            json_lines = []
            in_block = False
            for line in lines:
                if line.startswith("```") and not in_block:
                    in_block = True
                    continue
                elif line.startswith("```") and in_block:
                    break
                elif in_block:
                    json_lines.append(line)
            text = "\n".join(json_lines).strip()

        # Find JSON object
        start = text.find("{")
        end = text.rfind("}") + 1
        if start != -1 and end > start:
            text = text[start:end]

        parsed = json.loads(text)
        raw_artifacts = parsed.get("artifacts", [])

        artifacts: list[KnowledgeArtifact] = []
        for raw in raw_artifacts:
            try:
                artifact_type = raw.get("artifact_type", "fact").lower()
                if artifact_type not in _VALID_ARTIFACT_TYPES:
                    artifact_type = "fact"

                tags = raw.get("tags", [])
                if isinstance(tags, str):
                    tags = [t.strip() for t in tags.split(",")]

                confidence = float(raw.get("confidence", 0.5))
                importance = float(raw.get("importance_score", 0.5))

                artifacts.append(KnowledgeArtifact(
                    id=KnowledgeArtifact.new_id(),
                    artifact_type=artifact_type,
                    content=str(raw.get("content", "")),
                    summary=str(raw.get("summary", "")),
                    tags=tags[:10],
                    confidence=max(0.0, min(1.0, confidence)),
                    importance_score=max(0.0, min(1.0, importance)),
                ))
            except (ValueError, TypeError) as e:
                logger.debug("Failed to parse artifact: %s", e)
                continue

        return artifacts
