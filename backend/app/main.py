from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from app.core.config import settings
from app.core.exceptions import AppException
from app.api.routes import api_router


def create_application() -> FastAPI:
    """Factory creating and configuring the FastAPI application."""
    app = FastAPI(
        title=settings.PROJECT_NAME,
        description=settings.DESCRIPTION,
        version=settings.VERSION,
        docs_url="/docs",
        redoc_url="/redoc",
    )

    # Configure CORS middleware
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.ALLOWED_ORIGINS,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    # Exception handler for domain exceptions
    @app.exception_handler(AppException)
    async def app_exception_handler(request: Request, exc: AppException):
        return JSONResponse(
            status_code=exc.status_code,
            content={"success": False, "error": exc.message},
        )

    # Include modular API v1 router
    app.include_router(api_router, prefix=settings.API_V1_STR)

    @app.get(
        "/",
        summary="API Root",
        description="Root discovery endpoint confirming API presence and docs location.",
    )
    def root() -> dict:
        return {
            "message": "Welcome to NitiSetu API",
            "docs": "/docs",
            "version": settings.VERSION,
            "modules": {
                "laws": f"{settings.API_V1_STR}/laws/search",
                "schemes": f"{settings.API_V1_STR}/schemes",
                "documents": f"{settings.API_V1_STR}/documents/upload",
            },
        }

    return app


app = create_application()
