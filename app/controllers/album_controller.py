"""
Photo controller module for database CRUD operations.
"""
import logging
from uuid import UUID
from typing import Optional, List
from sqlalchemy import select
from sqlalchemy.orm import Session, selectinload

from app.controllers.base_controller import BaseController
from app.errors import OctopusError, ResourceNotFoundError
from app.database.models.associations import album_photos
from app.database.models.photos_model import PhotoDatabaseModel
from app.database.models.albums_model import AlbumDatabaseModel
from app.schemas import AlbumResponse, AlbumCreate, AlbumListResponse, AlbumUpdate

class AlbumController(BaseController):
    """
    Controlador para la gestión de operaciones de base de datos de albumes.
    Maneja la persistencia de registros y relaciones con álbumes.
    """
    def __init__(self, session: Session) -> None:
        super().__init__(session)
        self.logger = logging.getLogger(self.__class__.__name__)

    def create_album(self, new_album_data: AlbumCreate, validated_photo_ids: List[UUID] = None) -> Optional[AlbumResponse]:
        """
        Crea un nuevo álbum para un usuario.

        Args:
            new_album_data (AlbumCreate): Datos del nuevo álbum.
            validated_photo_ids (List[UUID]): Lista de IDs de fotos válidas.

        Returns:
            Optional[AlbumDatabaseModel]: El modelo del álbum creado o None.
        """
        user_id = self._validate_uudi(new_album_data.user_id)
        
        new_album = AlbumDatabaseModel(
            user_id=user_id, 
            name=new_album_data.name, 
            description=new_album_data.description
        )

        # Si hay fotos, buscamos los objetos REALES de la sesión
        if validated_photo_ids:
            stmt = select(PhotoDatabaseModel).where(PhotoDatabaseModel.id.in_(validated_photo_ids))
            photos_objs = self.session.execute(stmt).scalars().all()
            new_album.photos = list(photos_objs)
        
        if not self._commit_or_rollback(new_album):
            return None
            
        self.session.refresh(new_album)
        return AlbumResponse.model_validate(new_album)

    def is_album_owner(self, album_id: UUID, user_id: UUID) -> bool:
        """
        Comprobación de propiedad de álbum a nivel de datos.

        Args:
            album_id (UUID): ID del álbum.
            user_id (UUID): ID del usuario propietario.

        Returns:
            bool: True si el álbum pertenece al usuario, False en caso contrario.
        """
        album = self.session.get(AlbumDatabaseModel, album_id)
        return album is not None and album.user_id == user_id

    def get_album_by_id(self, album_id: UUID) -> Optional[AlbumResponse]:
        """
        Recupera un álbum por su ID.

        Args:
            album_id (UUID): ID del álbum.

        Returns:
            Optional[AlbumResponse]: El esquema de respuesta o None.
        """
        album_id = self._validate_uudi(album_id)
        album_db = self._get_item_by_id(AlbumDatabaseModel, album_id)
        if album_db:
            return AlbumResponse.model_validate(album_db)
        return None

    def get_user_albums(self, user_id: UUID) -> AlbumListResponse:
        """
        Recupera todos los álbumes de un usuario.

        Args:
            user_id (UUID): ID del propietario.

        Returns:
            AlbumListResponse: Objeto con la lista de álbumes y el total.
        """
        user_id = self._validate_uudi(user_id)
        stmt = (
            select(AlbumDatabaseModel)
            .where(AlbumDatabaseModel.user_id == user_id)
            .options(selectinload(AlbumDatabaseModel.photos))
        )
        albums_db = self.session.execute(stmt).scalars().all()
        return AlbumListResponse(count=len(albums_db), albums=[AlbumResponse.model_validate(a) for a in albums_db])

    def update_album(self, album_id: UUID, album_update: AlbumUpdate) -> Optional[AlbumResponse]:
        """
        Actualiza la metadata de un album de fotos

        Args:
            album_id (UUID): ID del álbum.
            album_update (AlbumUpdate): Datos actualizados.
        
        Returns:
            Optional[AlbumResponse]: El esquema de respuesta o None.
        """
        album_id = self._validate_uudi(album_id)
        album = self.session.get(AlbumDatabaseModel, album_id)
        if not album:
            return None

        for key, value in album_update.model_dump(exclude_unset=True).items():
            setattr(album, key, value)

        if not self._commit_or_rollback(album):
            return None
        self.session.refresh(album)
        return AlbumResponse.model_validate(album)

    def add_photo_to_album(self, photo_id: UUID, album_id: UUID) -> bool:
        """
        Crea la relación N:N entre una foto y un álbum.

        Args:
            photo_id (UUID): ID de la foto.
            album_id (UUID): ID del álbum.

        Returns:
            bool: True si la operación fue exitosa, False en caso contrario.
        """
        photo_id = self._validate_uudi(photo_id)
        album_id = self._validate_uudi(album_id)

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

    def add_several_photos_to_album(self, photo_ids: List[UUID], album_id: UUID) -> bool:
        """
        Relaciona múltiples fotos con un álbum en una sola transacción.
        
        Args:
            photo_ids (List[UUID]): Lista de IDs de las fotos.
            album_id (UUID): ID del álbum.
            
        Returns:
            bool: True si la operación fue exitosa.
        """
        # 1. Validaciones de rigor
        album_id = self._validate_uudi(album_id)
        valid_photo_ids = [self._validate_uudi(pid) for pid in photo_ids]

        try:
            # 2. Obtenemos el álbum
            album = self.session.get(AlbumDatabaseModel, album_id)
            if not album:
                raise ResourceNotFoundError(message="Álbum no encontrado")

            # 3. Obtenemos todas las fotos que existen de la lista proporcionada
            # Esto es mucho más eficiente que un bucle: una sola consulta SQL con 'IN'
            stmt = select(PhotoDatabaseModel).where(PhotoDatabaseModel.id.in_(valid_photo_ids))
            photos = self.session.execute(stmt).scalars().all()

            # 4. Agregamos solo las que no estén ya relacionadas
            existing_ids = {p.id for p in album.photos}
            added_count = 0
            
            for photo in photos:
                if photo.id not in existing_ids:
                    album.photos.append(photo)
                    added_count += 1

            # 5. Commit único para toda la operación
            if added_count > 0:
                self.session.commit()
                self.logger.info(f"Se añadieron {added_count} fotos al álbum {album_id}")
            
            return True

        except Exception as e:
            self.session.rollback()
            self.logger.error(f"Error masivo al vincular fotos al álbum {album_id}: {e}")
            return False

    def remove_photo_from_album(self, photo_id: UUID, album_id: UUID) -> AlbumResponse:
        """
        Quita una foto de un album pero sin eliminarla ni de la base de datos ni del almacenamiento.

        Args:
            photo_id (UUID): ID de la foto.
            album_id (UUID): ID del álbum.
        
        Returns:
            AlbumResponse: El esquema del album sin la foto removida.
        """
        photo_id = self._validate_uudi(photo_id)
        album_id = self._validate_uudi(album_id)

        # 1. Buscamos la foto y el álbum con sus relaciones cargadas
        # Usamos select(AlbumDatabaseModel) para acceder a su atributo .photos
        photo = self.session.get(PhotoDatabaseModel, photo_id)
        album = self.session.get(AlbumDatabaseModel, album_id)

        if not photo or not album:
            raise ResourceNotFoundError(
                message="Foto o Álbum no encontrado",
                details={"photo_id": str(photo_id), "album_id": str(album_id)}
            )

        # 2. Lógica de desasociación
        if photo in album.photos:
            album.photos.remove(photo)
            try:
                self.session.commit()
                self.logger.info(f"Foto {photo_id} removida del álbum {album_id}")
            except Exception as e:
                self.session.rollback()
                raise OctopusError(f"Error al desasociar la foto: {str(e)}")
        else:
            self.logger.warning(f"La foto {photo_id} no pertenecía al álbum {album_id}")

        return AlbumResponse.model_validate(photo)
    
    def remove_several_photos_from_album(self, photo_ids: List[UUID], album_id: UUID) -> bool:
        """
        Quita varias fotos de un album en una única transacción
        
        Args:
            photo_ids (List[UUID]): Lista de IDs de las fotos.
            album_id (UUID): ID del álbum.
            
        Returns:
            bool: True si la operación fue exitosa. False en caso contrario.
        """
        valid_album_id = self._validate_uudi(album_id)
        valid_photo_ids = [self._validate_uudi(pid) for pid in photo_ids]

        try:
            album = self.session.get(AlbumDatabaseModel, valid_album_id)
            if not album:
                raise ResourceNotFoundError(message="Álbum no encontrado")

            stmt = (
                select(PhotoDatabaseModel)
                .where(PhotoDatabaseModel.id.in_(valid_photo_ids))
            )
            photos = self.session.execute(stmt).scalars().all()
            delete_count = 0

            for photo in photos:
                if photo in album.photos:
                    album.photos.remove(photo)
                    delete_count += 1

            if delete_count > 0:
                self.session.commit()
                self.logger.info(f"Se eliminaron {delete_count} fotos del álbum {album_id}")
            
            return True
        except Exception as e:
            self.session.rollback()
            self.logger.error(f"Error al eliminar fotos del álbum {album_id}: {e}")
            return False

    def delete_album(self, album_id: UUID) -> bool:
        """
        Elimina el registro del álbum de la DB.

        Args:
            album_id (UUID): ID del álbum.
        
        Returns:
            bool: True si la eliminación fue exitosa, False en caso contrario.
        """
        album_id = self._validate_uudi(album_id)        
        album = self.session.get(AlbumDatabaseModel, album_id)
        
        if not album:
            return False

        try:
            # Al eliminar el objeto 'album', SQLAlchemy eliminará automáticamente
            # las entradas en la tabla de asociación si está configurado en cascada simple.
            self.session.delete(album)
            self.session.commit()
            return True
        except Exception as e:
            self.session.rollback()
            self.logger.error(f"Error al eliminar álbum {album_id}: {e}")
            return False