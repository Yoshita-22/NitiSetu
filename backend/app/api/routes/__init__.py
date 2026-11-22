from fastapi import APIRouter
from app.api.routes import chat, document_routes, health, law_routes, scheme_routes

api_router = APIRouter()

# Register modular routes
api_router.include_router(health.router, tags=["Health"])
api_router.include_router(chat.router, prefix="/chat", tags=["Chat Test"])
api_router.include_router(law_routes.router, prefix="/laws", tags=["Laws & Rights (NyayKosh)"])
api_router.include_router(scheme_routes.router, prefix="/schemes", tags=["Welfare Schemes"])
api_router.include_router(document_routes.router, prefix="/documents", tags=["Document Intelligence (PDF)"])
