"""
Módulo de servicio para la gestión de fotografías, metadatos y miniaturas.
"""
import logging
from uuid import UUID
from PIL import Image
from pathlib import Path
from sqlalchemy.orm import Session
from fastapi import HTTPException, status
from typing import Optional, BinaryIO, List

from app.services.users_service import UserService
from app.services.storage_service import StorageService
from app.services.metadata_service import MetadataService
from app.controllers.photo_controller import PhotoController
from app.schemas import PhotoCreate, PhotoResponse, AlbumResponse
from app.settings import settings

class PhotosService:
    """
    Servicio de alto nivel para el ciclo de vida de las fotos.
    Maneja la carga, generación de thumbnails y persistencia de metadatos.
    """
    def __init__(self, session: Session):
        self.logger = logging.getLogger(self.__class__.__name__)
        self.session = session
        
        # Encapsulamiento de dependencias
        self.photo_controller = PhotoController(session)
        self.storage_service = StorageService(session)
        self.user_service = UserService(session)
        self.metadata_service = MetadataService()
        
        # Configuración de miniaturas (podría ir en settings)
        self.thumb_size = (250, 250)

    # =========== MÉTODOS PRIVADOS ===========
    def _generate_thumbnail(self, original_path: Path, user_id: UUID) -> bool:
        """
        Genera una versión reducida de la imagen para previsualizaciones.
        
        Args:
            original_path (Path): Ruta de la foto original.
            user_id (UUID): ID del usuario para ubicar su carpeta de miniaturas.
        """
        try:
            thumb_dir = self.storage_service.get_user_thubnail_path(user_id)
            thumb_path = thumb_dir / original_path.name
            
            with Image.open(original_path) as img:
                # Mantenemos la relación de aspecto usando thumbnail()
                img.thumbnail(self.thumb_size)
                # Convertimos a RGB si es necesario (para evitar errores con formatos RGBA en JPEG)
                if img.mode in ("RGBA", "P"):
                    img = img.convert("RGB")
                img.save(thumb_path, "JPEG", optimize=True, quality=85)
            
            return True
        except Exception as e:
            self.logger.error(f"Error generando miniatura para {original_path.name}: {e}")
            return False

    # =========== METODOS PARA SUBIR/CREAR ===========
    def upload_photo(self, user_id: UUID, file_stream: BinaryIO, filename: str, description: Optional[str] = None) -> Optional[PhotoResponse]:
        """
        Orquesta el flujo completo de subida:
        1. Guarda el archivo físico (StorageService).
        2. Genera la miniatura.
        3. Extrae metadatos EXIF (MetadataService).
        4. Persiste la información en la base de datos.
        """
        target_path = None
        try:
            # 1. Almacenamiento físico y actualización de cuota
            target_path = self.storage_service.save_photo_stream(user_id, file_stream, filename)
            if not target_path:
                return None

            # 2. Generar Miniatura
            self._generate_thumbnail(target_path, user_id)

            # 3. Extracción de Metadatos
            metadata = self.metadata_service.extract_metadata(target_path)

            # 4. Preparar objeto para el controlador
            # Combinamos la info de archivo con los metadatos extraídos
            photo_data = PhotoCreate(
                file_name=target_path.name,
                description=description,
                storage_path=str(target_path),
                **metadata.model_dump() # Desempaquetamos los metadatos EXIF
            )

            # 5. Persistencia en DB
            new_photo = self.photo_controller.create_photo(user_id=user_id, photo_in=photo_data)
            
            self.logger.info(f"Foto {target_path.name} procesada y registrada para el usuario {user_id}")
            return new_photo

        except Exception as e:
            self.logger.error(f"Fallo en el flujo de upload_photo: {e}")
            # Limpieza en caso de error para mantener consistencia
            if target_path and target_path.exists():
                self.storage_service.delete_photo_file(user_id, target_path)
            return None

    def create_album(self, user_id: UUID, album_name: str) -> Optional[AlbumResponse]:
        """
        Crea un nuevo álbum para un usuario.

        Args:
            user_id (UUID): ID del propietario.
            album_name (str): Nombre del álbum.

        Returns:
            Optional[AlbumResponse]: El esquema de respuesta o None.
        """
        return self.photo_controller.create_album(user_id, album_name)

    def add_photo_to_album(self, photo_id: UUID, album_id: UUID) -> bool:
        """
        Crea la relación N:N entre una foto y un álbum.

        Args:
            photo_id (UUID): ID de la foto.
            album_id (UUID): ID del álbum.
        
        Returns:
            bool: True si la operación fue exitosa, False en caso contrario.
        """
        return self.photo_controller.add_photo_to_album(photo_id, album_id)

    # =========== MÉTODOS GET ===========
    def get_user_photos(self, user_id: UUID, skip: int = 0, limit: int = 100) -> PhotoResponse:
        """
        Recupera la lista de fotos de un usuario con paginación.

        Args:
            user_id (UUID): ID del propietario.
            skip (int): Desplazamiento.
            limit (int): Tamaño de página.

        Returns:
            PhotoResponse: Objeto con la lista de fotos y el total.
        """
        return self.photo_controller.get_user_photos(user_id, skip, limit)
    
    def get_album_by_id(self, album_id: UUID) -> Optional[AlbumResponse]:
        """
        Recupera un álbum por su ID.

        Args:
            album_id (UUID): ID del álbum.
        
        Returns:
            Optional[AlbumResponse]: El album y sus fotos o None.
        """
        return self.photo_controller.get_album_by_id(album_id)
    
    def get_user_albums(self, user_id: UUID) -> List[AlbumResponse]:
        """
        Recupera todos los álbumes de un usuario.

        Args:
            user_id (UUID): ID del propietario.

        Returns:
            List[AlbumResponse]: Lista de álbumes.
        """
        return self.photo_controller.get_user_albums(user_id)
    
    # =========== MÉTODOS DELETE ===========
    def delete_photo(self, photo_id: UUID, requester_id: UUID) -> bool:
        """
        Elimina una fotografia a petición de requester_id.

        Args:
            photo_id (UUID): ID de la foto.
            requester_id (UUID): ID del usuario que solicita la eliminación.

        Returns:
            bool: True si se eliminó, False si no se pudo eliminar.
        """
        photo = self.photo_controller.get_by_id(photo_id)
        if not photo:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Photo with ID {photo_id} not found."
            )

        user_photo = self.user_service.get_user_by_id(requester_id)
        if not user_photo:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"User with ID {requester_id} not found."
            )
        
        if user_photo.id != photo.user_id and not self.user_service._is_user_admin(requester_id):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"User {requester_id} does not have permission to delete photo {photo_id}."
            )
        
        success = self.photo_controller.delete_photo(photo_id)
        if not success:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Photo with ID {photo_id} not found."
            )
        return success
    
    def delete_album(self, album_id: UUID, requester_id: UUID) -> bool:
        """
        Elimina un álbum a petición de requester_id.

        Args:
            album_id (UUID): ID del álbum.
            requester_id (UUID): ID del usuario que solicita la eliminación.

        Returns:
            bool: True si se eliminó, False si no se pudo eliminar.
        """
        album = self.photo_controller.get_album_by_id(album_id)
        if not album:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Album with ID {album_id} not found."
            )

        user_album = self.user_service.get_user_by_id(requester_id)
        if not user_album:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"User with ID {requester_id} not found."
            )
        
        if user_album.id != album.user_id and not self.user_service._is_user_admin(requester_id):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"User {requester_id} does not have permission to delete album {album_id}."
            )
        
        success = self.photo_controller.delete_album(album_id)
        if not success:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Album with ID {album_id} not found."
            )
        return success