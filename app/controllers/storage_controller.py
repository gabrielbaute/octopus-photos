import logging
from uuid import UUID
from typing import Optional
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.database.models.storage_model import UserStorageDatabaseModel
from app.schemas.storage_schemas import UserStorage
from app.controllers.base_controller import BaseController

class StorageController(BaseController):
    """Controlador para la gestión de estadísticas de almacenamiento en DB."""

    def __init__(self, session: Session) -> None:
        """
        Inicializa el controlador con una sesión de base de datos dedicada.

        Args:
            session (Session): Sesión de base de datos.
        """
        super().__init__(session)
        self.logger = logging.getLogger(self.__class__.__name__)

    def create_initial_storage(self, user_id: UUID, path: str) -> Optional[UserStorage]:
        """
        Crea el registro inicial de almacenamiento para un usuario nuevo.

        Args:
            user_id (UUID): ID del usuario del almacenamiento.
            path (str): ruta del almacenamiento.

        Returns:
            Optional[UserStorage]: El esquema de respuesta o None.
        """
        user_id = self._validate_uudi(user_id)
        
        new_storage = UserStorageDatabaseModel(
            user_id=user_id,
            storage_path=path,
            count_files=0,
            storage_bytes_size=0
        )
        if self._commit_or_rollback(new_storage):
            self.session.refresh(new_storage)
            return UserStorage.model_validate(new_storage)
        return None

    def update_usage(self, user_id: UUID, size_delta: int, files_delta: int = 1) -> bool:
        """
        Actualiza el uso de espacio (incremento o decremento).

        Args:
            user_id (UUID): ID del usuario.
            size_delta (int): Incremento en bytes.
            files_delta (int): Incremento en archivos.

        Returns:
            bool: True si la actualización fue exitosa, False en caso contrario.
        """
        user_id = self._validate_uudi(user_id)
            
        try:
            stmt = select(UserStorageDatabaseModel).where(UserStorageDatabaseModel.user_id == user_id)
            storage_db = self.session.execute(stmt).scalar_one_or_none()
            
            if storage_db:
                storage_db.storage_bytes_size += size_delta
                storage_db.count_files += files_delta
                return self._commit_or_rollback(storage_db)
            return False
        except Exception as e:
            self.logger.error(f"Error updating storage for {user_id}: {e}")
            self.session.rollback()
            return False
        
    def get_uses_storage(self, user_id: UUID) -> Optional[UserStorage]:
        """
        Obtiene información del almacenamiento de un usuario.

        Args:
            user_id (UUID): ID del usuario.

        Returns:
            UserStorage: El esquema de respuesta.
        """
        user_id = self._validate_uudi(user_id)
        
        stmt = select(UserStorageDatabaseModel).where(UserStorageDatabaseModel.user_id == user_id)
        uses_storage = self.session.execute(stmt).scalar_one_or_none()
        
        if uses_storage:
            return UserStorage.model_validate(uses_storage)
        return None