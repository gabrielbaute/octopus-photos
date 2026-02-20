"""
Módulo de rutas para la gestión de fotografías.
"""
from uuid import UUID
from typing import Optional, List
from fastapi import APIRouter, Depends, UploadFile, File, Form, status, HTTPException

from app.enums import UserRole
from app.errors import OctopusError
from app.schemas.user_schemas import UserResponse
from app.services.photos_service import PhotosService
from app.api.dependencies import get_current_user, get_photos_service
from app.schemas.photos_schemas import PhotoResponse, PhotoResponseList

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