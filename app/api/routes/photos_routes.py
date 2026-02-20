"""
Módulo de rutas para la gestión de fotografías.
"""
from uuid import UUID
from pathlib import Path
from typing import Optional, List
from fastapi.responses import FileResponse
from fastapi import APIRouter, Depends, UploadFile, File, Form, status, HTTPException

from app.enums import UserRole
from app.errors import OctopusError
from app.services.photos_service import PhotosService
from app.api.dependencies import get_current_user, get_photos_service
from app.schemas import PhotoResponse, PhotoResponseList, PhotoUpdate, UserResponse, PhotoBulkAction

router = APIRouter(prefix="/photos", tags=["Photos"])

@router.post("/upload", response_model=PhotoResponse, status_code=status.HTTP_201_CREATED)
async def upload_photo(
    file: UploadFile = File(...),
    description: Optional[str] = Form(None),
    tags: Optional[str] = Form(None), # Los tags suelen venir como string separado por comas en FormData
    current_user: UserResponse = Depends(get_current_user),
    photo_service: PhotosService = Depends(get_photos_service)
):
    """
    Sube una fotografía al servidor.
    
    Procesa el archivo binario, genera miniaturas, extrae metadatos y 
    actualiza la cuota de almacenamiento del usuario.
    """
    try:
        # Convertimos los tags de string a lista si existen
        tag_list = [tag.strip() for tag in tags.split(",")] if tags else []

        # Ejecutamos la lógica de negocio
        # Pasamos el file.file que es el objeto file-like (BinaryIO) que espera tu servicio
        photo = photo_service.upload_photo(
            user_id=current_user.id,
            file_stream=file.file,
            file_name=file.filename,
            description=description,
            tags=tag_list
        )
        
        return photo

    except OctopusError as e:
        # Capturamos errores de cuota llena, formato inválido, etc.
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=e.message
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error interno al procesar la imagen: {str(e)}"
        )
    
@router.get("/me", response_model=PhotoResponseList)
async def get_my_photos(
    skip: int = 0,
    limit: int = 50,
    current_user: UserResponse = Depends(get_current_user),
    photo_service: PhotosService = Depends(get_photos_service)
):
    """
    Obtiene la colección de fotos del usuario actual de forma paginada.
    
    Args:
        limit (int): Número máximo de fotos a retornar (por defecto 50).
        offset (int): Número de fotos a saltar (para paginación).
    """
    return photo_service.get_user_photos(
            user_id=current_user.id, 
            skip=skip, 
            limit=limit
        )

@router.get("/{photo_id}", response_model=PhotoResponse)
async def get_photo_detail(
    photo_id: UUID,
    current_user: UserResponse = Depends(get_current_user),
    photo_service: PhotosService = Depends(get_photos_service)
):
    """
    Obtiene los metadatos detallados de una fotografía específica.
    
    Verifica que la foto pertenezca al usuario autenticado.
    """
    try:
        # Buscamos la foto en el controlador
        photo = photo_service.get_photo_by_id(photo_id)
        
        if not photo:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Fotografía no encontrada"
            )

        # RIGOR: Verificación de propiedad
        # Un usuario normal solo puede ver sus propias fotos.
        if photo.user_id != current_user.id and current_user.role != UserRole.ADMIN:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="No tienes permiso para acceder a este recurso"
            )

        return photo

    except OctopusError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=e.message
        )

@router.get("/{photo_id}/download")
async def download_photo_file(
    photo_id: UUID,
    current_user: UserResponse = Depends(get_current_user),
    photo_service: PhotosService = Depends(get_photos_service)
):
    """Sirve el archivo original de la fotografía."""
    photo = photo_service.photo_controller.get_by_id(photo_id)
    
    if not photo or (photo.user_id != current_user.id and current_user.role != UserRole.ADMIN):
        raise HTTPException(status_code=404, detail="Recurso no accesible")

    # photo.storage_path contiene la ruta absoluta con el UUID
    return FileResponse(
        path=photo.storage_path, 
        filename=photo.file_name, # El navegador/flutter lo descargará con su nombre original
        media_type="image/jpeg"
    )

@router.get("/{photo_id}/thumbnail")
async def get_photo_thumbnail(
    photo_id: UUID,
    current_user: UserResponse = Depends(get_current_user),
    photo_service: PhotosService = Depends(get_photos_service)
):
    """Sirve la miniatura de la fotografía."""
    photo = photo_service.photo_controller.get_by_id(photo_id)
    
    if not photo or (photo.user_id != current_user.id and current_user.role != UserRole.ADMIN):
        raise HTTPException(status_code=404, detail="Recurso no accesible")

    # Construimos la ruta a la miniatura usando la lógica de StorageService
    # Recuerda que el nombre físico es el mismo (UUID.jpg)
    thumb_dir = photo_service.storage_service.get_user_thubnail_path(photo.user_id)
    thumb_path = Path(thumb_dir) / Path(photo.storage_path).name
    
    if not thumb_path.exists():
        raise HTTPException(status_code=404, detail="Miniatura no generada")

    return FileResponse(path=thumb_path, media_type="image/jpeg")

@router.post("/albums/{album_id}/photos", status_code=status.HTTP_200_OK)
async def add_photos_to_album(
    album_id: UUID,
    action: PhotoBulkAction,
    current_user: UserResponse = Depends(get_current_user),
    photo_service: PhotosService = Depends(get_photos_service)
):
    """
    Asocia múltiples fotos a un álbum de forma masiva.
    
    Verifica que las fotos pertenezcan al usuario antes de asociarlas.
    """
    try:
        # Nota: El service debería internamente validar que el album_id 
        # pertenece a current_user.id para evitar que alguien inyecte fotos 
        # en álbumes ajenos.
        success = photo_service.add_photos_to_album(
            photo_ids=action.photo_ids,
            album_id=album_id,
            requester_id=current_user.id
        )
        
        if not success:
            raise HTTPException(status_code=400, detail="No se pudieron asociar las fotos")
            
        return {"message": f"Se han añadido {len(action.photo_ids)} fotos al álbum"}
        
    except OctopusError as e:
        raise HTTPException(status_code=400, detail=e.message)

@router.patch("/{photo_id}", response_model=PhotoResponse)
async def update_photo_metadata(
    photo_id: UUID,
    photo_update: PhotoUpdate,
    current_user: UserResponse = Depends(get_current_user),
    photo_service: PhotosService = Depends(get_photos_service)
):
    """
    Actualiza la descripción o los tags de una fotografía.
    """
    try:
        # 1. Buscamos la existencia y verificamos propiedad
        photo = photo_service.photo_controller.get_by_id(photo_id)
        
        if not photo:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Foto no encontrada")
            
        if photo.user_id != current_user.id and current_user.role != UserRole.ADMIN:
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="No tienes permiso")

        # 2. Delegamos la actualización al controlador
        updated_photo = photo_service.update_photo_metadata(photo_id, photo_update)
        
        return updated_photo

    except OctopusError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=e.message)

@router.delete("/albums/{album_id}/photos/{photo_id}", status_code=status.HTTP_200_OK)
async def remove_photo_from_album(
    album_id: UUID,
    photo_id: UUID,
    current_user: UserResponse = Depends(get_current_user),
    photo_service: PhotosService = Depends(get_photos_service)
):
    """
    Quita una foto de un álbum sin eliminar el archivo físico.
    """
    try:
        # El controlador que definimos antes devuelve la PhotoResponse
        photo = photo_service.photo_controller.remove_photo_from_album(photo_id, album_id)
        
        # Validamos que el usuario tenga permiso sobre la foto que acaba de "soltar"
        if photo.user_id != current_user.id and current_user.role != UserRole.ADMIN:
             raise HTTPException(status_code=403, detail="No tienes permiso sobre esta galería")
             
        return {"message": "Foto removida del álbum correctamente"}

    except OctopusError as e:
        raise HTTPException(status_code=400, detail=e.message)

@router.delete("/albums/{album_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_album(
    album_id: UUID,
    current_user: UserResponse = Depends(get_current_user),
    photo_service: PhotosService = Depends(get_photos_service)
):
    """
    Elimina un álbum completo. Las fotos no se borran del disco.
    """
    # Aquí es vital validar la propiedad del álbum antes de borrarlo
    # Podrías delegar esto a un 'AlbumService' en el futuro
    success = photo_service.photo_controller.delete_album(album_id)
    
    if not success:
        raise HTTPException(status_code=404, detail="Álbum no encontrado o no se pudo eliminar")
        
    return None

@router.delete("/{photo_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_photo(
    photo_id: UUID,
    current_user: UserResponse = Depends(get_current_user),
    photo_service: PhotosService = Depends(get_photos_service)
):
    """
    Elimina permanentemente una foto y libera espacio de almacenamiento.
    """
    try:
        photo_service.delete_photo(photo_id, current_user.id)
        return None # 204 No Content no devuelve cuerpo
    except OctopusError as e:
        raise HTTPException(status_code=400, detail=e.message)