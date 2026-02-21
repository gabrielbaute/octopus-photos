"""
Módulo de servicio para la gestión de albumes de fotos de un usuario.
"""
import logging
from uuid import UUID
from typing import Optional, List
from sqlalchemy.orm import Session

from app.services.users_service import UserService
from app.controllers.album_controller import AlbumController
from app.controllers.photo_controller import PhotoController
from app.errors import ResourceNotFoundError, PermissionDeniedError
from app.schemas import AlbumResponse, AlbumCreate, AlbumListResponse, AlbumUpdate

class AlbumService:
    """
    Servicio de alto nivel para el ciclo de vida de los álbumes.
    """
    def __init__(self, session: Session):
        self.logger = logging.getLogger(self.__class__.__name__)
        self.session = session
        
        # Encapsulamiento de dependencias
        self.album_controller = AlbumController(session)
        self.photo_controller = PhotoController(session)
        self.user_service = UserService(session)
    
    # =========== MÉTODOS PRIVADOS ===========
    def _validate_ownership(self, album_id: UUID, user_id: UUID) -> bool:
        """
        Verifica que un álbum pertenezca a un usuario.
        
        Args:
            album_id: ID del álbum a verificar.
            user_id: ID del usuario propietario.
            
        Returns:
            bool: True si el álbum pertenece al usuario, False en caso contrario.
        """
        if self.user_service._is_user_admin(user_id):
            return True
        
        return self.album_controller.is_album_owner(album_id, user_id)
    
    def _validate_photo_ownership(self, photo_ids: List[UUID], user_id: UUID) -> bool:
        """
        Verifica que una o varias fotos pertenezcan a un usuario.
        
        Args:
            photo_ids (List[UUID]): Lista de IDs a verificar.
            user_id (UUID): ID del usuario propietario.
            
        Returns:
            bool: True si las fotos pertenecen al usuario, False en caso contrario.
        """
        if self.user_service._is_user_admin(user_id):
            return True
        
        # Obtenemos solo las que sí le pertenecen
        owned_ids = self.photo_controller.filter_owned_photos(photo_ids, user_id)
        
        # RIGOR: El número de fotos encontradas debe coincidir con el solicitado
        # Si pides 5 y el filtro devuelve 3, significa que hay 2 que no te pertenecen.
        return len(owned_ids) == len(photo_ids)

    # =========== METODOS PARA AGREGAR/CREAR ===========
    def create_album(self, new_album_data: AlbumCreate) -> Optional[AlbumResponse]:
        """
        Crea un nuevo álbum para un usuario.

        Args:
            new_album_data (AlbumCreate): Datos del nuevo álbum.

        Returns:
            Optional[AlbumResponse]: El esquema de respuesta o None.
        """
        return self.album_controller.create_album(new_album_data)

    def add_photo_to_album(self, photo_id: UUID, album_id: UUID, requester_id: UUID) -> bool:
        """
        Crea la relación N:N entre una foto y un álbum.

        Args:
            photo_id (UUID): ID de la foto.
            album_id (UUID): ID del álbum.
            requester_id (UUID): ID del usuario que solicita la operación.
        
        Returns:
            bool: True si la operación fue exitosa, False en caso contrario.
        """
        if not self._validate_ownership(album_id, requester_id):
            raise PermissionDeniedError(
                message="No eres el propietario del álbum.",
                details={"album_id": str(album_id)}
            )
        
        if not self._validate_photo_ownership([photo_id], requester_id):
            raise PermissionDeniedError(
                message="La foto no pertenece al usuario.",
                details={"photo_id": str(photo_id)}
            )

        return self.album_controller.add_photo_to_album(photo_id, album_id)

    def add_photos_to_album(self, photo_ids: List[UUID], album_id: UUID, requester_id: UUID) -> bool:
        """
        Relaciona múltiples fotos con un álbum en una sola transacción.

        Args:
            photo_ids (List[UUID]): Lista de IDs de las fotos.
            album_id (UUID): ID del álbum.
            requester_id (UUID): ID del usuario que solicita la operación.

        Returns:
            bool: True si la operación fue exitosa.
        """
        # 1. Validar propiedad de las fotos (usando nuestro nuevo método)
        valid_photo_ids = self._validate_photo_ownership(photo_ids, requester_id)
        if not valid_photo_ids:
            raise PermissionDeniedError(
                message="Una o varias fotos no pertenecen al usuario.",
                details={"photo_ids": [str(photo_id) for photo_id in photo_ids]}
            )

        # 2. Validar propiedad del álbum 
        if not self.album_controller.is_album_owner(album_id, requester_id):
             raise PermissionDeniedError(
                 message="No eres el propietario del álbum.",
                 details={"album_id": str(album_id)}
                )
            
        # 3. Delegar la operación masiva al controlador
        return self.album_controller.add_several_photos_to_album(photo_ids, album_id)

    # =========== MÉTODOS GET ===========
    def get_album_by_id(self, album_id: UUID, requester_id: UUID) -> Optional[AlbumResponse]:
        """
        Recupera un álbum por su ID.

        Args:
            album_id (UUID): ID del álbum.
            requester_id (UUID): ID del usuario que solicita la operación.
        
        Returns:
            Optional[AlbumResponse]: El album y sus fotos o None.
        """
        if not self._validate_ownership(album_id, requester_id):
            raise PermissionDeniedError(
                message="No tienes permiso para acceder a este recurso.",
                details={"album_id": str(album_id)}
            )
        return self.album_controller.get_album_by_id(album_id)
    
    def get_user_albums(self, user_id: UUID) -> AlbumListResponse:
        """
        Recupera todos los álbumes de un usuario.

        Args:
            user_id (UUID): ID del propietario.

        Returns:
            AlbumListResponse: Objeto con la lista de álbumes y el total.
        """
        return self.album_controller.get_user_albums(user_id)
    
    # =========== MÉTODOS PUT ===========
    def update_album_metadata(self, album_id: UUID, album_update: AlbumUpdate, requester_id: UUID) -> Optional[AlbumResponse]:
        """
        Actualiza los metadatos de un álbum.

        Args:
            album_id (UUID): ID del álbum.
            album_update (AlbumUpdate): metadata actualizada
            requester_id (UUID): ID del usuario que solicita la actualización.
        
        Returns:
            Optional[AlbumResponse]: Album actualizado o None.
        """
        if not self._validate_ownership(album_id, requester_id):
            raise PermissionDeniedError(
                message="No tienes permiso para modificar este álbum.",
                details={"album_id": str(album_id)}
            )

        updated_album = self.album_controller.update_album(album_id, album_update)
        
        if not updated_album:
            raise ResourceNotFoundError(message="No se pudo encontrar el álbum para actualizar.")

        return updated_album

    def add_photo_to_album(self, photo_id: UUID, album_id: UUID, requester_id: UUID) -> bool:
        """
        Crea la relación N:N entre una foto y un álbum.

        Args:
            photo_id (UUID): ID de la foto.
            album_id (UUID): ID del álbum.
            requester_id (UUID): ID del usuario que solicita la operación.
        
        Returns:
            bool: True si la operación fue exitosa, False en caso contrario.
        """
        if not self._validate_ownership(album_id, requester_id):
            raise PermissionDeniedError(
                message="No tienes permiso para agregar fotos a este álbum.",
                details={"album_id": str(album_id)}
            )
        return self.album_controller.add_photo_to_album(photo_id, album_id)

    def add_several_photos_to_album(self, photo_ids: List[UUID], album_id: UUID, requester_id: UUID) -> bool:
        """
        Relaciona múltiples fotos con un álbum en una sola transacción.

        Args:
            photo_ids (List[UUID]): Lista de IDs de las fotos.
            album_id (UUID): ID del álbum.
            requester_id (UUID): ID del usuario que solicita la operación.

        Returns:
            bool: True si la operación fue exitosa.
        """
        # 1. Verificamos que el requester_id es en efecto el propietario del album
        if not self._validate_ownership(album_id, requester_id):
             raise PermissionDeniedError(message="No eres el propietario del álbum.")

        # 2. Verificamos que todas las fotos que quiere agregar son, en efecto, fotos del requester_id
        if not self._validate_photo_ownership(photo_ids, requester_id):
            raise PermissionDeniedError("Una o varias fotos no pertenecen al usuario.")
        
        # 3. Delegar la operación masiva al controlador
        return self.album_controller.add_several_photos_to_album(photo_ids, album_id)

    # =========== MÉTODOS DELETE ===========
    def remove_photo_from_album(self, photo_id: UUID, album_id: UUID, requester_id: UUID) -> AlbumResponse:
        """
        Quita una foto de un album pero sin eliminarla ni de la base de datos ni del almacenamiento.

        Args:
            photo_id (UUID): ID de la foto.
            album_id (UUID): ID del álbum.
            requester_id (UUID): ID del usuario que solicita la eliminación.

        Returns:
            AlbumResponse: El objeto del album sin la foto removida.
        """
        if not self._validate_ownership(album_id, requester_id):
            raise PermissionDeniedError(
                message="No tienes permiso para eliminar fotos de este álbum.",
                details={"album_id": str(album_id)}
            )
        
        return self.album_controller.remove_photo_from_album(photo_id, album_id)
    
    def remove_several_photos_from_album(self, photo_ids: List[UUID], album_id: UUID, requester_id: UUID) -> bool:
        """
        Quita múltiples fotos de un album.

        Args:
            photo_ids (List[UUID]): Lista de IDs de las fotos.
            album_id (UUID): ID del álbum.
            requester_id (UUID): ID del usuario que solicita la eliminación.

        Returns:
            bool: True si la operación fue exitosa.
        """
        if not self._validate_ownership(album_id, requester_id):
            raise PermissionDeniedError(
                message="No tienes permiso para eliminar fotos de este álbum.",
                details={"album_id": str(album_id)}
            )
        
        return self.album_controller.remove_several_photos_from_album(photo_ids, album_id)
    
    def delete_album(self, album_id: UUID, requester_id: UUID) -> bool:
        """
        Elimina un álbum a petición de requester_id.

        Args:
            album_id (UUID): ID del álbum.
            requester_id (UUID): ID del usuario que solicita la eliminación.

        Returns:
            bool: True si se eliminó, False si no se pudo eliminar.
        """
        album = self.album_controller.get_album_by_id(album_id)
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
        
        success = self.album_controller.delete_album(album_id)
        if not success:
            raise ResourceNotFoundError(
                message=f"Album no encontrado.",
                details={"album_id": str(album_id)}
            )
        return success
