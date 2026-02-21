"""
Módulo de rutas para la gestión de fotografías.
"""
from uuid import UUID
from typing import Optional
from fastapi import APIRouter, Depends, UploadFile, File, Form, status, HTTPException

from app.services.photos_service import PhotoService
from app.api.dependencies import get_current_user, get_photos_service
from app.errors import OctopusError, PermissionDeniedError, ResourceNotFoundError
from app.schemas import PhotoResponse, PhotoResponseList, PhotoUpdate, UserResponse

router = APIRouter(prefix="/photos", tags=["Photos"])

@router.post("/upload", response_model=PhotoResponse, status_code=status.HTTP_201_CREATED)
async def upload_photo(
    file: UploadFile = File(...),
    description: Optional[str] = Form(None),
    tags: Optional[str] = Form(None), 
    current_user: UserResponse = Depends(get_current_user),
    photo_service: PhotoService = Depends(get_photos_service)
):
    """Sube una foto, extrae EXIF y genera miniatura."""
    try:
        # Convertimos tags de "tag1, tag2" a ["tag1", "tag2"]
        tag_list = [t.strip() for t in tags.split(",")] if tags else []
        
        return photo_service.upload_photo(
            user_id=current_user.id,
            file_stream=file.file,
            filename=file.filename,
            description=description,
            tags=tag_list
        )
    except OctopusError as e:
        raise HTTPException(status_code=400, detail=e.message)

@router.get("/", response_model=PhotoResponseList)
async def list_photos(
    skip: int = 0,
    limit: int = 100,
    current_user: UserResponse = Depends(get_current_user),
    photo_service: PhotoService = Depends(get_photos_service)
):
    """Lista la galería del usuario con paginación."""
    return photo_service.get_user_photos(current_user.id, skip, limit)

@router.get("/{photo_id}", response_model=PhotoResponse)
async def get_photo(
    photo_id: UUID,
    current_user: UserResponse = Depends(get_current_user),
    photo_service: PhotoService = Depends(get_photos_service)
):
    """Obtiene metadatos de una foto específica."""
    photo = photo_service.get_photo_by_id(photo_id)
    if not photo or (photo.user_id != current_user.id and not current_user.is_admin):
        raise HTTPException(status_code=404, detail="Foto no encontrada")
    return photo

@router.patch("/{photo_id}", response_model=PhotoResponse)
async def update_photo(
    photo_id: UUID,
    photo_update: PhotoUpdate,
    current_user: UserResponse = Depends(get_current_user),
    photo_service: PhotoService = Depends(get_photos_service)
):
    """Actualiza descripción o tags de una foto."""
    try:
        # Aquí podrías añadir una validación de propiedad antes de llamar al service
        # o dejar que el service lo maneje si le pasas el requester_id
        return photo_service.update_photo_metadata(photo_id, photo_update)
    except OctopusError as e:
        raise HTTPException(status_code=400, detail=e.message)

@router.delete("/{photo_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_photo(
    photo_id: UUID,
    current_user: UserResponse = Depends(get_current_user),
    photo_service: PhotoService = Depends(get_photos_service)
):
    """Elimina permanentemente la foto del disco y la base de datos."""
    try:
        photo_service.delete_photo(photo_id, current_user.id)
        return None
    except PermissionDeniedError as e:
        raise HTTPException(status_code=403, detail=e.message)
    except ResourceNotFoundError as e:
        raise HTTPException(status_code=404, detail=e.message)
    except OctopusError as e:
        raise HTTPException(status_code=500, detail=e.message)