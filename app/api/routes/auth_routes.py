"""
Módulo para definir las rutas de autenticación de la API.
"""
from fastapi import APIRouter, HTTPException, status, Depends
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy.orm import Session

from app.api.dependencies import get_mail_service, get_user_service
from app.services.security_service import SecurityService
from app.services.users_service import UserService
from app.services.mail_service import MailService
from app.schemas import UserLogin, UserCreate, UserResponse, TokenData
from app.schemas.auth_schemas import Token, PasswordResetConfirm # Asumiendo que están aquí
from app.errors import OctopusError, ResourceNotFoundError

router = APIRouter(prefix="/auth", tags=["Authentication"])

@router.post("/login", response_model=Token)
def login_for_access_token(
    form_data: OAuth2PasswordRequestForm = Depends(),
    user_service: UserService = Depends(get_user_service)
):
    """
    Endpoint estándar de OAuth2 para obtener un token de acceso.
    """
    login_credentials = UserLogin(
        email=form_data.username, 
        password=form_data.password
    )
    
    # El servicio ya maneja la lógica de hash y verificación
    user = user_service.authenticate_user(login_credentials)
    
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Credenciales inválidas",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    if not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="La cuenta de usuario no está activa",
        )
    
    # Generamos el token de acceso
    security = SecurityService()
    access_token = security.create_access_token(
        data={"sub": str(user.id), "scope": "access"}
    )
    
    return {
        "access_token": access_token,
        "token_type": "bearer"
    }

@router.post("/register", response_model=UserResponse, status_code=status.HTTP_201_CREATED)
def register_user(
    user_in: UserCreate,
    user_service: UserService = Depends(get_user_service)
):
    """
    Registro público de nuevos usuarios. 
    Se encarga de crear el registro en DB y la estructura de carpetas física.
    """
    try:
        user = user_service.register_user(user_in)
        return user
    except OctopusError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=e.message
        )

@router.post("/password-recovery", status_code=status.HTTP_200_OK)
def request_recovery(
    email: str,
    user_service: UserService = Depends(get_user_service),
    mail_service: MailService = Depends(get_mail_service)
):
    """
    Solicita un link de recuperación. No revela si el email existe por seguridad.
    """
    try:
        user_service.request_password_recovery(email, mail_service)
    except ResourceNotFoundError:
        # No hacemos nada, devolvemos 200 para evitar enumeración de usuarios
        pass
    except OctopusError as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Error al procesar la solicitud de recuperación"
        )
        
    return {"message": "Si el email está registrado, recibirás un enlace de recuperación."}

@router.post("/reset-password", status_code=status.HTTP_200_OK)
def reset_password(
    data: PasswordResetConfirm,
    user_service: UserService = Depends(get_user_service)
):
    """
    Cambia la contraseña usando un token de scope 'password_reset'.
    """
    security = SecurityService()
    
    try:
        # 1. Validamos el token específico para reset
        token_data = security.decode_token(data.token, expected_scope="password_reset")
        
        # 2. Hasheamos la nueva password
        hashed_password = security.get_password_hash(data.new_password)
        
        # 3. Actualizamos
        success = user_service.user_controller.update_user_password(
            token_data.user_id, 
            hashed_password
        )
        
        if not success:
            raise OctopusError("No se pudo actualizar la contraseña.")
            
    except OctopusError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=e.message
        )
        
    return {"message": "Contraseña actualizada correctamente."}