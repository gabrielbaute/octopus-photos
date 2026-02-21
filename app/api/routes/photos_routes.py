"""
Módulo de rutas para la gestión de fotografías.
"""
from uuid import UUID
from pathlib import Path
from typing import Optional, List
from fastapi.responses import FileResponse
from fastapi import APIRouter, status, HTTPException, UploadFile, Depends, File, Form

from app.services.photos_service import PhotoService
from app.api.dependencies import get_current_user, get_photos_service
from app.errors import OctopusError, PermissionDeniedError, ResourceNotFoundError
from app.schemas import PhotoResponse, PhotoResponseList, PhotoUpdate, UserResponse

router = APIRouter(prefix="/photos", tags=["Photos"])

# =========== RUTA DE SUBIDA ===========

@router.post("/upload", response_model=PhotoResponse, status_code=status.HTTP_201_CREATED)
async def upload_photo(
    file: UploadFile = File(...),
    description: Optional[str] = Form(None),
    tags: Optional[List[str]] = Form(None), 
    current_user: UserResponse = Depends(get_current_user),
    photo_service: PhotoService = Depends(get_photos_service)
):
    try:
        # Procesamiento inteligente de tags
        final_tags = []
        if tags:
            # Si v0 envía ["tag1", "tag2"], 'tags' ya es una lista.
            # Si envía ["tag1, tag2"], lo aplanamos.
            for t in tags:
                final_tags.extend([item.strip() for item in t.split(",") if item.strip()])

        # Leemos el contenido para asegurarnos de que el stream esté disponible
        contents = await file.read()
        import io
        file_stream = io.BytesIO(contents)

        photo = photo_service.upload_photo(
            user_id=current_user.id,
            file_stream=file_stream,
            filename=file.filename,
            description=description,
            tags=final_tags
        )
        
        return photo

    except OctopusError as e:
        raise HTTPException(status_code=400, detail=e.message)
    except Exception as e:
        # LOGGING CRÍTICO: Para saber qué falló realmente en el 500
        import logging
        logging.error(f"Error en upload: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail="Error interno al procesar la imagen.")

# =========== RUTAS DE CONSULTA ===========

@router.get("/me", response_model=PhotoResponseList)
async def get_my_photos(
    skip: int = 0,
    limit: int = 100,
    include_deleted: bool = False, # Nuevo parámetro para ver la papelera
    current_user: UserResponse = Depends(get_current_user),
    photo_service: PhotoService = Depends(get_photos_service)
):
    """Lista la galería. Por defecto oculta lo que esté en la papelera."""
    return photo_service.get_user_photos(
        current_user.id, 
        skip=skip, 
        limit=limit, 
        include_deleted=include_deleted
    )

@router.get("/{photo_id}", response_model=PhotoResponse)
async def get_photo(
    photo_id: UUID,
    current_user: UserResponse = Depends(get_current_user),
    photo_service: PhotoService = Depends(get_photos_service)
):
    """Obtiene metadatos de una foto específica (incluyendo eliminadas)."""
    try:
        photo = photo_service.get_photo_by_id(photo_id, current_user.id)
        return photo
    except PermissionDeniedError as e:
        raise HTTPException(status_code=403, detail=e.message)
    except ResourceNotFoundError as e:
        raise HTTPException(status_code=404, detail=e.message)

# =========== SERVICIO DE BINARIOS (DOWNLOAD/THUMBNAIL) ===========

@router.get("/{photo_id}/download")
async def download_photo_file(
    photo_id: UUID,
    current_user: UserResponse = Depends(get_current_user),
    photo_service: PhotoService = Depends(get_photos_service)
):
    """
    Sirve el archivo original. 
    Permite descarga incluso si está en 'is_deleted' (para que el usuario la vea en la papelera).
    """
    try:
        # 1. Validar propiedad y existencia mediante el Service
        photo = photo_service.get_photo_by_id(photo_id, current_user.id)
        
        # 2. Verificar existencia física
        file_path = Path(photo.storage_path)
        if not file_path.exists():
            raise HTTPException(status_code=404, detail="Archivo físico no encontrado en el servidor")

        return FileResponse(
            path=file_path,
            filename=photo.file_name,
            media_type="image/jpeg" # O detectar dinámicamente según extensión
        )
    except PermissionDeniedError as e:
        raise HTTPException(status_code=403, detail=e.message)
    except ResourceNotFoundError as e:
        raise HTTPException(status_code=404, detail=e.message)

@router.get("/{photo_id}/thumbnail")
async def get_photo_thumbnail(
    photo_id: UUID,
    current_user: UserResponse = Depends(get_current_user),
    photo_service: PhotoService = Depends(get_photos_service)
):
    """Sirve la miniatura optimizada para previsualización."""
    try:
        # Validar propiedad
        photo = photo_service.get_photo_by_id(photo_id, current_user.id)
        
        # Obtener ruta de miniatura desde el storage_service
        thumb_dir = photo_service.storage_service.get_user_thubnail_path(photo.user_id)
        thumb_path = Path(thumb_dir) / Path(photo.storage_path).name
        
        if not thumb_path.exists():
            # Si no existe, podríamos intentar regenerarla on-the-fly o devolver error
            raise HTTPException(status_code=404, detail="Miniatura no disponible")

        return FileResponse(path=thumb_path, media_type="image/jpeg")
    except (PermissionDeniedError, ResourceNotFoundError) as e:
        raise HTTPException(status_code=404, detail="Recurso no encontrado")

# =========== RUTAS DE ACCIÓN (SOFT DELETE / RESTORE) ===========

@router.post("/{photo_id}/trash", status_code=status.HTTP_200_OK)
async def move_to_trash(
    photo_id: UUID,
    current_user: UserResponse = Depends(get_current_user),
    photo_service: PhotoService = Depends(get_photos_service)
):
    """Mueve una foto a la papelera (Soft Delete)."""
    try:
        success = photo_service.trash_photo(photo_id, current_user.id)
        return {"message": "Foto movida a la papelera", "id": photo_id}
    except PermissionDeniedError as e:
        raise HTTPException(status_code=403, detail=e.message)
    except ResourceNotFoundError as e:
        raise HTTPException(status_code=404, detail=e.message)

@router.post("/{photo_id}/restore", status_code=status.HTTP_200_OK)
async def restore_photo(
    photo_id: UUID,
    current_user: UserResponse = Depends(get_current_user),
    photo_service: PhotoService = Depends(get_photos_service)
):
    """Restaura una foto de la papelera."""
    try:
        # Nota: Debes implementar restore_photo en PhotoService llamando al controller
        success = photo_service.restore_photo(photo_id, current_user.id)
        return {"message": "Foto restaurada exitosamente", "id": photo_id}
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

# =========== RUTAS DE ELIMINACIÓN PERMANENTE ===========

@router.delete("/{photo_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_photo_permanently(
    photo_id: UUID,
    current_user: UserResponse = Depends(get_current_user),
    photo_service: PhotoService = Depends(get_photos_service)
):
    """
    BORRADO FÍSICO: Elimina permanentemente de DB y Disco.
    Inapelable. No se puede recuperar.
    """
    try:
        photo_service.delete_photo_permanently(photo_id, current_user.id)
        return None
    except PermissionDeniedError as e:
        raise HTTPException(status_code=403, detail=e.message)
    except ResourceNotFoundError as e:
        raise HTTPException(status_code=404, detail=e.message)
    except OctopusError as e:
        raise HTTPException(status_code=500, detail=e.message)

# =========== RUTAS DE EDICIÓN ===========

@router.patch("/{photo_id}", response_model=PhotoResponse)
async def update_photo_metadata(
    photo_id: UUID,
    photo_update: PhotoUpdate,
    current_user: UserResponse = Depends(get_current_user),
    photo_service: PhotoService = Depends(get_photos_service)
):
    """
    Actualiza la descripción o los tags de una fotografía.
    Solo el propietario o un ADMIN pueden realizar esta acción.
    """
    try:
        # El servicio debe internamente usar _validate_ownership
        updated_photo = photo_service.update_photo_metadata(
            photo_id=photo_id, 
            update_data=photo_update, 
            requester_id=current_user.id
        )
        return updated_photo

    except (ResourceNotFoundError, PermissionDeniedError) as e:
        # Mapeo directo de tus excepciones personalizadas a códigos HTTP
        status_code = 404 if isinstance(e, ResourceNotFoundError) else 403
        raise HTTPException(status_code=status_code, detail=e.message)
    except OctopusError as e:
        raise HTTPException(status_code=400, detail=e.message)