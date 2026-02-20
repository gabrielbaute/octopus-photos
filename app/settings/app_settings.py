import sys
from pathlib import Path
from pydantic import ValidationError
from pydantic_settings import BaseSettings, SettingsConfigDict

from app.settings.version import __version__
from app.errors.config_errors import ConfigurationError


class Settings(BaseSettings):
    # Datos base
    APP_NAME: str = "OctopusPhotos"
    APP_VERSION: str = __version__
    APP_URL: str = "http://localhost:8000"

    # Directorios
    BASE_PATH: Path = Path.home() / f".{APP_NAME}"
    UI_PATH: Path = Path(__file__).parent.parent / "ui"
    DATA_PATH: Path = BASE_PATH / "data"
    LOGS_PATH: Path = DATA_PATH / "logs"
    CONFIG_PATH: Path = BASE_PATH / "config"
    TMP_PATH: Path = DATA_PATH / "tmp"
    STORAGE_BASE_PATH: Path = DATA_PATH / "storage"

    # Database
    INSTANCE_PATH: Path = BASE_PATH / "instance"
    @property
    def DATABASE_URL(self) -> str:
        db_path = self.INSTANCE_PATH / f"{self.APP_NAME}.db"
        # En Windows, Path.absolute() devolverá algo como C:\Users\...
        # sqlite://// para absoluto
        return f"sqlite:///{db_path.absolute()}"
    
    DATABASE_ECHO: bool = False
    DATABASE_CONNECT_ARGS: dict = {}
    DATABASE_POOL_SIZE: int = 10
    DATABASE_POOL_RECYCLE: int = 3600
    DATABASE_POOL_TIMEOUT: int = 30
    DATABASE_POOL_PRE_PING: bool = True

    # API
    API_HOST: str = "127.0.0.1"
    API_PORT: int = 8000
    API_RELOAD: bool = True
    API_LOG_LEVEL: str = "info"

    # Encriptado
    SECRET_KEY: str
    SECURITY_PASSWORD_SALT: str
    JWT_SECRET_KEY: str
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int
    REFRESH_TOKEN_EXPIRE_MINUTES: int

    # Mail
    MAIL_HOST: str = "smtp.google.com"
    MAIL_PORT: int = 587
    MAIL_USERNAME: str = "gabrielbaute@gmail.com"
    MAIL_PASSWORD: str = "your-email-password"
    MAIL_USE_TLS: bool = True
    MAIL_USE_SSL: bool = False
    MAIL_TEMPLATES_DIR: Path = UI_PATH / "emails"

    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8")

    def ensure_dirs(self) -> None:
            """Crea la estructura de directorios necesaria para self-hosting."""
            dirs = [
                self.BASE_PATH, self.DATA_PATH, self.LOGS_PATH, 
                self.CONFIG_PATH, self.TMP_PATH, self.INSTANCE_PATH,
                self.STORAGE_BASE_PATH
            ]
            for directory in dirs:
                try:
                    directory.mkdir(parents=True, exist_ok=True)
                except OSError as e:
                    # Aquí podrías lanzar un error semántico si no hay permisos de escritura
                    print(f" ERROR CRÍTICO: No se pudo crear el directorio {directory}. revise permisos.")
                    sys.exit(1)

def load_settings() -> Settings:
    """
    Instancia la configuración capturando errores de validación para
    presentar mensajes amigables al usuario.
    """
    try:
        instance = Settings()
        instance.ensure_dirs()
        return instance
    except ValidationError as e:
        missing_vars = [str(err["loc"][0]) for err in e.errors() if err["type"] == "missing"]
        
        message = (
            "\n" + "="*60 + "\n"
            " ERROR DE CONFIGURACIÓN EN OCTOPUS PHOTOS\n"
            "="*60 + "\n"
            "Faltan variables de entorno obligatorias en tu archivo .env o sistema:\n"
            f"  {', '.join(missing_vars)}\n\n"
            "Por favor, revisa el archivo '.env.example' y asegúrate de configurar\n"
            "estas llaves para que el servicio pueda iniciar.\n"
            "="*60
        )
        # Lanzamos nuestro error personalizado o salimos elegantemente
        print(message)
        sys.exit(1)

settings = load_settings()
