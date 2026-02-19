"""
Controlador base con métodos comunes a todos los controladores.
"""
import logging
from typing import Any, Optional, Type
from sqlalchemy.orm import Session
from sqlalchemy.exc import SQLAlchemyError

class BaseController:
    """
    Controlador base para manejar operaciones de base de datos con gestión de sesiones explícita.
    """
    def __init__(self, session: Session) -> None:
        """
        Inicializa el controlador con una sesión de base de datos dedicada y un registrador.
        """
        self.logger = logging.getLogger(self.__class__.__name__)
        self.session = session

    def _commit_or_rollback(self, record: Any) -> bool:
        """
        Helper interno para confirmar un nuevo registro o revertirlo en caso de error.

        Args:
            record (object): La instancia del modelo SQLAlchemy que se guardará.

        Returns:
            bool: Verdadero si la operación fue exitosa, falso en caso contrario.
        """
        try:
            self.session.add(record)
            self.session.commit()
            self.logger.info(f"Successfully committed: {record}")
            return True
        except SQLAlchemyError as e:
            self.session.rollback()
            self.logger.error(f"SQLAlchemy Error during commit: {e}")
            return False

    def _update_or_rollback(self, record: Any) -> bool:
        """
        Helper interno para actualizar un registro existente o revertirlo en caso de error.

        Args:
            record (object): La instancia del modelo SQLAlchemy que se actualizará.

        Returns:
            bool: True si la actualización fue exitosa, False en caso contrario.
        """
        try:
            self.session.add(record)
            self.session.commit()
            self.logger.info(f"Successfully updated: {record}")
            return True
        except SQLAlchemyError as e:
            self.session.rollback()
            self.logger.error(f"SQLAlchemy Error during update: {e}")
            return False

    def _delete_or_rollback(self, record: Any) -> bool:
        """
        Helper interno para eliminar un registro o revertirlo en caso de error.

        Args:
            record (object): La instancia del modelo SQLAlchemy que se eliminará.

        Returns:
            bool: True si la eliminación fue exitosa, False en caso contrario.
        """
        try:
            self.session.delete(record)
            self.session.commit()
            self.logger.info(f"Successfully deleted: {record}")
            return True
        except SQLAlchemyError as e:
            self.session.rollback()
            self.logger.error(f"SQLAlchemy Error during deletion: {e}")
            return False

    def _get_item_by_id(self, model: Type[Any], item_id: str) -> Optional[Any]:
        """
        Recupera un elemento por su ID de la base de datos utilizando el Mapa de identidad.

        Args:
            model (Type[Any]): La clase de modelo SQLAlchemy para consultar.
            item_id (int): La ID primaria del elemento.

        Returns:
            Optional[Any]: La instancia del modelo recuperada o None si no se encuentra/error.
        """
        try:
            # session.get es la forma preferida para búsquedas por PK en SQLAlchemy 2.0
            item = self.session.get(model, item_id)
            if item:
                self.logger.info(f"Successfully retrieved {model.__tablename__} ID: {item_id}")
                return item
            
            self.logger.warning(f"{model.__tablename__} with ID {item_id} not found.")
            return None
        except SQLAlchemyError as e:
            self.logger.error(f"SQLAlchemy Error during retrieval of {model.__tablename__}: {e}")
            return None
    
    def _close_session(self) -> None:
        """
        Cierram manualmente la sesión de base de datos.
        Debe llamarse cuando el controlador ya no sea necesario.
        """
        self.session.close()
        self.logger.debug("Database session closed.")