""" 
Entrypoint de la API
"""
import uvicorn

from app.settings import settings, OctopusLogger
from app.api.app_factory import create_app
from app.database.db_config import init_db

# Nos aseguramos que los directorios se crean
settings.ensure_dirs()

# Inicializamos el logger
OctopusLogger.setup_logging(level="INFO")

# Creamos la base de datos
init_db(settings=settings)

# Creamos la app de la API
app = create_app(settings=settings)

def run_server():
    """
    Run the FastAPI server.
    """
    uvicorn.run(
        "main:app",
        host=settings.API_HOST,
        port=settings.API_PORT,
        log_level="info",
        reload=False,
    )

if __name__ == "__main__":
    run_server()