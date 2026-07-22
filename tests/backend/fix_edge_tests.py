path = "/home/aalej/nova-core/tests/backend/test_knowledge_graph.py"

with open(path, "r") as f:
    content = f.read()

old = """class TestEdgeCases:
    @pytest.mark.asyncio
    async def test_delete_nonexistent_relationship(self, engine):
        engine = KnowledgeGraphEngine()
        await engine.initialize()
        deleted = await engine.delete_relationship("nonexistent")
        assert not deleted

    @pytest.mark.asyncio
    async def test_extract_from_text_empty(self, engine):
        engine = KnowledgeGraphEngine()
        await engine.initialize()
        result = await engine.extract_from_text("")
        assert result["entities"] == []

    @pytest.mark.asyncio
    async def test_search_no_results(self, engine):
        engine = KnowledgeGraphEngine()
        await engine.initialize()
        results = await engine.search("zzzznonexistent")
        assert results == []"""

new = """class TestEdgeCases:
    @pytest.mark.asyncio
    async def test_delete_nonexistent_relationship(self):
        engine = KnowledgeGraphEngine()
        await engine.initialize()
        deleted = await engine.delete_relationship("nonexistent")
        assert not deleted

    @pytest.mark.asyncio
    async def test_extract_from_text_empty(self):
        engine = KnowledgeGraphEngine()
        await engine.initialize()
        result = await engine.extract_from_text("")
        assert result["entities"] == []

    @pytest.mark.asyncio
    async def test_search_no_results(self):
        engine = KnowledgeGraphEngine()
        await engine.initialize()
        results = await engine.search("zzzznonexistent")
        assert results == []"""

content = content.replace(old, new)

with open(path, "w") as f:
    f.write(content)

print("Done")
