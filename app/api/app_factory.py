"""
FastAPI Application Factory module
"""
from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles #Para archivos estáticos en un futuro, aunque el frontend irá en flutter
from fastapi.middleware.cors import CORSMiddleware

from app.settings import Settings
from app.api.include_routes import include_routes

def create_app(settings: Settings) -> FastAPI:
    """
    Crea y configura la aplicación FastAPI.
    
    Args:
        settings (Settings): Las configuraciones de la aplicación.
    
    Returns:
        FastAPI: Instancia de la aplicación FastAPI configurada.
    """
    app = FastAPI(
        title=settings.APP_NAME,
        description=f"{settings.APP_NAME} API",
        version=settings.APP_VERSION,
        docs_url="/docs",
        redoc_url="/redoc",
        openapi_url="/openapi.json",
    )

    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],
        allow_methods=["*"],
        allow_headers=["*"],
        allow_credentials=True,
    )

    include_routes(app, prefix="/api/v1")

    return app