import pytest
from unittest.mock import MagicMock
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.settings import settings
from app.database.db_base import Base

@pytest.fixture
def mock_mail_service():
    """Mock para evitar envíos de correos reales."""
    return MagicMock()

@pytest.fixture
def db_session():
    """Sesión de DB en memoria para aislamiento total."""
    engine = create_engine("sqlite:///:memory:", connect_args={"check_same_thread": False})
    Base.metadata.create_all(bind=engine)
    Session = sessionmaker(bind=engine)
    session = Session()
    yield session
    session.close()

@pytest.fixture
def temp_storage(tmp_path, monkeypatch):
    """Crea un directorio temporal para STORAGE_BASE_PATH y lo limpia al terminar."""
    storage_dir = tmp_path / "storage"
    storage_dir.mkdir()
    # Parcheamos el path en settings para que el servicio use el temporal
    monkeypatch.setattr(settings, "STORAGE_BASE_PATH", str(storage_dir))
    return storage_dir