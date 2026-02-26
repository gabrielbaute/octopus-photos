"""
FastAPI Application Factory module
"""
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.settings import Settings
from app.api.web_client import setup_web_client
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

    # Inicializamos los routers de la API
    include_routes(app, prefix="/api/v1")

    # Servimos el cliente web
    setup_web_client(app, settings)

    return app