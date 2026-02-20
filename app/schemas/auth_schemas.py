from typing import Optional
from pydantic import BaseModel, ConfigDict, Field, EmailStr

class Token(BaseModel):
    """
    Esquema para el token.

    Args:
        access_token (str): Token de acceso.
        token_type (str): Tipo de token
    """
    access_token: str
    token_type: str

    model_config = ConfigDict(
        json_schema_extra={
            "examples": [
                {
                    "access_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
                    "token_type": "bearer"
                }
            ]
        }
    )


class TokenData(BaseModel):
    """
    Esquema para datos del token.

    Args:
        user_id (Optional[str]): ID del usuario asociado con el token.
    """
    user_id: Optional[str] = None

    model_config = ConfigDict(
        json_schema_extra={
            "examples": [
                {
                    "user_id": "xxxx-xxxx-xxxx-xxxx"
                }
            ]
        }
    )

class PasswordResetConfirm(BaseModel):
    """
    Esquema para confirmación de cambio de contraseña.

    Args:
        token (str): Token JWT para cambio de contraseña.
        new_password (str): Nueva contraseña.
    """
    token: str
    new_password: str = Field(..., min_length=8)

    model_config = ConfigDict(
        json_schema_extra={
            "examples": [
                {
                    "token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
                    "new_password": "new_password"
                }
            ]
        }
    
    )

class UserLogin(BaseModel):
    """
    Esquema para el endpoint de autenticación.
    
    Args:
        email (EmailStr): Dirección de correo electrónico.
        password (str): Contraseña.
    """
    email: EmailStr
    password: str

class PasswordChange(BaseModel):
    """
    Esquema para el cambio de contraseña.

    Args:
        current_password (str): Contraseña actual.
        new_password (str): Nueva contraseña.
    """
    current_password: str
    new_password: str = Field(..., min_length=8)