"""
Módulo para las rutas de check healt y status
"""
from fastapi import APIRouter, Depends, status, HTTPException
from fastapi.responses import JSONResponse

from app.api.dependencies import get_settings_instance
from app.settings import Settings

router = APIRouter(prefix="/check", tags=["Check-Health"])

@router.get("/health", status_code=status.HTTP_200_OK)
def health_check():
    """Health check endpoint to verify API is running."""
    return JSONResponse(
        status_code=status.HTTP_200_OK,
        content={
            "status": "OK",
            "message": "API is running",
        }
    )

@router.get("/server-info", status_code=status.HTTP_200_OK)
def get_server_info(settings: Settings = Depends(get_settings_instance)):
    """Endpoint para obtener información del servidor."""
    return JSONResponse(
        status_code=status.HTTP_200_OK,
        content={
            "server_name": settings.APP_NAME,
            "server_version": settings.APP_VERSION,
        }
    )