from fastapi import APIRouter
from app.api.v1 import agentic, auth, cleanup, emails, intelligence, rag, rules

api_router = APIRouter()
api_router.include_router(emails.router)
api_router.include_router(rules.router)
api_router.include_router(cleanup.router)
api_router.include_router(rag.router)
api_router.include_router(intelligence.router)
api_router.include_router(auth.router)
api_router.include_router(agentic.router)
