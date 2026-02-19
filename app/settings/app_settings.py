from pathlib import Path
from pydantic_settings import BaseSettings, SettingsConfigDict

from app.settings.version import __version__


class Settings(BaseSettings):
    # Datos base
    APP_NAME: str = "OctopusPhotos"
    APP_VERSION: str = __version__

    # Directorios
    BASE_PATH: Path = Path.home() / f".{APP_NAME}"
    DATA_PATH: Path = BASE_PATH / "data"
    LOGS_PATH: Path = DATA_PATH / "logs"
    CONFIG_PATH: Path = BASE_PATH / "config"
    TMP_PATH: Path = DATA_PATH / "tmp"
    STORAGE_BASE_PATH: Path = DATA_PATH / "storage"

    # Database
    DATABASE_URL: str = f"sqlite:///{APP_NAME}.db"
    INSTANCE_PATH: Path = BASE_PATH / "instance"
    DATABASE_ECHO: bool = False
    DATABASE_CONNECT_ARGS: dict = {}

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

    @staticmethod
    def ensure_dirs() -> None:
        dirs = [
            Settings.DATA_PATH,
            Settings.LOGS_PATH,
            Settings.CONFIG_PATH,
            Settings.TMP_PATH,
            Settings.INSTANCE_PATH
        ]
        
        try:
            Settings.BASE_PATH.mkdir(parents=True, exist_ok=True)
            for dir in dirs:
                dir.mkdir(parents=True, exist_ok=True)
        except FileExistsError:
            pass


    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8")

settings = Settings()