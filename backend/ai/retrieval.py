"""
User-scoped, persistent Semantic Retrieval Service.
Searches SQLite-persisted chunk embeddings using cosine similarity.
Strictly isolates User A from User B, prevents cross-document data leakage,
and provides source citations (document title, filename, page, section heading).
"""
import json
import logging
from typing import List, Dict, Any, Optional
from sqlalchemy.orm import Session

from backend.models import ChunkEmbedding, SourceChunk, Document
from backend.ai.embeddings import generate_local_embedding, cosine_similarity
from backend.ai.provider import BaseAIProvider

logger = logging.getLogger(__name__)

class RetrievalService:
    def __init__(self, db: Session, ai_provider: Optional[BaseAIProvider] = None):
        self.db = db
        if ai_provider is None:
            from backend.ai.gemini_provider import GeminiProvider
            self.ai_provider = GeminiProvider()
        else:
            self.ai_provider = ai_provider

    def index_chunk(self, user_id: str, document_id: str, chunk_id: str, text: str, force_local: bool = False) -> ChunkEmbedding:
        """
        Embeds and persists vector record for a source chunk.
        Safe against duplicates (replaces if exists).
        """
        # Determine embedding via provider or local deterministic fallback
        if not force_local and self.ai_provider and self.ai_provider.is_available():
            try:
                vector = self.ai_provider.generate_embedding(text)
                model_name = getattr(self.ai_provider, "embedding_model", "text-embedding-004")
            except Exception as e:
                logger.warning(f"Provider embedding failed, falling back to local: {e}")
                vector = generate_local_embedding(text)
                model_name = "local-hash-normalized-64"
        else:
            vector = generate_local_embedding(text)
            model_name = "local-hash-normalized-64"

        # Check existing
        existing = self.db.query(ChunkEmbedding).filter(ChunkEmbedding.chunk_id == chunk_id).first()
        if existing:
            existing.embedding_json = json.dumps(vector)
            existing.dimension = len(vector)
            existing.model_name = model_name
            self.db.commit()
            return existing

        new_emb = ChunkEmbedding(
            chunk_id=chunk_id,
            document_id=document_id,
            user_id=user_id,
            embedding_json=json.dumps(vector),
            dimension=len(vector),
            model_name=model_name
        )
        self.db.add(new_emb)
        self.db.commit()
        return new_emb

    def index_chunks_batch(
        self,
        user_id: str,
        document_id: str,
        chunk_records: List[SourceChunk]
    ) -> int:
        """
        Embeds and indexes all chunk records for a document with consistent vector representation.
        Guarantees that late-document pages share the same vector space and dimensionality as early pages.
        """
        if not chunk_records:
            return 0

        texts = [c.content for c in chunk_records]
        vectors = []
        model_name = "local-hash-normalized-64"

        if self.ai_provider and self.ai_provider.is_available():
            try:
                vectors = self.ai_provider.generate_embeddings_batch(texts)
                model_name = getattr(self.ai_provider, "embedding_model", "text-embedding-004")
            except Exception as e:
                logger.warning(f"Batch embedding via provider failed ({e}), using local hash embeddings.")
                vectors = [generate_local_embedding(t) for t in texts]
                model_name = "local-hash-normalized-64"
        else:
            vectors = [generate_local_embedding(t) for t in texts]
            model_name = "local-hash-normalized-64"

        for chunk_rec, vec in zip(chunk_records, vectors):
            existing = self.db.query(ChunkEmbedding).filter(ChunkEmbedding.chunk_id == chunk_rec.id).first()
            if existing:
                existing.embedding_json = json.dumps(vec)
                existing.dimension = len(vec)
                existing.model_name = model_name
            else:
                new_emb = ChunkEmbedding(
                    chunk_id=chunk_rec.id,
                    document_id=document_id,
                    user_id=user_id,
                    embedding_json=json.dumps(vec),
                    dimension=len(vec),
                    model_name=model_name
                )
                self.db.add(new_emb)
        self.db.commit()
        return len(chunk_records)

    def backfill_unindexed_chunks(self, user_id: Optional[str] = None) -> int:
        """
        Indexes any existing chunks in the database that do not yet have embeddings.
        Preserves all current user data without requiring re-upload.
        """
        query = (
            self.db.query(SourceChunk, Document.user_id)
            .join(Document, SourceChunk.document_id == Document.id)
            .outerjoin(ChunkEmbedding, SourceChunk.id == ChunkEmbedding.chunk_id)
            .filter(ChunkEmbedding.id == None)
        )
        if user_id:
            query = query.filter(Document.user_id == user_id)

        unindexed = query.all()
        indexed_count = 0
        for chunk, u_id in unindexed:
            try:
                self.index_chunk(
                    user_id=u_id,
                    document_id=chunk.document_id,
                    chunk_id=chunk.id,
                    text=chunk.content
                )
                indexed_count += 1
            except Exception as e:
                logger.error(f"Failed to index chunk {chunk.id}: {e}")

        return indexed_count

    def retrieve(
        self,
        user_id: str,
        query: str,
        document_ids: Optional[List[str]] = None,
        category_id: Optional[str] = None,
        top_k: int = 4
    ) -> List[Dict[str, Any]]:
        """
        Retrieves top_k source chunks for the user matching query.
        Security enforced: Queries strictly filtered by user_id and validated document_ids.
        """
        if not query or not query.strip():
            return []

        # 1. Compute query vector
        if self.ai_provider and self.ai_provider.is_available():
            try:
                query_vec = self.ai_provider.generate_embedding(query)
            except Exception:
                query_vec = generate_local_embedding(query)
        else:
            query_vec = generate_local_embedding(query)

        # 2. Build filtered SQL query
        q = (
            self.db.query(ChunkEmbedding, SourceChunk, Document)
            .join(SourceChunk, ChunkEmbedding.chunk_id == SourceChunk.id)
            .join(Document, ChunkEmbedding.document_id == Document.id)
            .filter(ChunkEmbedding.user_id == user_id)
        )

        # Document scoping with ownership validation
        if document_ids:
            # Ensure documents belong to this user
            valid_doc_ids = [
                d.id for d in self.db.query(Document.id)
                .filter(Document.id.in_(document_ids), Document.user_id == user_id)
                .all()
            ]
            if not valid_doc_ids:
                return []
            q = q.filter(ChunkEmbedding.document_id.in_(valid_doc_ids))

        # Category scoping
        if category_id:
            q = q.filter(Document.category_id == category_id)

        candidates = q.all()
        if not candidates:
            return []

        # 3. Compute cosine similarity scores
        scored = []
        for emb, chunk, doc in candidates:
            try:
                emb_vec = json.loads(emb.embedding_json)
                target_q_vec = query_vec
                if len(target_q_vec) != len(emb_vec):
                    target_q_vec = generate_local_embedding(query)
                sim = cosine_similarity(target_q_vec, emb_vec)
                scored.append({
                    "score": sim,
                    "chunk_id": chunk.id,
                    "document_id": doc.id,
                    "document_title": doc.title,
                    "filename": doc.filename,
                    "page_number": chunk.page_number,
                    "section_heading": chunk.section_heading,
                    "content": chunk.content,
                    "char_count": len(chunk.content)
                })
            except Exception as e:
                logger.warning(f"Error scoring embedding for chunk {chunk.id}: {e}")

        # 4. Sort descending by score and filter out low relevance noise
        scored.sort(key=lambda x: x["score"], reverse=True)
        # Retain chunks with genuine semantic relevance (sim >= 0.20, or top candidates if positive)
        relevant = [c for c in scored if c["score"] >= 0.20]
        if not relevant and scored:
            relevant = [c for c in scored if c["score"] > 0.05]
        return relevant[:top_k]

    def retrieve_comprehensive(
        self,
        user_id: str,
        query: str,
        document_ids: Optional[List[str]] = None,
        category_id: Optional[str] = None,
        max_chunks: int = 12
    ) -> List[Dict[str, Any]]:
        """
        Mode B: COMPREHENSIVE TOPIC RETRIEVAL.
        Retrieves grounded content distributed across document sections, headings,
        and concept inventories, preventing single-section truncation while enforcing user isolation.
        """
        # 1. Resolve validated document IDs
        q_docs = self.db.query(Document.id).filter(Document.user_id == user_id)
        if document_ids:
            q_docs = q_docs.filter(Document.id.in_(document_ids))
        if category_id:
            q_docs = q_docs.filter(Document.category_id == category_id)

        valid_doc_ids = [d.id for d in q_docs.all()]
        if not valid_doc_ids:
            return []

        # 2. Check if concept inventory is available for these documents
        from backend.concept_inventory import ConceptInventoryBuilder
        builder = ConceptInventoryBuilder(self.db)
        priority_chunk_ids = []
        for doc_id in valid_doc_ids:
            try:
                inv = builder.build_or_get_inventory(doc_id, user_id)
                if inv and inv.outline_json:
                    for sec in inv.outline_json:
                        if sec.get("chunk_id"):
                            priority_chunk_ids.append(sec["chunk_id"])
            except Exception as e:
                logger.warning(f"Error checking inventory for {doc_id}: {e}")

        # 3. Retrieve semantically top chunks
        top_semantic = self.retrieve(
            user_id=user_id,
            query=query,
            document_ids=valid_doc_ids,
            category_id=category_id,
            top_k=max_chunks
        )
        included_chunk_ids = {c["chunk_id"] for c in top_semantic}
        comprehensive_chunks = list(top_semantic)

        # 4. Supplement missing section chunks to ensure full outline coverage
        if len(comprehensive_chunks) < max_chunks and priority_chunk_ids:
            for p_id in priority_chunk_ids:
                if len(comprehensive_chunks) >= max_chunks:
                    break
                if p_id not in included_chunk_ids:
                    chunk = (
                        self.db.query(SourceChunk, Document)
                        .join(Document, SourceChunk.document_id == Document.id)
                        .filter(SourceChunk.id == p_id, Document.user_id == user_id)
                        .first()
                    )
                    if chunk:
                        sc, doc = chunk
                        included_chunk_ids.add(sc.id)
                        comprehensive_chunks.append({
                            "score": 0.85, # Section landmark
                            "chunk_id": sc.id,
                            "document_id": doc.id,
                            "document_title": doc.title,
                            "filename": doc.filename,
                            "page_number": sc.page_number,
                            "section_heading": sc.section_heading,
                            "content": sc.content,
                            "char_count": len(sc.content)
                        })

        # 5. If still space and chunks exist, include chronological progression of chunks
        if len(comprehensive_chunks) < max_chunks:
            remaining_chunks = (
                self.db.query(SourceChunk, Document)
                .join(Document, SourceChunk.document_id == Document.id)
                .filter(SourceChunk.document_id.in_(valid_doc_ids), Document.user_id == user_id)
                .order_by(SourceChunk.chunk_index.asc())
                .limit(max_chunks * 2)
                .all()
            )
            for sc, doc in remaining_chunks:
                if len(comprehensive_chunks) >= max_chunks:
                    break
                if sc.id not in included_chunk_ids:
                    included_chunk_ids.add(sc.id)
                    comprehensive_chunks.append({
                        "score": 0.60,
                        "chunk_id": sc.id,
                        "document_id": doc.id,
                        "document_title": doc.title,
                        "filename": doc.filename,
                        "page_number": sc.page_number,
                        "section_heading": sc.section_heading,
                        "content": sc.content,
                        "char_count": len(sc.content)
                    })

        return comprehensive_chunks[:max_chunks]

