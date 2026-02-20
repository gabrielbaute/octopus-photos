"""
Módulo de servicio para la gestión de fotografías, metadatos y miniaturas.
"""
import logging
from uuid import UUID
from PIL import Image
from pathlib import Path
from sqlalchemy.orm import Session
from typing import Optional, BinaryIO, List

from app.services.users_service import UserService
from app.services.storage_service import StorageService
from app.services.metadata_service import MetadataService
from app.controllers.photo_controller import PhotoController
from app.schemas import PhotoCreate, PhotoResponse, AlbumResponse, PhotoResponseList, PhotoUpdate
from app.errors import ValidationError, ResourceNotFoundError, PermissionDeniedError, OctopusError

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
    def upload_photo(self, user_id: UUID, file_stream: BinaryIO, filename: str, description: Optional[str] = None) -> PhotoResponse:
        """
        Sube una foto al servidor desde la API y en stream.

        Args:
            user_id (UUID): ID del propietario.
            file_stream (BinaryIO): El objeto de flujo binario del archivo.
            filename (str): Nombre original del archivo.
            description (Optional[str]): Descripción opcional.

        Returns:
            PhotoResponse: El esquema de respuesta.
        
        Raises:
            ValidationError: Si el formato no es soportado.
        """
        target_path = self.storage_service.get_user_path(user_id)
        
        # 1. Validar extensión (prevención básica)
        suffix = Path(filename).suffix.lower()
        if suffix not in [".jpg", ".jpeg", ".png", ".webp"]:
            raise ValidationError(
                message="Formato de imagen no soportado",
                details={"supported_formats": [".jpg", ".jpeg", ".png", ".webp"]}
            )

        try:
            # 2. Almacenamiento (el storage_service debería lanzar StorageError si no hay cuota)
            target_path = self.storage_service.save_photo_stream(user_id, file_stream, filename)
            
            # 3. Procesamiento técnico
            self._generate_thumbnail(target_path, user_id)
            metadata = self.metadata_service.extract_metadata(target_path)

            photo_data = PhotoCreate(
                file_name=filename,
                description=description,
                **metadata.model_dump()
            )

            # 4. DB
            new_photo = self.photo_controller.create_photo(
                user_id=user_id,
                photo_data=photo_data,
                storage_path=str(target_path),
                metadata=metadata
                )
            
            if not new_photo:
                raise OctopusError("Error inesperado al persistir la foto en base de datos")

            return new_photo

        except Exception as e:
            # Rollback físico: si algo falló, borramos el rastro en disco
            if target_path and target_path.exists():
                self.storage_service.delete_photo_file(user_id, target_path)
            
            self.logger.error(f"Fallo crítico en upload: {str(e)}")
            raise OctopusError(f"Fallo crítico en upload: {str(e)}")
    

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
    def get_photo_by_id(self, photo_id: UUID) -> Optional[PhotoResponse]:
        """
        Recupera una foto por su ID.

        Args:
            photo_id (UUID): ID de la foto.

        Returns:
            Optional[PhotoResponse]: El esquema de respuesta o None.
        """
        return self.photo_controller.get_by_id(photo_id)
    
    def get_user_photos(self, user_id: UUID, skip: int = 0, limit: int = 100) -> PhotoResponseList:
        """
        Recupera la lista de fotos de un usuario con paginación.

        Args:
            user_id (UUID): ID del propietario.
            skip (int): Desplazamiento.
            limit (int): Tamaño de página.

        Returns:
            PhotoResponseList: Objeto con la lista de fotos y el total.
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
    
    # =========== MÉTODOS PUT ===========
    def update_photo_metadata(self, photo_id: UUID, photo_update: PhotoUpdate) -> Optional[PhotoResponse]:
        """
        Actualiza los metadatos de una foto.

        Args:
            photo_id (UUID): ID de la foto.
            photo_update (PhotoUpdate): Datos actualizados.

        Returns:
            Optional[PhotoResponse]: El esquema de respuesta o None.
        """
        return self.photo_controller.update_photo(photo_id, photo_update)
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
            raise ResourceNotFoundError(
                message=f"Foto no encontrada.",
                details={"photo_id": str(photo_id)}
            )

        user_photo = self.user_service.get_user_by_id(requester_id)
        if not user_photo:
            raise ResourceNotFoundError(
                message="Usuario solicitante de la acción no encontrado",
                details={"user_id": str(requester_id)}
            )
        
        if user_photo.id != photo.user_id and not self.user_service._is_user_admin(requester_id):
            raise PermissionDeniedError(
                message="Privilegios insuficientes",
                details={"action": "delete_photo", "required": "Rol de ADMIN o propietario de la foto."}
            )
        
        success = self.photo_controller.delete_photo(photo_id)
        if not success:
            raise ResourceNotFoundError(
                message=f"Foto no encontrada.",
                details={"photo_id": str(photo_id)}
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
            raise ResourceNotFoundError(
                message=f"Album no encontrado.",
                details={"album_id": str(album_id)}
            )

        user_album = self.user_service.get_user_by_id(requester_id)
        if not user_album:
            raise ResourceNotFoundError(
                message=f"Usuario no encontrado.",
                details={"user_id": str(requester_id)}
            )
        
        if user_album.id != album.user_id and not self.user_service._is_user_admin(requester_id):
            raise PermissionDeniedError(
                message="Privilegios insuficientes",
                details={"action": "delete_album", "required": "Rol de ADMIN o propietario del álbum."}
            )
        
        success = self.photo_controller.delete_album(album_id)
        if not success:
            raise ResourceNotFoundError(
                message=f"Album no encontrado.",
                details={"album_id": str(album_id)}
            )
        return success