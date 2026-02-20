from typing import Any, Dict, Optional

class OctopusError(Exception):
    """Base para todos los errores de la aplicación."""
    def __init__(self, message: str, details: Optional[Dict[str, Any]] = None):
        super().__init__(message)
        self.message = message
        self.details = details or {}

class ValidationError(OctopusError):
    """Error de validación de datos o reglas de negocio."""
    pass

class ResourceNotFoundError(OctopusError):
    """Cuando un recurso (User, Photo, Album) no existe."""
    pass

class StorageError(OctopusError):
    """Errores físicos de disco o cuota."""
    pass

class PermissionDeniedError(OctopusError):
    """Cuando un usuario no tiene permisos para realizar una acción."""
    pass