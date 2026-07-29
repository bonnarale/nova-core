#!/usr/bin/env python3
"""Bulk ingest amBotHs OS knowledge docs into nova-core RAG system.

Usage:
    # Ingest all knowledge docs
    python scripts/ingest_amboths_knowledge.py --source <ariel-v1.5.0>/knowledge

    # Ingest with Ollama embeddings (requires Ollama running)
    python scripts/ingest_amboths_knowledge.py --source <ariel-v1.5.0>/knowledge --provider ollama

    # Re-index (delete existing + re-add)
    python scripts/ingest_amboths_knowledge.py --source <ariel-v1.5.0>/knowledge --reindex

    # Test a query after ingestion
    python scripts/ingest_amboths_knowledge.py --source <ariel-v1.5.0>/knowledge --query "¿Qué es el Sentinel?"

    # Dry run (list files without ingesting)
    python scripts/ingest_amboths_knowledge.py --source <ariel-v1.5.0>/knowledge --dry-run
"""

from __future__ import annotations

import argparse
import asyncio
import logging
import sys
import time
from pathlib import Path
from typing import Optional

# Add backend to path so we can import app modules
sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "backend"))

from app.rag.embeddings import InMemoryEmbeddingProvider, OllamaEmbeddingProvider
from app.rag.engine import RAGEngine
from app.rag.factory import RAGFactory
from app.rag.index import RAGIndex
from app.rag.repository import InMemoryRepository
from app.rag.schemas import ChunkStrategy, IndexDocument, RetrievalQuery

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    datefmt="%H:%M:%S",
)
logger = logging.getLogger(__name__)


# ── Discovery ────────────────────────────────────────────────────────


def discover_knowledge_files(source_dir: Path) -> list[Path]:
    """Recursively find all .md files in the knowledge directory."""
    files: list[Path] = []
    for md_file in sorted(source_dir.rglob("*.md")):
        files.append(md_file)
    return files


def read_file_content(file_path: Path) -> Optional[str]:
    """Read a file's content as UTF-8 text. Returns None on failure."""
    try:
        return file_path.read_text(encoding="utf-8")
    except Exception as e:
        logger.warning("Failed to read %s: %s", file_path, e)
        return None


# ── Indexing ─────────────────────────────────────────────────────────


def build_index_document(
    file_path: Path,
    source_dir: Path,
    content: str,
    category: str = "amboths-knowledge",
) -> IndexDocument:
    """Build an IndexDocument from a markdown file."""
    # Use relative path as document ID for idempotency
    doc_id = str(file_path.relative_to(source_dir)).replace("\\", "/")
    # Derive title from filename
    title = file_path.stem.replace("-", " ").replace("_", " ").title()
    # Derive source tag from parent directory
    source_tag = str(file_path.parent.relative_to(source_dir)).replace("\\", "/")
    if source_tag == ".":
        source_tag = "root"

    return IndexDocument(
        document_id=f"amboths/{doc_id}",
        content=content,
        title=title,
        source=source_tag,
        author="amBotHs OS",
        category=category,
        language="es",  # Most knowledge docs are in Spanish
        tags=["amboths", "knowledge", source_tag],
        chunk_strategy=ChunkStrategy.MARKDOWN,
        chunk_size=512,
        chunk_overlap=50,
        metadata={
            "origin": "ariel-v1.5.0",
            "file_path": doc_id,
            "original_filename": file_path.name,
        },
    )


async def ingest_files(
    files: list[Path],
    source_dir: Path,
    engine: RAGEngine,
    reindex: bool = False,
) -> dict:
    """Ingest a list of files into the RAG engine. Returns summary stats."""
    stats = {
        "total_files": len(files),
        "indexed": 0,
        "skipped": 0,
        "failed": 0,
        "total_chunks": 0,
        "total_latency_ms": 0.0,
    }

    for i, file_path in enumerate(files, 1):
        logger.info("[%d/%d] Processing %s", i, len(files), file_path.name)

        content = read_file_content(file_path)
        if not content or len(content.strip()) < 10:
            logger.warning("  Skipping (too short or unreadable)")
            stats["skipped"] += 1
            continue

        doc = build_index_document(file_path, source_dir, content)

        # Re-index: remove existing chunks first
        if reindex:
            try:
                await engine.index.remove_document(doc.document_id)
                logger.info("  Removed existing chunks for %s", doc.document_id)
            except Exception:
                pass  # Document might not exist yet

        result = await engine.index_document(doc)

        if result.status.value == "indexed" or result.chunks_created > 0:
            stats["indexed"] += 1
            stats["total_chunks"] += result.chunks_created
            stats["total_latency_ms"] += result.latency_ms
            logger.info(
                "  Indexed: %d chunks in %.0fms",
                result.chunks_created,
                result.latency_ms,
            )
        else:
            stats["failed"] += 1
            logger.error("  Failed: %s", result.error)

    return stats


# ── Query test ───────────────────────────────────────────────────────


async def test_query(engine: RAGEngine, query: str) -> None:
    """Run a test query and print results."""
    logger.info("─" * 60)
    logger.info("Query: %s", query)
    logger.info("─" * 60)

    req = RetrievalQuery(query=query, top_k=5, threshold=0.0)
    result = await engine.retrieve(query, top_k=5)

    if not result.chunks:
        logger.info("No results found.")
        return

    for i, chunk in enumerate(result.chunks, 1):
        content_preview = chunk.chunk.content[:200].replace("\n", " ")
        logger.info(
            "  [%d] score=%.3f | %s\n      %s...",
            i,
            chunk.score,
            chunk.chunk.metadata.title,
            content_preview,
        )


# ── Main ─────────────────────────────────────────────────────────────


async def main(args: argparse.Namespace) -> None:
    source_dir = Path(args.source)
    if not source_dir.is_dir():
        logger.error("Source directory does not exist: %s", source_dir)
        sys.exit(1)

    # Discover files
    files = discover_knowledge_files(source_dir)
    logger.info("Found %d markdown files in %s", len(files), source_dir)

    if args.dry_run:
        logger.info("\n--- Dry Run ---")
        for f in files:
            rel = f.relative_to(source_dir)
            size = f.stat().st_size
            logger.info("  %s (%d bytes)", rel, size)
        return

    # Create embedding provider
    if args.provider == "ollama":
        logger.info("Using Ollama embeddings (model: %s)", args.model)
        embedder = OllamaEmbeddingProvider(
            model=args.model,
            base_url=args.ollama_url,
        )
    else:
        logger.info("Using InMemory embeddings (trigram hashing, no GPU needed)")
        embedder = InMemoryEmbeddingProvider(dimension=384)

    # Create repository (in-memory for simplicity; swap to Chroma for persistence)
    repository = InMemoryRepository()

    # Create RAG engine via factory
    factory = RAGFactory(
        embedder=embedder,
        repository=repository,
        collection="amboths-knowledge",
    )
    engine = factory.create_engine()
    await engine.initialize()

    logger.info("RAG engine ready (provider=%s, collection=%s)", args.provider, "amboths-knowledge")

    # Ingest
    start = time.time()
    stats = await ingest_files(files, source_dir, engine, reindex=args.reindex)
    elapsed = time.time() - start

    # Summary
    logger.info("\n" + "═" * 60)
    logger.info("INGESTION COMPLETE")
    logger.info("═" * 60)
    logger.info("  Files indexed:  %d", stats["indexed"])
    logger.info("  Files skipped:  %d", stats["skipped"])
    logger.info("  Files failed:   %d", stats["failed"])
    logger.info("  Total chunks:   %d", stats["total_chunks"])
    logger.info("  Total time:     %.1fs", elapsed)
    logger.info("  Avg latency:    %.0fms/chunk", stats["total_latency_ms"] / max(stats["total_chunks"], 1))
    logger.info("═" * 60)

    # Test query if requested
    if args.query:
        await test_query(engine, args.query)

    # Health check
    health = await engine.health()
    logger.info("\nEngine health: %s", health)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Ingest amBotHs knowledge docs into nova-core RAG",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=__doc__,
    )
    parser.add_argument(
        "--source",
        required=True,
        help="Path to amBotHs knowledge/ directory",
    )
    parser.add_argument(
        "--provider",
        choices=["in_memory", "ollama"],
        default="in_memory",
        help="Embedding provider (default: in_memory)",
    )
    parser.add_argument(
        "--model",
        default="nomic-embed-text",
        help="Ollama embedding model (default: nomic-embed-text)",
    )
    parser.add_argument(
        "--ollama-url",
        default="http://localhost:11434",
        help="Ollama base URL (default: http://localhost:11434)",
    )
    parser.add_argument(
        "--reindex",
        action="store_true",
        help="Re-index: remove existing chunks before adding",
    )
    parser.add_argument(
        "--query",
        help="Run a test query after ingestion",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="List files without ingesting",
    )
    return parser.parse_args()


if __name__ == "__main__":
    args = parse_args()
    asyncio.run(main(args))
