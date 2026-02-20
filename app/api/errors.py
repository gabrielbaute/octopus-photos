from fastapi import FastAPI, Request, status
from fastapi.responses import JSONResponse
from app.errors.base import (
    OctopusError, 
    ResourceNotFoundError, 
    PermissionDeniedError, 
    StorageError,
    ValidationError # Asumiendo que tienes este
)

def register_error_handlers(app: FastAPI):
    """
    Registra los manejadores globales de excepciones para la aplicación.
    """

    @app.exception_handler(OctopusError)
    async def global_octopus_handler(request: Request, exc: OctopusError):
        # Mapeo riguroso de excepciones a códigos HTTP
        error_mapping = {
            ResourceNotFoundError: status.HTTP_404_NOT_FOUND,
            PermissionDeniedError: status.HTTP_403_FORBIDDEN,
            StorageError: status.HTTP_507_INSUFFICIENT_STORAGE,
            ValidationError: status.HTTP_400_BAD_REQUEST,
        }

        # Buscamos el código en el mapa, por defecto usamos 400
        http_status = error_mapping.get(type(exc), status.HTTP_400_BAD_REQUEST)

        # Si el error es una falla de autenticación en el login, 
        # aunque sea un ResourceNotFound, forzamos 401 por seguridad
        if "auth" in str(request.url) and isinstance(exc, ResourceNotFoundError):
            http_status = status.HTTP_401_UNAUTHORIZED

        return JSONResponse(
            status_code=http_status,
            content={
                "status": "error",
                "code": exc.__class__.__name__,
                "message": exc.message,
                "details": exc.details or {}
            },
        )

    @app.exception_handler(Exception)
    async def unhandled_exception_handler(request: Request, exc: Exception):
        """Captura cualquier error no controlado para evitar fugas de información."""
        # Aquí sí logueamos el traceback internamente para el ingeniero
        import logging
        logger = logging.getLogger("uvicorn.error")
        logger.error(f"Unhandled error: {str(exc)}", exc_info=True)

        return JSONResponse(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            content={
                "status": "error",
                "code": "InternalServerError",
                "message": "Ha ocurrido un error inesperado en el servidor."
            },
        )