"""
Módulo de rutas para la gestión de usuarios (Autogestión).
"""
from fastapi import APIRouter, Depends, HTTPException, status
from app.api.dependencies import get_current_user, get_user_service
from app.schemas import UserResponse, UserUpdate, PasswordChange
from app.services.users_service import UserService
from app.services.security_service import SecurityService
from app.errors import OctopusError

router = APIRouter(prefix="/users", tags=["Users"])

@router.get("/me", response_model=UserResponse)
def get_my_profile(current_user: UserResponse = Depends(get_current_user)):
    """Retorna el perfil del usuario autenticado."""
    return current_user

@router.patch("/me", response_model=UserResponse)
def update_my_profile(
    user_update: UserUpdate,
    current_user: UserResponse = Depends(get_current_user),
    user_service: UserService = Depends(get_user_service)
):
    """Actualiza datos básicos del perfil (email, username)."""
    try:
        updated_user = user_service.user_controller.update_user(current_user.id, user_update)
        return updated_user
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

@router.post("/me/change-password", status_code=status.HTTP_200_OK)
def change_password(
    data: PasswordChange,
    current_user: UserResponse = Depends(get_current_user),
    user_service: UserService = Depends(get_user_service)
):
    """
    Cambia la contraseña del usuario validando la anterior.
    """
    # 1. Verificar la contraseña actual
    # Necesitamos el hash de la DB (el esquema UserResponse no lo trae por seguridad)
    user_db = user_service.user_controller._get_item_by_id(
        user_service.user_controller.model_class, current_user.id
    )
    
    security = SecurityService()
    if not security.verify_password(data.current_password, user_db.password_hash):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="La contraseña actual es incorrecta"
        )
    
    # 2. Actualizar a la nueva
    new_hash = security.get_password_hash(data.new_password)
    success = user_service.user_controller.update_user_password(current_user.id, new_hash)
    
    if not success:
        raise HTTPException(status_code=500, detail="No se pudo actualizar la contraseña")
        
    return {"message": "Contraseña actualizada exitosamente"}

@router.post("/me/deactivate", status_code=status.HTTP_200_OK)
def deactivate_my_account(
    current_user: UserResponse = Depends(get_current_user),
    user_service: UserService = Depends(get_user_service)
):
    """
    Desactiva la cuenta del usuario (is_active = False).
    El usuario perderá el acceso inmediatamente.
    """
    try:
        user_service.deactivate_user(current_user.id)
        return {"message": "Cuenta desactivada correctamente. Lamentamos verte partir."}
    except OctopusError as e:
        raise HTTPException(status_code=400, detail=e.message)