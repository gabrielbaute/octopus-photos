"""
Módulo de rutas para la gestión de álbumes.
"""
from uuid import UUID
from fastapi import APIRouter, status, HTTPException, Depends

from app.errors import OctopusError, PermissionDeniedError, ResourceNotFoundError
from app.services.albums_service import AlbumService
from app.api.dependencies import get_current_user, get_albums_service
from app.schemas import (
    AlbumResponse, 
    AlbumListResponse, 
    AlbumCreate, 
    AlbumUpdate, 
    UserResponse,
    PhotoBulkAction
)

router = APIRouter(prefix="/albums", tags=["Albums"])

# --- OPERACIONES DE COLECCIÓN ---

@router.post("/", response_model=AlbumResponse, status_code=status.HTTP_201_CREATED)
async def create_album(
    album_create: AlbumCreate,
    current_user: UserResponse = Depends(get_current_user),
    album_service: AlbumService = Depends(get_albums_service)
):
    """Crea un nuevo álbum y opcionalmente le asigna fotos iniciales."""
    try:
        return album_service.create_album(album_create)
    except OctopusError as e:
        raise HTTPException(status_code=400, detail=e.message)

@router.get("/", response_model=AlbumListResponse)
async def get_albums(
    current_user: UserResponse = Depends(get_current_user),
    album_service: AlbumService = Depends(get_albums_service)
):
    """Lista todos los álbumes del usuario actual."""
    return album_service.get_user_albums(current_user.id)


# --- OPERACIONES DE RECURSO INDIVIDUAL ---

@router.get("/{album_id}", response_model=AlbumResponse)
async def get_album_detail(
    album_id: UUID,
    current_user: UserResponse = Depends(get_current_user),
    album_service: AlbumService = Depends(get_albums_service)
):
    """Obtiene el detalle de un álbum (incluyendo su lista de fotos)."""
    try:
        return album_service.get_album_by_id(album_id, current_user.id)
    except PermissionDeniedError as e:
        raise HTTPException(status_code=403, detail=e.message)
    except ResourceNotFoundError as e:
        raise HTTPException(status_code=404, detail=e.message)

@router.patch("/{album_id}", response_model=AlbumResponse)
async def update_album(
    album_id: UUID,
    album_update: AlbumUpdate,
    current_user: UserResponse = Depends(get_current_user),
    album_service: AlbumService = Depends(get_albums_service)
):
    """Actualiza nombre o descripción de un álbum."""
    try:
        return album_service.update_album_metadata(album_id, album_update, current_user.id)
    except (PermissionDeniedError, ResourceNotFoundError) as e:
        status_code = 403 if isinstance(e, PermissionDeniedError) else 404
        raise HTTPException(status_code=status_code, detail=e.message)

@router.delete("/{album_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_album(
    album_id: UUID,
    current_user: UserResponse = Depends(get_current_user),
    album_service: AlbumService = Depends(get_albums_service)
):
    """Elimina un álbum. Las fotos contenidas NO se eliminan del sistema."""
    try:
        album_service.delete_album(album_id, current_user.id)
        return None
    except (PermissionDeniedError, ResourceNotFoundError) as e:
        status_code = 403 if isinstance(e, PermissionDeniedError) else 404
        raise HTTPException(status_code=status_code, detail=e.message)


# --- GESTIÓN DE CONTENIDO (RELACIÓN N:N) ---

@router.post("/{album_id}/photos", status_code=status.HTTP_201_CREATED)
async def add_photos_to_album(
    album_id: UUID,
    action: PhotoBulkAction,
    current_user: UserResponse = Depends(get_current_user),
    album_service: AlbumService = Depends(get_albums_service)
):
    """Añade múltiples fotos a un álbum existente."""
    try:
        album_service.add_several_photos_to_album(action.photo_ids, album_id, current_user.id)
        return {"message": f"{len(action.photo_ids)} fotos añadidas correctamente"}
    except (PermissionDeniedError, OctopusError) as e:
        raise HTTPException(status_code=400, detail=e.message)

@router.delete("/{album_id}/photos", status_code=status.HTTP_204_NO_CONTENT)
async def remove_photos_from_album(
    album_id: UUID,
    action: PhotoBulkAction,
    current_user: UserResponse = Depends(get_current_user),
    album_service: AlbumService = Depends(get_albums_service)
):
    """Quita múltiples fotos de un álbum sin eliminarlas del sistema."""
    try:
        album_service.remove_several_photos_from_album(action.photo_ids, album_id, current_user.id)
        return None
    except PermissionDeniedError as e:
        raise HTTPException(status_code=403, detail=e.message)
