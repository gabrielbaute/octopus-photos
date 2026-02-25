"""
Photo controller module for database CRUD operations.
"""
import logging
from uuid import UUID
from datetime import date
from typing import Optional, List
from sqlalchemy import select, func, extract
from sqlalchemy.orm import Session, selectinload

from app.schemas.metadata_schemas import PhotoMetadata
from app.controllers.base_controller import BaseController
from app.database.models.associations import album_photos
from app.database.models.photos_model import PhotoDatabaseModel
from app.schemas import PhotoCreate, PhotoResponse, PhotoResponseList, PhotoUpdate

class PhotoController(BaseController):
    """
    Controlador para la gestión de operaciones de base de datos de fotos.
    Maneja la persistencia de registros y relaciones con álbumes.
    """

    def __init__(self, session: Session) -> None:
        super().__init__(session)
        self.logger = logging.getLogger(self.__class__.__name__)

    def filter_owned_photos(self, photo_ids: List[UUID], user_id: UUID) -> List[UUID]:
        """
        Consulta en DB los IDs que pertenecen al usuario.

        Args:
            photo_ids (List[UUID]): Lista de IDs a verificar.
            user_id (UUID): ID del usuario propietario.

        Returns:
            List[UUID]: Lista de IDs que efectivamente pertenecen al usuario.
        """
        stmt = (
            select(PhotoDatabaseModel.id)
            .where(
                PhotoDatabaseModel.id.in_(photo_ids),
                PhotoDatabaseModel.user_id == user_id
            )
        )
        return list(self.session.execute(stmt).scalars().all())

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
        photo_id = self._validate_uudi(photo_id)
        photo_db = self._get_item_by_id(PhotoDatabaseModel, photo_id)
        if photo_db:
            return PhotoResponse.model_validate(photo_db)
        return None

    def get_photos_this_day(self, user_id: UUID, target_date: date) -> PhotoResponseList:
        """
        Obtiene fotos de cualquier año que coincidan en mes y día.

        Args:
            user_id (UUID): ID del propietario.
            target_date (date): Día en que fue tomada la foto, sin importar el año.
        
        Returns:
            PhotoResponseList: Objeto con la lista de fotos y el total.
        """
        photos = self.session.execute(
            select(PhotoDatabaseModel)
            .where(
                PhotoDatabaseModel.user_id == user_id,
                PhotoDatabaseModel.is_deleted == False,
                extract('month', PhotoDatabaseModel.date_taken) == target_date.month,
                extract('day', PhotoDatabaseModel.date_taken) == target_date.day
            )
            .order_by(PhotoDatabaseModel.date_taken.desc())
        ).scalars().all()
        photos = [PhotoResponse.model_validate(p) for p in photos]
        return PhotoResponseList(count=len(photos), photos=photos)

    def get_by_range_date(
        self, 
        user_id: UUID, 
        start_date: str, 
        end_date: str,
        include_deleted: bool = False
    ) -> PhotoResponseList:
        """
        Obtiene una lista de fotos dentro de un rango de fechas.

        Args:
            user_id (UUID): ID del propietario.
            start_date (str): Fecha inicial.
            end_date (str): Fecha final.
            include_deleted (bool): True para traer las fotos en papelera, false para no.
        
        Returns:
            PhotoResponseList: Objeto con la lista de fotos y el total.
        """
        user_id = self._validate_uudi(user_id)
        filters = [PhotoDatabaseModel.user_id == user_id]
        if not include_deleted:
            filters.append(PhotoDatabaseModel.is_deleted == False)
        
        stmt = (
            select(PhotoDatabaseModel)
            .where(*filters, PhotoDatabaseModel.storage_date.between(start_date, end_date))
            .options(selectinload(PhotoDatabaseModel.albums))
        )
        photos_db = self.session.execute(stmt).scalars().all()

        count_stmt = select(func.count()).select_from(PhotoDatabaseModel).where(*filters)
        total = self.session.execute(count_stmt).scalar() or 0

        return PhotoResponseList(count=total, photos=[PhotoResponse.model_validate(p) for p in photos_db])

    def get_user_older_photo(self, user_id: UUID) -> Optional[PhotoResponse]:
        """
        Obtiene la foto más antigua de un usuario.

        Args:
            user_id (UUID): ID del propietario.
        
        Returns:
            Optional[PhotoResponse]: El esquema de respuesta o None.
        """
        user_id = self._validate_uudi(user_id)
        stmt = (
            select(PhotoDatabaseModel)
            .where(PhotoDatabaseModel.user_id == user_id)
            .order_by(PhotoDatabaseModel.storage_date.asc())
            .limit(1)
        )
        photo_db = self.session.execute(stmt).scalar()
        return PhotoResponse.model_validate(photo_db) if photo_db else None

    def mark_as_encrypted(
        self, 
        photo_id: UUID, 
        new_storage_path: str, 
        salt: str
    ) -> Optional[PhotoDatabaseModel]:
        """
        Actualiza el registro de la foto tras ser cifrada y movida al baúl.

        Args:
            photo_id (UUID): ID de la fotografía.
            new_storage_path (str): Nueva ruta física dentro de 'vault/photos'.
            salt (str): Salt hexadecimal utilizado para la derivación de la clave.
        """
        photo = self.session.query(PhotoDatabaseModel).filter(
            PhotoDatabaseModel.id == photo_id
        ).first()

        if photo:
            photo.is_encrypted = True
            photo.storage_path = new_storage_path
            photo.encryption_salt = salt
            self._update_or_rollback()
            self.session.refresh(photo)
        
        return photo

    def trash_photo(self, photo_id: UUID) -> bool:
        """
        Marca una foto como borrada (Soft Delete).

        Args:
            photo_id (UUID): ID de la foto.
        
        Returns:
            bool: True si la operación fue exitosa, False en caso contrario.
        """
        photo_db = self._get_item_by_id(PhotoDatabaseModel, photo_id)
        if not photo_db:
            return False
        
        photo_db.is_deleted = True
        photo_db.deleted_at = func.now() # O datetime.utcnow()
        
        return self._update_or_rollback(photo_db)

    def restore_photo(self, photo_id: UUID) -> bool:
        """
        Restaura una foto de la papelera.

        Args:
            photo_id (UUID): ID de la foto.
        
        Returns:
            bool: True si la operación fue exitosa, False en caso contrario.
        """
        photo_db = self._get_item_by_id(PhotoDatabaseModel, photo_id)
        if not photo_db:
            return False
        
        photo_db.is_deleted = False
        photo_db.deleted_at = None
        
        return self._update_or_rollback(photo_db)

    def get_user_photos(
            self, 
            user_id: UUID, 
            skip: int = 0, 
            limit: int = 100, 
            only_deleted: bool = False
        ) -> PhotoResponseList:
        """
        Obtiene la lista de fotos de un usuario con paginación.
        
        Args:
            user_id (UUID): ID del propietario.
            skip (int): Saltar
            limit (int): Tamaño de paginado de la petición
            include_deleted (bool): True para traer las fotos en papelera, false para no.
        
        Returns:
            PhotoResponseList: Objeto con la lista de fotos y el total.
        """
        user_id = self._validate_uudi(user_id)
        # Filtro base por usuario
        filters = [PhotoDatabaseModel.user_id == user_id]

        # Lógica de estados excluyentes
        if only_deleted:
            # Estado Papelera: is_deleted == True
            filters.append(PhotoDatabaseModel.is_deleted == True)
        else:
            # Estado Timeline: is_deleted == False
            filters.append(PhotoDatabaseModel.is_deleted == False)

        # 1. Consulta paginada
        stmt = (
            select(PhotoDatabaseModel)
            .where(*filters)
            .order_by(PhotoDatabaseModel.date_taken.desc()) # <--- Añade esto
            .offset(skip)
            .limit(limit)
        )
        photos_db = self.session.execute(stmt).scalars().all()
        
        # 2. Conteo coherente con los filtros aplicados
        count_stmt = select(func.count()).select_from(PhotoDatabaseModel).where(*filters)
        total = self.session.execute(count_stmt).scalar() or 0

        return PhotoResponseList(
            count=total,
            photos=[PhotoResponse.model_validate(p) for p in photos_db]
        )

    def update_photo(self, photo_id: UUID, photo_update: PhotoUpdate) -> Optional[PhotoResponse]:
        """
        Actualiza los metadatos de una foto.

        Args:
            photo_id (UUID): ID de la foto.
            photo_update (PhotoUpdate): Data a actualizar.
        
        Returns:
            Optional[PhotoResponse]: El esquema de respuesta o None.
        """
        photo_id = self._validate_uudi(photo_id)
        photo_db = self._get_item_by_id(PhotoDatabaseModel, photo_id)
        if not photo_db:
            return None

        for field, value in photo_update.model_dump(exclude_unset=True).items():
            setattr(photo_db, field, value)

        if not self._update_or_rollback(photo_db):
            return None

        self.session.refresh(photo_db)
        return PhotoResponse.model_validate(photo_db)

    def delete_photo(self, photo_id: UUID) -> bool:
        """
        Elimina el registro de la foto de la DB.

        Args:
            photo_id (UUID): ID de la foto.

        Returns:
            bool: True si la eliminación fue exitosa, False en caso contrario.
        """
        photo_id = self._validate_uudi(photo_id)
        photo_db = self._get_item_by_id(PhotoDatabaseModel, photo_id)
        if not photo_db:
            return False
        return self._delete_or_rollback(photo_db)
 