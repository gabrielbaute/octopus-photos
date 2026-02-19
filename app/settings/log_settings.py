import logging
from pathlib import Path
from typing import Dict, Optional
from logging.handlers import RotatingFileHandler

from app.settings.app_settings import settings

class OctopusLogger:
    """
    Configuración del sistema de logs.
    """
    # Parámetros de rotación: 5MB por archivo, manteniendo hasta 5 backups
    MAX_BYTES: int = 5 * 1024 * 1024 
    BACKUP_COUNT: int = 5
    LOG_FILE: Path = settings.LOGS_PATH / f"{settings.APP_NAME}.log"
    LEVEL_MAP: Dict[str, int] = {
        "DEBUG": logging.DEBUG,
        "INFO": logging.INFO,
        "WARNING": logging.WARNING,
        "ERROR": logging.ERROR,
        "CRITICAL": logging.CRITICAL
    }

    @staticmethod
    def setup_logging(level: Optional[str] = "INFO") -> None:
        """
        Configura el sistema de logging básico.

        Args:
            level (Optional[str]): Nivel de registro. Ejemplo: "DEBUG", "INFO", etc.

        Returns:
            None
        """
        # Aseguramos que el directorio de logs existe
        settings.LOGS_PATH.mkdir(parents=True, exist_ok=True)

        # Definimos el formato
        log_format = "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
        
        # Handler de Rotación
        rotate_handler = RotatingFileHandler(
            filename=OctopusLogger.LOG_FILE,
            mode="a",
            maxBytes=OctopusLogger.MAX_BYTES,
            backupCount=OctopusLogger.BACKUP_COUNT,
            encoding="utf-8"
        )

        # Handler de Consola
        stream_handler = logging.StreamHandler()

        logging.basicConfig(
            level=OctopusLogger.LEVEL_MAP.get(level, logging.INFO),
            format=log_format,
            datefmt="%Y-%m-%d %H:%M:%S",
            handlers=[rotate_handler, stream_handler]
        )