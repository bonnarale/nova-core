path = "/home/aalej/nova-core/tests/backend/test_knowledge_graph.py"

with open(path, "r") as f:
    content = f.read()

# Fix all cognitive integration tests to avoid deep import chains
replacements = [
    (
        "from app.cognitive.context import IntentType\n        assert IntentType.KNOWLEDGE_GRAPH.value == \"KNOWLEDGE_GRAPH\"",
        "from app.cognitive.context import IntentType as KGIntentType\n        assert KGIntentType.KNOWLEDGE_GRAPH.value == \"KNOWLEDGE_GRAPH\""
    ),
    (
        """from app.cognitive.decision import KnowledgeGraphHandler, default_handler_registry
        from app.cognitive.context import IntentType

        handler = KnowledgeGraphHandler()
        assert IntentType.KNOWLEDGE_GRAPH in handler.handled_intents

        registry = default_handler_registry()
        assert IntentType.KNOWLEDGE_GRAPH in registry""",
        """from app.cognitive.decision import KnowledgeGraphHandler
        from app.cognitive.decision import default_handler_registry as kg_default_registry
        from app.cognitive.context import IntentType as KGIntentType2

        handler = KnowledgeGraphHandler()
        assert KGIntentType2.KNOWLEDGE_GRAPH in handler.handled_intents

        registry = kg_default_registry()
        assert KGIntentType2.KNOWLEDGE_GRAPH in registry"""
    ),
    (
        """from app.cognitive.router import RuleBasedIntentDetector
        from app.cognitive.context import IntentType

        detector = RuleBasedIntentDetector()
        assert IntentType.KNOWLEDGE_GRAPH in detector._PATTERNS
        assert \"knowledge graph\" in detector._PATTERNS[IntentType.KNOWLEDGE_GRAPH]""",
        """from app.cognitive.router import RuleBasedIntentDetector as KGRuleBasedDetector
        from app.cognitive.context import IntentType as KGIntentType3

        detector = KGRuleBasedDetector()
        assert KGIntentType3.KNOWLEDGE_GRAPH in detector._PATTERNS
        assert \"knowledge graph\" in detector._PATTERNS[KGIntentType3.KNOWLEDGE_GRAPH]"""
    ),
]

for old, new in replacements:
    content = content.replace(old, new)

with open(path, "w") as f:
    f.write(content)

print("Done")
