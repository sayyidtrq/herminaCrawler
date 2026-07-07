from __future__ import annotations

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.config import get_settings
from apps.api.app_api.errors import register_exception_handlers
from apps.api.app_api.routers import (
    analysis,
    dashboard,
    exports,
    fetch_jobs,
    fetch_logs,
    health,
    locations,
    pipeline,
    reviews,
    settings,
    auth,
    places,
    competitors,
)


def create_app() -> FastAPI:
    app = FastAPI(
        title="Hermina Review Intelligence API",
        version="0.1.0",
        docs_url="/api/docs",
        redoc_url="/api/redoc",
        openapi_url="/api/openapi.json",
    )
    app.add_middleware(
        CORSMiddleware,
        allow_origins=list(get_settings().cors_allowed_origins),
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )
    register_exception_handlers(app)
    app.include_router(health.router, prefix="/api")
    app.include_router(auth.router, prefix="/api")
    app.include_router(places.router, prefix="/api")
    app.include_router(competitors.router, prefix="/api")
    app.include_router(settings.router, prefix="/api")
    app.include_router(locations.router, prefix="/api")
    app.include_router(reviews.router, prefix="/api")
    app.include_router(dashboard.router, prefix="/api")
    app.include_router(fetch_jobs.router, prefix="/api")
    app.include_router(analysis.router, prefix="/api")
    app.include_router(exports.router, prefix="/api")
    app.include_router(pipeline.router, prefix="/api")
    app.include_router(fetch_logs.router, prefix="/api")
    return app


app = create_app()
