"""RAG chunking strategies — split documents into manageable pieces."""

from __future__ import annotations

import re
from typing import Any, Optional
from uuid import uuid4

from app.rag.base import Chunker
from app.rag.schemas import Chunk, ChunkMetadata, ChunkStrategy


class FixedSizeChunker(Chunker):
    """Splits text into fixed-size chunks."""

    @property
    def chunker_id(self) -> str:
        return "fixed_size"

    async def chunk(
        self,
        content: str,
        metadata: Optional[ChunkMetadata] = None,
        chunk_size: int = 512,
        chunk_overlap: int = 50,
        **kwargs: Any,
    ) -> list[Chunk]:
        meta = metadata or ChunkMetadata(strategy=ChunkStrategy.FIXED)
        chunks: list[Chunk] = []
        start = 0
        idx = 0
        while start < len(content):
            end = min(start + chunk_size, len(content))
            text = content[start:end]
            chunk_meta = ChunkMetadata(
                chunk_id=str(uuid4()),
                document_id=meta.document_id,
                source_id=meta.source_id,
                title=meta.title,
                chunk_index=idx,
                start_char=start,
                end_char=end,
                token_count=len(text.split()),
                strategy=ChunkStrategy.FIXED,
                tags=meta.tags,
                source=meta.source,
                author=meta.author,
                category=meta.category,
                language=meta.language,
                confidence=meta.confidence,
                metadata=meta.metadata,
            )
            chunks.append(Chunk(id=chunk_meta.chunk_id, content=text, metadata=chunk_meta))
            start += chunk_size - chunk_overlap
            idx += 1
        return chunks


class SemanticChunker(Chunker):
    """Splits text at semantic boundaries (sentences/paragraphs)."""

    @property
    def chunker_id(self) -> str:
        return "semantic"

    async def chunk(
        self,
        content: str,
        metadata: Optional[ChunkMetadata] = None,
        chunk_size: int = 512,
        chunk_overlap: int = 50,
        **kwargs: Any,
    ) -> list[Chunk]:
        meta = metadata or ChunkMetadata(strategy=ChunkStrategy.SEMANTIC)
        sentences = re.split(r'(?<=[.!?])\s+', content)
        chunks: list[Chunk] = []
        current_text = ""
        start = 0
        idx = 0
        for sentence in sentences:
            if len(current_text) + len(sentence) > chunk_size and current_text:
                chunk_meta = ChunkMetadata(
                    chunk_id=str(uuid4()),
                    document_id=meta.document_id,
                    source_id=meta.source_id,
                    title=meta.title,
                    chunk_index=idx,
                    start_char=start,
                    end_char=start + len(current_text),
                    token_count=len(current_text.split()),
                    strategy=ChunkStrategy.SEMANTIC,
                    tags=meta.tags,
                    source=meta.source,
                    author=meta.author,
                    category=meta.category,
                    language=meta.language,
                    confidence=meta.confidence,
                    metadata=meta.metadata,
                )
                chunks.append(Chunk(id=chunk_meta.chunk_id, content=current_text.strip(), metadata=chunk_meta))
                overlap_text = current_text[-chunk_overlap:] if chunk_overlap > 0 else ""
                start = start + len(current_text) - len(overlap_text)
                current_text = overlap_text + " "
                idx += 1
            current_text += sentence + " "
        if current_text.strip():
            chunk_meta = ChunkMetadata(
                chunk_id=str(uuid4()),
                document_id=meta.document_id,
                source_id=meta.source_id,
                title=meta.title,
                chunk_index=idx,
                start_char=start,
                end_char=start + len(current_text),
                token_count=len(current_text.split()),
                strategy=ChunkStrategy.SEMANTIC,
                tags=meta.tags,
                source=meta.source,
                author=meta.author,
                category=meta.category,
                language=meta.language,
                confidence=meta.confidence,
                metadata=meta.metadata,
            )
            chunks.append(Chunk(id=chunk_meta.chunk_id, content=current_text.strip(), metadata=chunk_meta))
        return chunks


class RecursiveChunker(Chunker):
    """Recursively splits by paragraph, then sentence, then word."""

    @property
    def chunker_id(self) -> str:
        return "recursive"

    async def chunk(
        self,
        content: str,
        metadata: Optional[ChunkMetadata] = None,
        chunk_size: int = 512,
        chunk_overlap: int = 50,
        **kwargs: Any,
    ) -> list[Chunk]:
        meta = metadata or ChunkMetadata(strategy=ChunkStrategy.RECURSIVE)
        separators = ["\n\n", "\n", ". ", " "]
        return await self._recursive_split(content, meta, chunk_size, chunk_overlap, separators, 0)

    async def _recursive_split(
        self,
        text: str,
        metadata: ChunkMetadata,
        chunk_size: int,
        chunk_overlap: int,
        separators: list[str],
        depth: int,
    ) -> list[Chunk]:
        if len(text) <= chunk_size:
            chunk_meta = ChunkMetadata(
                chunk_id=str(uuid4()),
                document_id=metadata.document_id,
                source_id=metadata.source_id,
                title=metadata.title,
                chunk_index=0,
                start_char=0,
                end_char=len(text),
                token_count=len(text.split()),
                strategy=ChunkStrategy.RECURSIVE,
                tags=metadata.tags,
                source=metadata.source,
                author=metadata.author,
                category=metadata.category,
                language=metadata.language,
                confidence=metadata.confidence,
                metadata=metadata.metadata,
            )
            return [Chunk(id=chunk_meta.chunk_id, content=text.strip(), metadata=chunk_meta)]

        sep = separators[depth] if depth < len(separators) else separators[-1]
        parts = text.split(sep)
        chunks: list[Chunk] = []
        current = ""
        idx = 0
        for part in parts:
            candidate = current + sep + part if current else part
            if len(candidate) > chunk_size and current:
                chunk_meta = ChunkMetadata(
                    chunk_id=str(uuid4()),
                    document_id=metadata.document_id,
                    source_id=metadata.source_id,
                    title=metadata.title,
                    chunk_index=idx,
                    start_char=0,
                    end_char=len(current),
                    token_count=len(current.split()),
                    strategy=ChunkStrategy.RECURSIVE,
                    tags=metadata.tags,
                    source=metadata.source,
                    author=metadata.author,
                    category=metadata.category,
                    language=metadata.language,
                    confidence=metadata.confidence,
                    metadata=metadata.metadata,
                )
                chunks.append(Chunk(id=chunk_meta.chunk_id, content=current.strip(), metadata=chunk_meta))
                idx += 1
                current = part
            else:
                current = candidate
        if current.strip():
            chunk_meta = ChunkMetadata(
                chunk_id=str(uuid4()),
                document_id=metadata.document_id,
                source_id=metadata.source_id,
                title=metadata.title,
                chunk_index=idx,
                start_char=0,
                end_char=len(current),
                token_count=len(current.split()),
                strategy=ChunkStrategy.RECURSIVE,
                tags=metadata.tags,
                source=metadata.source,
                author=metadata.author,
                category=metadata.category,
                language=metadata.language,
                confidence=metadata.confidence,
                metadata=metadata.metadata,
            )
            chunks.append(Chunk(id=chunk_meta.chunk_id, content=current.strip(), metadata=chunk_meta))
        return chunks


class MarkdownChunker(Chunker):
    """Splits markdown by headings and structural elements."""

    @property
    def chunker_id(self) -> str:
        return "markdown"

    async def chunk(
        self,
        content: str,
        metadata: Optional[ChunkMetadata] = None,
        chunk_size: int = 512,
        chunk_overlap: int = 50,
        **kwargs: Any,
    ) -> list[Chunk]:
        meta = metadata or ChunkMetadata(strategy=ChunkStrategy.MARKDOWN)
        heading_pattern = re.compile(r'^(#{1,6}\s+.+)$', re.MULTILINE)
        parts = heading_pattern.split(content)
        chunks: list[Chunk] = []
        idx = 0
        current = ""
        start = 0
        for part in parts:
            if heading_pattern.match(part):
                if current.strip():
                    chunk_meta = ChunkMetadata(
                        chunk_id=str(uuid4()),
                        document_id=meta.document_id,
                        source_id=meta.source_id,
                        title=meta.title,
                        chunk_index=idx,
                        start_char=start,
                        end_char=start + len(current),
                        token_count=len(current.split()),
                        strategy=ChunkStrategy.MARKDOWN,
                        tags=meta.tags,
                        source=meta.source,
                        author=meta.author,
                        category=meta.category,
                        language=meta.language,
                        confidence=meta.confidence,
                        metadata=meta.metadata,
                    )
                    chunks.append(Chunk(id=chunk_meta.chunk_id, content=current.strip(), metadata=chunk_meta))
                    idx += 1
                    start += len(current)
                    current = ""
            current += part + "\n"
        if current.strip():
            chunk_meta = ChunkMetadata(
                chunk_id=str(uuid4()),
                document_id=meta.document_id,
                source_id=meta.source_id,
                title=meta.title,
                chunk_index=idx,
                start_char=start,
                end_char=start + len(current),
                token_count=len(current.split()),
                strategy=ChunkStrategy.MARKDOWN,
                tags=meta.tags,
                source=meta.source,
                author=meta.author,
                category=meta.category,
                language=meta.language,
                confidence=meta.confidence,
                metadata=meta.metadata,
            )
            chunks.append(Chunk(id=chunk_meta.chunk_id, content=current.strip(), metadata=chunk_meta))
        if not chunks:
            small_size = min(chunk_size, len(content))
            small_chunker = FixedSizeChunker()
            return await small_chunker.chunk(content, metadata, small_size, chunk_overlap)
        return chunks


class CodeChunker(Chunker):
    """Splits code by functions, classes, and logical blocks."""

    @property
    def chunker_id(self) -> str:
        return "code"

    async def chunk(
        self,
        content: str,
        metadata: Optional[ChunkMetadata] = None,
        chunk_size: int = 512,
        chunk_overlap: int = 50,
        **kwargs: Any,
    ) -> list[Chunk]:
        meta = metadata or ChunkMetadata(strategy=ChunkStrategy.CODE)
        block_pattern = re.compile(
            r'^(?:(?:async\s+)?(?:def|class|function|module)\s+\w+|'
            r'(?:if|for|while|try|with)\s+.+:|'
            r'#\s*region|#\s*endregion)',
            re.MULTILINE,
        )
        splits = block_pattern.split(content)
        chunks: list[Chunk] = []
        idx = 0
        current = ""
        start = 0
        for part in splits:
            candidate = current + part if current else part
            if len(candidate) > chunk_size and current.strip():
                chunk_meta = ChunkMetadata(
                    chunk_id=str(uuid4()),
                    document_id=meta.document_id,
                    source_id=meta.source_id,
                    title=meta.title,
                    chunk_index=idx,
                    start_char=start,
                    end_char=start + len(current),
                    token_count=len(current.split()),
                    strategy=ChunkStrategy.CODE,
                    tags=meta.tags,
                    source=meta.source,
                    author=meta.author,
                    category=meta.category,
                    language=meta.language,
                    confidence=meta.confidence,
                    metadata=meta.metadata,
                )
                chunks.append(Chunk(id=chunk_meta.chunk_id, content=current.strip(), metadata=chunk_meta))
                idx += 1
                start += len(current)
                current = part
            else:
                current = candidate
        if current.strip():
            chunk_meta = ChunkMetadata(
                chunk_id=str(uuid4()),
                document_id=meta.document_id,
                source_id=meta.source_id,
                title=meta.title,
                chunk_index=idx,
                start_char=start,
                end_char=start + len(current),
                token_count=len(current.split()),
                strategy=ChunkStrategy.CODE,
                tags=meta.tags,
                source=meta.source,
                author=meta.author,
                category=meta.category,
                language=meta.language,
                confidence=meta.confidence,
                metadata=meta.metadata,
            )
            chunks.append(Chunk(id=chunk_meta.chunk_id, content=current.strip(), metadata=chunk_meta))
        if not chunks:
            small_chunker = FixedSizeChunker()
            return await small_chunker.chunk(content, metadata, chunk_size, chunk_overlap)
        return chunks


def get_chunker(strategy: ChunkStrategy = ChunkStrategy.RECURSIVE) -> Chunker:
    """Factory for creating chunkers by strategy."""
    mapping: dict[ChunkStrategy, type[Chunker]] = {
        ChunkStrategy.FIXED: FixedSizeChunker,
        ChunkStrategy.SEMANTIC: SemanticChunker,
        ChunkStrategy.RECURSIVE: RecursiveChunker,
        ChunkStrategy.MARKDOWN: MarkdownChunker,
        ChunkStrategy.CODE: CodeChunker,
    }
    cls = mapping.get(strategy, RecursiveChunker)
    return cls()
