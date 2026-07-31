"""Tests for Chapter 31 — Appendix / Documentation validation."""

from __future__ import annotations

import os
import re
from pathlib import Path

import pytest


# ---------------------------------------------------------------------------
# Paths
# ---------------------------------------------------------------------------

PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
DOCS_DIR = PROJECT_ROOT / "docs"


# ---------------------------------------------------------------------------
# Documentation file existence
# ---------------------------------------------------------------------------

REQUIRED_DOCS = [
    "README.md",
    "ARCHITECTURE.md",
    "SYSTEM_OVERVIEW.md",
    "DIRECTORY_STRUCTURE.md",
    "API_REFERENCE.md",
    "DATABASE.md",
    "SECURITY.md",
    "OBSERVABILITY.md",
    "DEPLOYMENT.md",
    "SCALING.md",
    "TESTING.md",
    "CONTRIBUTING.md",
    "DEVELOPMENT.md",
    "OPERATIONS.md",
    "TROUBLESHOOTING.md",
    "CHANGELOG.md",
    "ROADMAP.md",
    "GLOSSARY.md",
    "FAQ.md",
]


class TestDocumentationFilesExist:
    """Validate that all required documentation files exist."""

    @pytest.mark.parametrize("filename", REQUIRED_DOCS)
    def test_doc_file_exists(self, filename: str) -> None:
        doc_path = DOCS_DIR / filename
        assert doc_path.exists(), f"Missing documentation file: docs/{filename}"

    @pytest.mark.parametrize("filename", REQUIRED_DOCS)
    def test_doc_file_not_empty(self, filename: str) -> None:
        doc_path = DOCS_DIR / filename
        if doc_path.exists():
            content = doc_path.read_text(encoding="utf-8")
            assert len(content) > 50, f"Documentation file too short: docs/{filename}"

    def test_docs_directory_has_files(self) -> None:
        assert DOCS_DIR.exists(), "docs/ directory does not exist"
        md_files = list(DOCS_DIR.glob("*.md"))
        assert len(md_files) >= 19, f"Expected at least 19 docs, found {len(md_files)}"


# ---------------------------------------------------------------------------
# Content validation
# ---------------------------------------------------------------------------

class TestDocumentationContent:
    """Validate documentation content quality."""

    def test_readme_has_title(self) -> None:
        content = (DOCS_DIR / "README.md").read_text(encoding="utf-8")
        assert "# NOVA CORE" in content or "# nova-core" in content.lower()

    def test_readme_has_quickstart(self) -> None:
        content = (DOCS_DIR / "README.md").read_text(encoding="utf-8")
        assert "Quick Start" in content or "quick start" in content.lower() or "Setup" in content

    def test_readme_has_structure(self) -> None:
        content = (DOCS_DIR / "README.md").read_text(encoding="utf-8")
        assert "Project Structure" in content or "Directory" in content or "Layout" in content

    def test_architecture_has_principles(self) -> None:
        content = (DOCS_DIR / "ARCHITECTURE.md").read_text(encoding="utf-8")
        assert "SOLID" in content or "Clean Architecture" in content or "Async" in content

    def test_architecture_has_patterns(self) -> None:
        content = (DOCS_DIR / "ARCHITECTURE.md").read_text(encoding="utf-8")
        assert "Strategy" in content or "Provider" in content or "Factory" in content

    def test_system_overview_lists_subsystems(self) -> None:
        content = (DOCS_DIR / "SYSTEM_OVERVIEW.md").read_text(encoding="utf-8")
        assert "Cognitive" in content
        assert "Event" in content or "Event System" in content

    def test_api_reference_has_endpoints(self) -> None:
        content = (DOCS_DIR / "API_REFERENCE.md").read_text(encoding="utf-8")
        assert "/agents" in content
        assert "/events" in content
        assert "/workflows" in content

    def test_database_has_models(self) -> None:
        content = (DOCS_DIR / "DATABASE.md").read_text(encoding="utf-8")
        assert "ConversationSession" in content or "Goal" in content

    def test_security_has_auth(self) -> None:
        content = (DOCS_DIR / "SECURITY.md").read_text(encoding="utf-8")
        assert "Authentication" in content or "auth" in content.lower()

    def test_deployment_has_docker(self) -> None:
        content = (DOCS_DIR / "DEPLOYMENT.md").read_text(encoding="utf-8")
        assert "Docker" in content or "docker" in content

    def test_scaling_has_strategies(self) -> None:
        content = (DOCS_DIR / "SCALING.md").read_text(encoding="utf-8")
        assert "Load Balanc" in content or "Worker" in content

    def test_testing_has_commands(self) -> None:
        content = (DOCS_DIR / "TESTING.md").read_text(encoding="utf-8")
        assert "pytest" in content

    def test_glossary_has_terms(self) -> None:
        content = (DOCS_DIR / "GLOSSARY.md").read_text(encoding="utf-8")
        assert "Cognitive Engine" in content or "Knowledge Graph" in content

    def test_faq_has_qa(self) -> None:
        content = (DOCS_DIR / "FAQ.md").read_text(encoding="utf-8")
        assert "###" in content or "Q:" in content or "?" in content

    def test_changelog_has_version(self) -> None:
        content = (DOCS_DIR / "CHANGELOG.md").read_text(encoding="utf-8")
        assert "0.1.0" in content or "v0.1.0" in content or "1.0.0" in content or "v1.0.0" in content

    def test_roadmap_has_future(self) -> None:
        content = (DOCS_DIR / "ROADMAP.md").read_text(encoding="utf-8")
        assert "Future" in content or "roadmap" in content.lower()

    def test_contributing_has_steps(self) -> None:
        content = (DOCS_DIR / "CONTRIBUTING.md").read_text(encoding="utf-8")
        assert "fork" in content.lower() or "Pull Request" in content or "clone" in content.lower()

    def test_operations_has_monitoring(self) -> None:
        content = (DOCS_DIR / "OPERATIONS.md").read_text(encoding="utf-8")
        assert "monitor" in content.lower() or "health" in content.lower()


# ---------------------------------------------------------------------------
# Mermaid diagram validation
# ---------------------------------------------------------------------------

MERMAID_PATTERN = re.compile(r"```mermaid\s*\n(.*?)```", re.DOTALL)


def _extract_mermaid_blocks(content: str) -> list[str]:
    return MERMAID_PATTERN.findall(content)


def _validate_mermaid_syntax(block: str) -> bool:
    block = block.strip()
    if not block:
        return False
    first_line = block.split("\n")[0].strip()
    valid_starts = {
        "graph", "flowchart", "sequenceDiagram", "classDiagram",
        "stateDiagram", "erDiagram", "gantt", "pie", "gitgraph",
        "mindmap", "timeline", "block-beta", "kanban",
    }
    for valid in valid_starts:
        if first_line.startswith(valid):
            return True
    return False


class TestMermaidDiagrams:
    """Validate Mermaid diagram syntax in documentation."""

    @pytest.mark.parametrize("filename", REQUIRED_DOCS)
    def test_mermaid_blocks_valid(self, filename: str) -> None:
        doc_path = DOCS_DIR / filename
        if not doc_path.exists():
            pytest.skip(f"File not found: {filename}")
        content = doc_path.read_text(encoding="utf-8")
        blocks = _extract_mermaid_blocks(content)
        for i, block in enumerate(blocks):
            assert _validate_mermaid_syntax(block), (
                f"Invalid Mermaid syntax in docs/{filename} block {i + 1}: "
                f"{block[:80]}..."
            )


# ---------------------------------------------------------------------------
# Internal link validation
# ---------------------------------------------------------------------------

LINK_PATTERN = re.compile(r"\[([^\]]*)\]\(([^)]+)\)")


class TestInternalLinks:
    """Validate internal links in documentation."""

    @pytest.mark.parametrize("filename", REQUIRED_DOCS)
    def test_internal_links_valid(self, filename: str) -> None:
        doc_path = DOCS_DIR / filename
        if not doc_path.exists():
            pytest.skip(f"File not found: {filename}")
        content = doc_path.read_text(encoding="utf-8")
        links = LINK_PATTERN.findall(content)
        for link_text, link_target in links:
            if link_target.startswith("http://") or link_target.startswith("https://"):
                continue
            if link_target.startswith("#"):
                continue
            if link_target.startswith("mailto:"):
                continue
            if ":" in link_target and not os.name == "nt":
                continue
            if link_target.endswith("LICENSE"):
                continue
            target_path = (doc_path.parent / link_target).resolve()
            assert target_path.exists(), (
                f"Broken link in docs/{filename}: [{link_text}]({link_target})"
            )


# ---------------------------------------------------------------------------
# API route documentation vs actual routes
# ---------------------------------------------------------------------------

class TestAPIDocumentationMatch:
    """Validate that API documentation references actual route files."""

    def test_api_reference_mentions_agents(self) -> None:
        content = (DOCS_DIR / "API_REFERENCE.md").read_text(encoding="utf-8")
        assert "/agents" in content

    def test_api_reference_mentions_events(self) -> None:
        content = (DOCS_DIR / "API_REFERENCE.md").read_text(encoding="utf-8")
        assert "/events" in content

    def test_api_reference_mentions_workflows(self) -> None:
        content = (DOCS_DIR / "API_REFERENCE.md").read_text(encoding="utf-8")
        assert "/workflows" in content

    def test_api_reference_mentions_scheduler(self) -> None:
        content = (DOCS_DIR / "API_REFERENCE.md").read_text(encoding="utf-8")
        assert "/scheduler" in content

    def test_api_reference_mentions_security(self) -> None:
        content = (DOCS_DIR / "API_REFERENCE.md").read_text(encoding="utf-8")
        assert "/security" in content

    def test_api_reference_mentions_plugins(self) -> None:
        content = (DOCS_DIR / "API_REFERENCE.md").read_text(encoding="utf-8")
        assert "/plugins" in content

    def test_api_reference_mentions_knowledge_graph(self) -> None:
        content = (DOCS_DIR / "API_REFERENCE.md").read_text(encoding="utf-8")
        assert "/knowledge-graph" in content

    def test_api_reference_mentions_rag(self) -> None:
        content = (DOCS_DIR / "API_REFERENCE.md").read_text(encoding="utf-8")
        assert "/rag" in content

    def test_api_reference_mentions_vector_memory(self) -> None:
        content = (DOCS_DIR / "API_REFERENCE.md").read_text(encoding="utf-8")
        assert "/vector-memory" in content

    def test_api_reference_mentions_models(self) -> None:
        content = (DOCS_DIR / "API_REFERENCE.md").read_text(encoding="utf-8")
        assert "/models" in content

    def test_api_reference_mentions_tools(self) -> None:
        content = (DOCS_DIR / "API_REFERENCE.md").read_text(encoding="utf-8")
        assert "/tools" in content

    def test_api_reference_mentions_database(self) -> None:
        content = (DOCS_DIR / "API_REFERENCE.md").read_text(encoding="utf-8")
        assert "/database" in content

    def test_api_reference_mentions_deployment(self) -> None:
        content = (DOCS_DIR / "API_REFERENCE.md").read_text(encoding="utf-8")
        assert "/deployment" in content

    def test_api_reference_mentions_scaling(self) -> None:
        content = (DOCS_DIR / "API_REFERENCE.md").read_text(encoding="utf-8")
        assert "/scaling" in content

    def test_api_reference_mentions_future(self) -> None:
        content = (DOCS_DIR / "API_REFERENCE.md").read_text(encoding="utf-8")
        assert "/future" in content

    def test_api_reference_mentions_observability(self) -> None:
        content = (DOCS_DIR / "API_REFERENCE.md").read_text(encoding="utf-8")
        assert "/observability" in content

    def test_api_reference_mentions_goals(self) -> None:
        content = (DOCS_DIR / "API_REFERENCE.md").read_text(encoding="utf-8")
        assert "/goals" in content

    def test_api_reference_mentions_tasks(self) -> None:
        content = (DOCS_DIR / "API_REFERENCE.md").read_text(encoding="utf-8")
        assert "/tasks" in content

    def test_api_reference_mentions_learning(self) -> None:
        content = (DOCS_DIR / "API_REFERENCE.md").read_text(encoding="utf-8")
        assert "/learning" in content


# ---------------------------------------------------------------------------
# Cross-reference validation
# ---------------------------------------------------------------------------

class TestCrossReferences:
    """Validate that documentation files cross-reference each other."""

    def test_readme_links_to_architecture(self) -> None:
        content = (DOCS_DIR / "README.md").read_text(encoding="utf-8")
        assert "ARCHITECTURE" in content or "Architecture" in content

    def test_readme_links_to_api_reference(self) -> None:
        content = (DOCS_DIR / "README.md").read_text(encoding="utf-8")
        assert "API_REFERENCE" in content or "API Reference" in content

    def test_readme_links_to_testing(self) -> None:
        content = (DOCS_DIR / "README.md").read_text(encoding="utf-8")
        assert "TESTING" in content or "Testing" in content

    def test_readme_links_to_deployment(self) -> None:
        content = (DOCS_DIR / "README.md").read_text(encoding="utf-8")
        assert "DEPLOYMENT" in content or "Deployment" in content


# ---------------------------------------------------------------------------
# Implementation code references
# ---------------------------------------------------------------------------

class TestCodeReferences:
    """Validate that documentation references match actual code."""

    def test_architecture_references_app_packages(self) -> None:
        content = (DOCS_DIR / "ARCHITECTURE.md").read_text(encoding="utf-8")
        assert "app." in content

    def test_system_overview_references_all_layers(self) -> None:
        content = (DOCS_DIR / "SYSTEM_OVERVIEW.md").read_text(encoding="utf-8")
        assert "Cognitive" in content
        assert "Execution" in content or "Task" in content
        assert "Infrastructure" in content or "Event" in content
        assert "Platform" in content or "Security" in content

    def test_database_references_sqlalchemy(self) -> None:
        content = (DOCS_DIR / "DATABASE.md").read_text(encoding="utf-8")
        assert "SQLAlchemy" in content or "sqlalchemy" in content

    def test_testing_references_pytest(self) -> None:
        content = (DOCS_DIR / "TESTING.md").read_text(encoding="utf-8")
        assert "pytest" in content

    def test_deployment_references_docker(self) -> None:
        content = (DOCS_DIR / "DEPLOYMENT.md").read_text(encoding="utf-8")
        assert "docker" in content.lower()

    def test_deployment_references_kubernetes(self) -> None:
        content = (DOCS_DIR / "DEPLOYMENT.md").read_text(encoding="utf-8")
        assert "kubernetes" in content.lower() or "kubectl" in content.lower() or "k8s" in content.lower()


# ---------------------------------------------------------------------------
# Edge cases
# ---------------------------------------------------------------------------

class TestEdgeCases:
    """Edge case tests for documentation."""

    def test_all_docs_are_utf8(self) -> None:
        for filename in REQUIRED_DOCS:
            doc_path = DOCS_DIR / filename
            if doc_path.exists():
                content = doc_path.read_text(encoding="utf-8")
                assert isinstance(content, str), f"File {filename} is not valid UTF-8"

    def test_no_broken_mermaid_fences(self) -> None:
        for filename in REQUIRED_DOCS:
            doc_path = DOCS_DIR / filename
            if not doc_path.exists():
                continue
            content = doc_path.read_text(encoding="utf-8")
            opens = content.count("```mermaid")
            closes = content.count("```", content.find("mermaid") if "mermaid" in content else 0)
            # Each mermaid block opens with ```mermaid and closes with ```
            assert opens <= closes, f"Unclosed Mermaid block in docs/{filename}"

    def test_docs_have_headings(self) -> None:
        for filename in REQUIRED_DOCS:
            doc_path = DOCS_DIR / filename
            if not doc_path.exists():
                continue
            content = doc_path.read_text(encoding="utf-8")
            assert content.strip().startswith("#"), f"docs/{filename} should start with a heading"
