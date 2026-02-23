"""
Dependencias para inyectar en la API
"""
from typing import Optional
from sqlalchemy.orm import Session
from fastapi.security import OAuth2PasswordBearer
from fastapi import HTTPException, status, Query, Depends

from app.enums import UserRole
from app.errors import OctopusError
from app.database.db_session import get_db
from app.settings import settings, Settings
from app.mail import SMTPClient, MailBuilder
from app.schemas import UserResponse, TokenData
from app.services.mail_service import MailService
from app.services.users_service import UserService
from app.services.photos_service import PhotoService
from app.services.albums_service import AlbumService
from app.services.storage_service import StorageService
from app.services.memories_service import MemoriesService
from app.services.security_service import SecurityService

# OAuth2 scheme
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/v1/auth/login", auto_error=False)

# ============ Proveedores de Servicios ============
def get_settings_instance() -> Settings:
    """Provee una instancia de Settings."""
    return settings

def get_mail_service() -> MailService:
    """Provee MailService usando las rutas definidas en settings."""
    client = SMTPClient(settings=settings)
    builder = MailBuilder(template_dir=settings.MAIL_TEMPLATES_DIR)
    return MailService(client, builder, settings)

def get_user_service(db: Session = Depends(get_db)) -> UserService:
    """
    Provee una instancia de UserService con la sesión de DB inyectada.

    Args:
        db (Session): Sesión de la base de datos.

    Returns:
        UserService: Instancia de UserService.
    """
    return UserService(db)

def get_storage_service(db: Session = Depends(get_db)) -> StorageService:
    """
    Provee StorageService.
    
    Args:
        db (Session): Sesión de la base de datos.
    
    Returns:
        StorageService: Instancia de StorageService.
    """
    return StorageService(db)

def get_photos_service(db: Session = Depends(get_db)) -> PhotoService:
    """
    Provee PhotoService.

    Args:
        db (Session): Sesión de la base de datos.
        
    Returns:
        PhotoService: Instancia de PhotoService.
    """
    return PhotoService(db)

def get_albums_service(db: Session = Depends(get_db)) -> AlbumService:
    """
    Provee AlbumService.

    Args:
        db (Session): Sesión de la base de datos.
        
    Returns:
        AlbumService: Instancia de AlbumService.
    """
    return AlbumService(db)

def get_memories_service(db: Session = Depends(get_db)) -> MemoriesService:
    """
    Provee MemoriesService.

    Args:
        db (Session): Sesión de la base de datos.
        
    Returns:
        MemoriesService: Instancia de MemoriesService.
    """
    return MemoriesService(settings, db)

# ============ Dependencias de Seguridad y Usuario ============

def get_current_user(
    token_header: Optional[str] = Depends(oauth2_scheme),
    token_query: Optional[str] = Query(None, alias="token"),
    user_service: UserService = Depends(get_user_service)
) -> UserResponse:
    """
    Valida el token JWT (extraído de Header o Query Param) y retorna el usuario actual.

    Esta implementación permite que recursos multimedia (como <img>) puedan
    autenticarse pasando el token en la URL, manteniendo la compatibilidad 
    con el estándar OAuth2 para el resto de la API.

    Args:
        token_header (Optional[str]): Token extraído del header Authorization.
        token_query (Optional[str]): Token extraído del parámetro de consulta 'token'.
        user_service (UserService): Servicio para la gestión de la entidad de usuario.

    Returns:
        UserResponse: Objeto del usuario autenticado y activo.

    Raises:
        HTTPException: 401 si el token no existe o es inválido, 
                        403 si el usuario está desactivado.
    """
    # 1. Priorizar el header, pero caer al query param si es necesario
    token = token_header or token_query
    
    if not token:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="No se proporcionaron credenciales de autenticación",
            headers={"WWW-Authenticate": "Bearer"},
        )

    try:
        # 2. Decodificar el token usando el SecurityService
        security_service = SecurityService()
        token_data: TokenData = security_service.decode_token(
            token, 
            expected_scope="access"
        )
        
        # 3. Recuperar usuario desde la base de datos
        user = user_service.user_controller.get_by_id(token_data.user_id)
        
        if user is None:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Credenciales no válidas o usuario inexistente",
            )
            
        if not user.is_active:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="La cuenta de usuario está desactivada",
            )
            
        return user

    except OctopusError as e:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=e.message,
            headers={"WWW-Authenticate": "Bearer"},
        )

def get_current_admin(
    current_user: UserResponse = Depends(get_current_user)
) -> UserResponse:
    """
    Asegura que el usuario tenga privilegios de administrador.

    Args:
        current_user (UserResponse): Usuario actual.
    
    Returns:
        UserResponse: Usuario actual.
    
    Raises:
        HTTPException: Si el usuario no tiene privilegios de administrador.
    """
    if current_user.role != UserRole.ADMIN:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Operación restringida a administradores",
        )
    return current_user