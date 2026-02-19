"""
Photo controller module for database CRUD operations.
"""
import logging
from uuid import UUID
from typing import Optional, List
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.schemas.metadata_schemas import PhotoMetadata
from app.controllers.base_controller import BaseController
from app.database.models.associations import album_photos
from app.database.models.photos_model import PhotoDatabaseModel
from app.database.models.albums_model import AlbumDatabaseModel
from app.schemas.photos_schemas import PhotoCreate, PhotoResponse, PhotoResponseList

class PhotoController(BaseController):
    """
    Controlador para la gestión de operaciones de base de datos de fotos.
    Maneja la persistencia de registros y relaciones con álbumes.
    """

    def __init__(self, session: Session) -> None:
        super().__init__(session)
        self.logger = logging.getLogger(self.__class__.__name__)

    def create_photo(
        self, 
        user_id: UUID, 
        photo_data: PhotoCreate, 
        storage_path: str, 
        metadata: PhotoMetadata
    ) -> Optional[PhotoResponse]:
        """
        Crea un registro de foto en la base de datos integrando metadatos técnicos.

        Args:
            user_id (UUID): ID del propietario.
            photo_data (PhotoCreate): Datos básicos (file_name, description, tags).
            storage_path (str): Ruta final del archivo en el sistema de archivos.
            metadata (PhotoMetadata): Metadatos EXIF ya parseados.
        
        Returns:
            Optional[PhotoResponse]: El esquema de respuesta o None.
        """
        # Combinamos datos de creación y metadatos técnicos
        # model_dump(exclude_unset=True) asegura que no sobreescribamos con Nones si no hay EXIF
        db_photo = PhotoDatabaseModel(
            user_id=user_id,
            storage_path=storage_path,
            file_name=photo_data.file_name,
            description=photo_data.description,
            tags=",".join(photo_data.tags) if photo_data.tags else None,
            **metadata.model_dump(exclude_unset=True) 
        )

        if not self._commit_or_rollback(db_photo):
            return None

        self.session.refresh(db_photo)
        return PhotoResponse.model_validate(db_photo)

    def get_by_id(self, photo_id: UUID) -> Optional[PhotoResponse]:
        """
        Recupera una foto por su ID.
        
        Args:
            photo_id (UUID): ID de la foto.
        
        Returns:
            Optional[PhotoResponse]: El esquema de respuesta o None.
        """
        photo_db = self._get_item_by_id(PhotoDatabaseModel, photo_id)
        if photo_db:
            return PhotoResponse.model_validate(photo_db)
        return None

    def get_user_photos(self, user_id: UUID, skip: int = 0, limit: int = 100) -> PhotoResponseList:
        """
        Obtiene la lista de fotos de un usuario con paginación.
        
        Args:
            user_id (UUID): ID del propietario.
            skip (int): Saltar
            limit (int): Tamaño de paginado de la petición
        
        Returns:
            PhotoResponseList: Objeto con la lista de fotos y el total.
        """
        stmt = (
            select(PhotoDatabaseModel)
            .where(PhotoDatabaseModel.user_id == user_id)
            .offset(skip)
            .limit(limit)
        )
        photos_db = self.session.execute(stmt).scalars().all()
        count_stmt = select(PhotoDatabaseModel).where(PhotoDatabaseModel.user_id == user_id)
        total = len(self.session.execute(count_stmt).scalars().all())

        return PhotoResponseList(
            count=total,
            photos=[PhotoResponse.model_validate(p) for p in photos_db]
        )

    def add_photo_to_album(self, photo_id: UUID, album_id: UUID) -> bool:
        """
        Crea la relación N:N entre una foto y un álbum.

        Args:
            photo_id (UUID): ID de la foto.
            album_id (UUID): ID del álbum.

        Returns:
            bool: True si la operación fue exitosa, False en caso contrario.
        """
        try:
            photo = self.session.get(PhotoDatabaseModel, photo_id)
            album = self.session.get(AlbumDatabaseModel, album_id)

            if photo and album:
                if photo not in album.photos:
                    album.photos.append(photo)
                    return self._commit_or_rollback(album)
            return False
        except Exception as e:
            self.logger.error(f"Error linking photo {photo_id} to album {album_id}: {e}")
            self.session.rollback()
            return False

    def delete_photo(self, photo_id: UUID) -> bool:
        """
        Elimina el registro de la foto de la DB.

        Args:
            photo_id (UUID): ID de la foto.

        Returns:
            bool: True si la eliminación fue exitosa, False en caso contrario.
        """
        photo_db = self._get_item_by_id(PhotoDatabaseModel, photo_id)
        if not photo_db:
            return False
        return self._delete_or_rollback(photo_db)