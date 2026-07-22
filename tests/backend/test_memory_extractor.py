"""Tests for MemoryExtractor."""

import pytest

from app.services.extractor import MemoryExtractor


class TestMemoryExtractor:
    @pytest.fixture
    def extractor(self):
        return MemoryExtractor()

    def test_extract_name_spanish(self, extractor):
        msgs = [{"role": "user", "content": "Me llamo Ariel"}]
        result = extractor.extract(msgs)
        assert result["name"] == "Ariel"

    def test_extract_name_english(self, extractor):
        msgs = [{"role": "user", "content": "My name is John"}]
        result = extractor.extract(msgs)
        assert result["name"] == "John"

    def test_extract_name_soy(self, extractor):
        msgs = [{"role": "user", "content": "Soy Maria"}]
        result = extractor.extract(msgs)
        assert result["name"] == "Maria"

    def test_extract_goal_spanish(self, extractor):
        msgs = [{"role": "user", "content": "Quiero construir un asistente"}]
        result = extractor.extract(msgs)
        assert "construir un asistente" in result.get("goals", [])

    def test_extract_goal_english(self, extractor):
        msgs = [{"role": "user", "content": "I want to build an AI"}]
        result = extractor.extract(msgs)
        assert "build an AI" in result.get("goals", [])

    def test_extract_preference_spanish(self, extractor):
        msgs = [{"role": "user", "content": "Me gusta Python"}]
        result = extractor.extract(msgs)
        assert "Python" in result.get("preferences", [])

    def test_extract_preference_english(self, extractor):
        msgs = [{"role": "user", "content": "I like Rust"}]
        result = extractor.extract(msgs)
        assert "Rust" in result.get("preferences", [])

    def test_extract_fact_spanish(self, extractor):
        msgs = [{"role": "user", "content": "Trabajo en NOVA CORE"}]
        result = extractor.extract(msgs)
        assert any("NOVA CORE" in f for f in result.get("facts", []))

    def test_extract_fact_english(self, extractor):
        msgs = [{"role": "user", "content": "I work at Google"}]
        result = extractor.extract(msgs)
        assert any("Google" in f for f in result.get("facts", []))

    def test_full_extraction(self, extractor):
        msgs = [{"role": "user", "content": "Me llamo Ariel y estoy creando NOVA CORE"}]
        result = extractor.extract(msgs)
        assert result["name"] == "Ariel"
        assert any("NOVA CORE" in f for f in result.get("facts", []))

    def test_no_match_returns_empty(self, extractor):
        msgs = [{"role": "user", "content": "Hola"}]
        result = extractor.extract(msgs)
        assert result == {}

    def test_skips_assistant_messages(self, extractor):
        msgs = [
            {"role": "assistant", "content": "Me llamo Bot"},
            {"role": "user", "content": "Hola"},
        ]
        result = extractor.extract(msgs)
        assert "name" not in result
