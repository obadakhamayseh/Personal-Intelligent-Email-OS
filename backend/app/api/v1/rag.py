from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.schemas.api_schemas import RagQueryRequest, RagQueryResponse
from app.services.rag_service import SemanticEmailRAGService

router = APIRouter(prefix="/rag", tags=["Semantic Email RAG"])


@router.post("/query", response_model=RagQueryResponse)
async def query_semantic_rag(
    payload: RagQueryRequest, db: AsyncSession = Depends(get_db)
):
    service = SemanticEmailRAGService()
    return await service.query(db, payload)
