"""
Módulo de configuración de la base de datos
"""
from pathlib import Path
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.settings import settings
from app.database.db_base import Base

engine = create_engine(settings.DATABASE_URL, connect_args=settings.DATABASE_CONNECT_ARGS)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

def init_db(instance_path: Path = settings.INSTANCE_PATH) -> None:
    """
    Inicializa la base de datos.
    
    Args:
        instance_path (Path): Ruta de la instancia de la base de datos.

    Returns:
        None
    """
    Path(instance_path).mkdir(parents=True, exist_ok=True)
    Base.metadata.create_all(bind=engine)