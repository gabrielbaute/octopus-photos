
"""
Módulo de configuración de la base de datos
"""
import logging
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from app.settings import Settings, settings
from app.database.db_base import Base
from app.database.models import (
    users_model, 
    storage_model, 
    photos_model, 
    albums_model, 
    associations
)

logger = logging.getLogger("DatabaseSettings")

logger.info("Creando engine...")
engine = create_engine(settings.DATABASE_URL, connect_args=settings.DATABASE_CONNECT_ARGS)
logger.info("Generando SessionLocal...")
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

def init_db(settings: Settings) -> None:
    """
    Inicializa la base de datos.

    Args:
        settings (Settings): Configuración de la aplicación.

    Returns:
        None
    """
    settings.INSTANCE_PATH.mkdir(parents=True, exist_ok=True)    
    try:
        Base.metadata.create_all(bind=engine)
        logger.info(f"Base de datos inicializada en: {settings.DATABASE_URL}")
    except Exception as e:
        logger.error(f"Error al inicializar la base de datos: {e}")