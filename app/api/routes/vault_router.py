"""
Endpoints para la gestión del Baúl Seguro (Vault).
"""
from fastapi import APIRouter, Depends, Header, Form, Path
from fastapi.responses import StreamingResponse
from sqlalchemy.orm import Session
from uuid import UUID

from app.services.vault_service import VaultService
from app.schemas.user_schemas import UserResponse # Asumiendo tu esquema de usuario
from app.api.dependencies import get_current_user, get_vault_service, get_vault_password

router = APIRouter(prefix="/vault", tags=["Vault"])

@router.post("/lock/{photo_id}")
async def lock_photo(
    photo_id: UUID = Path(...),
    vault_password: str = Form(...), # Recibimos la clave por Form para mayor seguridad en el POST
    current_user: UserResponse = Depends(get_current_user),
    vault_service: VaultService = Depends(get_vault_service)
):
    """
    Mueve una foto existente al baúl cifrado.
    """
    success = vault_service.lock_photo(photo_id, current_user.id, vault_password)
    return {"status": "success", "message": "Fotografía asegurada en el baúl."}

@router.get("/view/{photo_id}")
async def get_vault_photo(
    photo_id: UUID,
    vault_password: str = Depends(get_vault_password),
    current_user: UserResponse = Depends(get_current_user),
    vault_service: VaultService = Depends(get_vault_service)
):
    """
    Obtiene la foto original del baúl.
    """
    stream = vault_service.get_decrypted_stream(
        photo_id, current_user.id, vault_password, is_thumbnail=False
    )
    return StreamingResponse(stream, media_type="image/jpeg")

@router.get("/view/{photo_id}/thumbnail")
async def get_vault_thumbnail(
    photo_id: UUID,
    vault_password: str = Depends(get_vault_password),
    current_user: UserResponse = Depends(get_current_user),
    vault_service: VaultService = Depends(get_vault_service)
):
    """
    Obtiene la miniatura cifrada del baúl.
    """
    stream = vault_service.get_decrypted_stream(
        photo_id, current_user.id, vault_password, is_thumbnail=True
    )
    return StreamingResponse(stream, media_type="image/jpeg")