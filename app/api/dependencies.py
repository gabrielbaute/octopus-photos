"""
Dependencias para inyectar en la API
"""
from typing import Generator
from sqlalchemy.orm import Session
from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer

from app.enums import UserRole
from app.errors import OctopusError
from app.database.db_session import get_db
from app.settings import settings, Settings
from app.mail import SMTPClient, MailBuilder
from app.schemas import UserResponse, TokenData
from app.services.mail_service import MailService
from app.services.users_service import UserService
from app.services.photos_service import PhotosService
from app.services.storage_service import StorageService
from app.services.security_service import SecurityService


# OAuth2 scheme
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/v1/auth/login")

# --- Proveedores de Servicios ---

def get_settings_instance() -> Settings:
    """Provee una instancia de Settings."""
    return settings

def get_mail_service() -> MailService:
    """Provee MailService usando las rutas definidas en settings."""
    client = SMTPClient(settings=settings)
    builder = MailBuilder(template_dir=settings.MAIL_TEMPLATES_DIR)
    return MailService(client, builder, settings)

def get_user_service(db: Session = Depends(get_db)) -> UserService:
    """Provee una instancia de UserService con la sesión de DB inyectada."""
    return UserService(db)

def get_storage_service(db: Session = Depends(get_db)) -> StorageService:
    """Provee StorageService."""
    return StorageService(db)

def get_photos_service(db: Session = Depends(get_db)) -> PhotosService:
    """Provee PhotosService."""
    return PhotosService(db)

# --- Dependencias de Seguridad y Usuario ---

def get_current_user(
    token: str = Depends(oauth2_scheme), 
    user_service: UserService = Depends(get_user_service)
) -> UserResponse:
    """
    Valida el token JWT y retorna el usuario actual.

    Args:
        token (str): Token JWT.
        user_service (UserService): servicio de usuario para getionar la entidad de usuario.
    
    Returns:
        UserResponse: Usuario actual.
    
    Raises:
        HTTPException: Si el token no es válido o el usuario no existe.
    """
    try:
        # 1. Decodificar el token
        security_service = SecurityService()
        token_data: TokenData = security_service.decode_token(token, expected_scope="access")
        
        # 2. Buscar usuario (usamos el servicio inyectado)
        user = user_service.user_controller.get_by_id(token_data.user_id)
        
        if user is None:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Credenciales de usuario no válidas o usuario inexistente",
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