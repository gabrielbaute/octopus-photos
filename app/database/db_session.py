from app.database.db_config import SessionLocal

# Dependency
def get_db():
    """
    Generador de sesión debase de datos.
    """
    db = SessionLocal() # Tu sessionmaker de SQLAlchemy
    try:
        yield db
    finally:
        db.close()