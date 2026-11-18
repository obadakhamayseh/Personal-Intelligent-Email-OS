import math
from typing import Any, Dict, List, Optional
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.logging import get_logger
from app.models.entities import EmailEmbedding, EmailMetadata
from app.schemas.api_schemas import RagCitation, RagQueryRequest, RagQueryResponse
from app.services.llm_provider import LLMProviderService

logger = get_logger("rag_service")


def build_gmail_thread_url(thread_id: str) -> str:
    return f"https://mail.google.com/mail/u/0/#all/{thread_id}"


def _cosine_similarity(vec_a: List[float], vec_b: List[float]) -> float:
    if not vec_a or not vec_b or len(vec_a) != len(vec_b):
        return 0.0
    dot = sum(a * b for a, b in zip(vec_a, vec_b))
    norm_a = math.sqrt(sum(a * a for a in vec_a)) or 1.0
    norm_b = math.sqrt(sum(b * b for b in vec_b)) or 1.0
    return float(dot / (norm_a * norm_b))


class SemanticEmailRAGService:
    """
    Semantic Email RAG Engine using pgvector cosine distance (with portable fallback)
    returning natural-language answers in Arabic or English with clickable Gmail thread citations.
    """

    def __init__(self, llm_service: Optional[LLMProviderService] = None):
        self.llm = llm_service or LLMProviderService()

    async def query(
        self, db: AsyncSession, req: RagQueryRequest
    ) -> RagQueryResponse:
        q_embedding = await self.llm.generate_embedding(req.question)
        dialect_name = db.bind.dialect.name if db.bind else "postgresql"

        citations: List[RagCitation] = []

        if dialect_name == "postgresql":
            try:
                distance_expr = EmailEmbedding.embedding.cosine_distance(q_embedding)
                stmt = (
                    select(EmailEmbedding, EmailMetadata, (1.0 - distance_expr).label("similarity"))
                    .join(EmailMetadata, EmailMetadata.message_id == EmailEmbedding.message_id)
                    .where(EmailMetadata.is_trashed.is_(False))
                )
                if req.category_filter:
                    stmt = stmt.where(EmailEmbedding.category == req.category_filter.value)
                stmt = stmt.order_by(distance_expr.asc()).limit(req.top_k)
                rows = (await db.execute(stmt)).all()
                for emb, meta, sim in rows:
                    citations.append(
                        RagCitation(
                            message_id=meta.message_id,
                            thread_id=meta.thread_id,
                            subject=meta.subject,
                            sender_email=meta.sender_email,
                            internal_date=meta.internal_date,
                            category=meta.category,
                            similarity_score=round(max(0.0, float(sim)), 4),
                            gmail_thread_url=build_gmail_thread_url(meta.thread_id),
                            snippet=meta.ai_summary or meta.snippet,
                        )
                    )
            except Exception as exc:
                logger.warning("pgvector_query_fallback_to_portable", error=str(exc))

        if not citations:
            stmt = (
                select(EmailEmbedding, EmailMetadata)
                .join(EmailMetadata, EmailMetadata.message_id == EmailEmbedding.message_id)
                .where(EmailMetadata.is_trashed.is_(False))
            )
            if req.category_filter:
                stmt = stmt.where(EmailEmbedding.category == req.category_filter.value)
            rows = (await db.execute(stmt)).all()

            scored: List[tuple[float, EmailMetadata]] = []
            q_lower = req.question.lower()
            for emb, meta in rows:
                vec = list(emb.embedding) if emb.embedding is not None else []
                sim = _cosine_similarity(q_embedding, vec)
                # Boost exact keyword overlap for hybrid accuracy
                text_blob = f"{meta.subject} {meta.snippet} {meta.body_text} {meta.sender_email}".lower()
                for word in q_lower.split():
                    if len(word) >= 3 and word in text_blob:
                        sim += 0.15
                scored.append((min(0.9999, sim), meta))

            scored.sort(key=lambda x: x[0], reverse=True)
            for sim, meta in scored[: req.top_k]:
                citations.append(
                    RagCitation(
                        message_id=meta.message_id,
                        thread_id=meta.thread_id,
                        subject=meta.subject,
                        sender_email=meta.sender_email,
                        internal_date=meta.internal_date,
                        category=meta.category,
                        similarity_score=round(max(0.0, sim), 4),
                        gmail_thread_url=build_gmail_thread_url(meta.thread_id),
                        snippet=meta.ai_summary or meta.snippet,
                    )
                )

        context_dicts: List[Dict[str, Any]] = [c.model_dump() for c in citations]
        answer = await self.llm.synthesize_rag_answer(req.question, context_dicts)

        return RagQueryResponse(
            question=req.question,
            answer=answer,
            citations=citations,
        )
