from app.errors.base import OctopusError

class ConfigurationError(OctopusError):
    """Excepción lanzada cuando faltan variables de entorno o la configuración es inválida."""
    def __init__(self, message: str, missing_fields: list[str] = None):
        super().__init__(message=message, details={"missing_fields": missing_fields})