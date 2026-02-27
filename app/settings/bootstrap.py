import sys
import secrets
import logging
from app.utils.get_environment_path import get_env_paths

logger = logging.getLogger("Bootstrap")


def bootstrap_config() -> None:
    """
    Prepara el entorno, directorios y variables mínimas para el primer arranque.
    """
    # Usamos la primera ruta de la tupla (la del usuario) para el bootstrap
    env_paths = get_env_paths()
    user_env = env_paths[0] 
    
    # Si el archivo ya existe, no hacemos nada, dejamos que Pydantic cargue
    if user_env.exists():
        return

    print(f"--- PRIMER ARRANQUE: Configurando entorno en {user_env.parent} ---")

    # 1. Crear directorios (Config, Data, etc.)
    user_env.parent.mkdir(parents=True, exist_ok=True)

    # 2. Generar secretos automáticamente
    # Generamos hexadecimales seguros: 32 bytes -> 64 caracteres
    secret_key = secrets.token_hex(32)
    jwt_key = secrets.token_hex(32)
    salt = secrets.token_hex(16)

    # 3. Contenido inicial del .env
    # Nota: Aquí puedes poner los valores por defecto que el usuario podría querer cambiar
    default_env_content = f"""# OCTOPUS PHOTOS - AUTO-GENERATED CONFIG
APP_NAME=OctopusPhotos
API_HOST=0.0.0.0
API_PORT=8082

# Seguridad (Generados automáticamente)
SECRET_KEY={secret_key}
JWT_SECRET_KEY={jwt_key}
SECURITY_PASSWORD_SALT={salt}
ALGORITHM=HS256

# Tiempos de expiración
ACCESS_TOKEN_EXPIRE_MINUTES=60
REFRESH_TOKEN_EXPIRE_MINUTES=10080

# Configuración d correo (coloca tus credenciales)
MAIL_HOST=smtp.google.com
MAIL_PORT=587
MAIL_USERNAME=yourmail@gmail.com
MAIL_PASSWORD=your-app-specific-password
MAIL_USE_TLS=True
MAIL_USE_SSL=False
"""
    
    try:
        user_env.write_text(default_env_content, encoding="utf-8")
        logger.info("--- Configuración inicial creada con éxito ---")
    except Exception as e:
        print(f"Error crítico al escribir la configuración: {e}")
        sys.exit(1)