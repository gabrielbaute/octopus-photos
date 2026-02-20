from uuid import UUID
from pathlib import Path
from typing import Optional
from datetime import datetime
from pydantic import BaseModel, Field, ConfigDict, EmailStr

from app.enums.user_roles_enum import UserRole
from app.schemas.storage_schemas import UserStorage

class UserBase(BaseModel):
    """
    Atributos compartidos de usuario.

    Args:
        username (str): Nombre de usuario.
        email (EmailStr): Dirección de correo electrónico.
    """
    username: str = Field(..., min_length=3, max_length=50)
    email: EmailStr
    role: UserRole = Field(..., description="Rol del usuario")

class UserCreate(UserBase):
    """
    Esquema para registro: aquí sí pedimos el password plano.
    
    Args:
        username (str): Nombre de usuario.
        email (EmailStr): Dirección de correo electrónico.
        password (str): Contraseña.
    """
    password: str = Field(..., min_length=8)

class UserResponse(UserBase):
    """
    Esquema de respuesta seguro: sin contraseñas.
    
    Args:
        id (UUID): Identificador único.
        username (str): Nombre de usuario.
        email (EmailStr): Dirección de correo electrónico.
        role (UserRole): Rol del usuario.
        created_at (datetime): Fecha de creación.
        is_active (bool): Indica si el usuario está activo.
        storage (Optional[UserStorage]): Ruta del almacenamiento.
    """
    id: UUID
    created_at: datetime
    is_active: bool
    storage: Optional[UserStorage]

    model_config = ConfigDict(from_attributes=True)

class UserListResponse(BaseModel):
    """
    Esquema de respuesta para una lista de usuarios.
    
    Args:
        count (int): Número de usuarios.
        users (List[UserResponse]): Lista de usuarios.
    """
    count: int = Field(..., description="Número de usuarios")
    users: list[UserResponse] = Field(..., description="Lista de usuarios")

    model_config = ConfigDict(from_attributes=True)

class UserUpdate(UserBase):
    """
    Esquema para actualizar usuario
    
    Args:
        username (Optional[str]): Nombre de usuario.
        email (Optional[EmailStr]): Dirección de correo electrónico.
        is_active (Optional[bool]): Indica si el usuario está activo.
    """
    username: Optional[str] = Field(..., min_length=3, max_length=50)
    email: Optional[EmailStr]
    is_active: Optional[bool]

    model_config = ConfigDict(from_attributes=True)

