"""
User controller module for database CRUD operations.
"""
import logging
from typing import Optional, Dict
from sqlalchemy import select
from sqlalchemy.orm import Session
from sqlalchemy.exc import SQLAlchemyError

from app.controllers.base_controller import BaseController
from app.database.models.users_model import UsersDatabaseModel
from app.schemas.user_schemas import UserCreate, UserUpdate, UserResponse, UserListResponse

class UserController(BaseController):
    """
    Controlador para la gestión de operaciones de base de datos de bajo nivel para usuarios. 
    Actúa como límite entre los esquemas de Pydantic y los modelos de SQLAlchemy.
    """
    def __init__(self, session: Session) -> None:
        super().__init__(session)
        self.logger = logging.getLogger(self.__class__.__name__)

    def create(self, user_data: UserCreate, hashed_password: str) -> Optional[UserResponse]:
        """
        Asigna UserCreate a UsersDatabaseModel y lo conserva.

        Args:
            user_data (UserCreate): Esquema que contiene la entrada del usuario.
            hashed_password (str): Hash de contraseña precalculado.

        Returns:
            Optional[UserResponse]: The validated response schema or None.
        """
        # Extraemos los datos a un dict y eliminamos la password en plano
        user_dict = user_data.model_dump()
        user_dict.pop("password", None)
        
        # Creamos la instancia del modelo SQL inyectando el hash manualmente
        new_user = UsersDatabaseModel(
            **user_dict,
            password_hash=hashed_password
        )
        
        if not self._commit_or_rollback(new_user):
            return None
            
        self.session.refresh(new_user)
        return UserResponse.model_validate(new_user)

    def get_by_id(self, user_id: str) -> Optional[UserResponse]:
        """
        Obtiene un usuario por su ID.

        Args:
            user_id (str): ID del usuario.

        Returns:
            Optional[UserResponse]: El esquema de respuesta o None.
        """
        # Usamos el método heredado de BaseController
        user_db = self._get_item_by_id(UsersDatabaseModel, user_id)
        if user_db:
            return UserResponse.model_validate(user_db)
        return None

    def get_by_email(self, email: str) -> Optional[UserResponse]:
        """
        Obtiene un usuario por su dirección de correo electrónico.

        Args:
            email (str): Dirección de correo electrónico del usuario.
        """
        stmt = select(UsersDatabaseModel).where(UsersDatabaseModel.email == email)
        user_db = self.session.execute(stmt).scalar_one_or_none()
        
        if user_db:
            return UserResponse.model_validate(user_db)
        return None
    
    def get_user_hash(self, user_id: str) -> Optional[Dict[str,str]]:
        """
        Obtiene el hash de contraseña de un usuario por su ID.

        Args:
            user_id (str): ID del usuario.
        
        Returns:
            Optional[Dict[str,str]]: Un diccionario con el ID del usuario y su hash de contraseña.
        """
        try:
            stmt = select(UsersDatabaseModel.password_hash).where(UsersDatabaseModel.id == user_id)
            password_hash = self.session.execute(stmt).scalar_one_or_none()
            return {
                "user_id": user_id,
                "password_hash": password_hash
            }
        except SQLAlchemyError as e:
            self.logger.error(f"Error retrieving password hash for user {user_id}: {e}")
            return None
        
    
    def get_all_users(self) -> UserListResponse:
        """
        Obtiene todos los usarios en la base de datos.

        Returns:
            UserListResponse: Lista de usuarios con todos los usuarios.
        """
        stmt = select(UsersDatabaseModel)
        users_db = self.session.execute(stmt).scalars().all()
        
        users_list = [UserResponse.model_validate(user) for user in users_db]
        return UserListResponse(count=len(users_list), users=users_list)

    def update_user(self, user_id: str, update_data: UserUpdate) -> Optional[UserResponse]:
        """
        Actualiza la data de un usuario ya existente.

        Args:
            user_id (str): ID del usuario.
            update_data (UserUpdate): Datos de actualización del usuario.

        Returns:
            Optional[UserResponse]: El esquema de respuesta o None.
        """
        user_db = self._get_item_by_id(UsersDatabaseModel, user_id)
        if not user_db:
            self.logger.warning(f"User with ID {user_id} not found for update.")
            return None
        
        for field, value in update_data.model_dump(exclude_unset=True).items():
            setattr(user_db, field, value)
        
        if not self._update_or_rollback(user_db):
            self.logger.error(f"Failed to update user with ID {user_id}.")
            return None
        
        self.session.refresh(user_db)
        return UserResponse.model_validate(user_db)

    def update_user_password(self, user_id: str, hashed_password: str) -> bool:
        """
        Actualiza la contraseña de un usuario existente.

        Args:
            user_id (str): ID del usuario.
            hashed_password (str): Hash de la contraseña.

        Returns:
            bool: True si la actualización fue exitosa, False en caso contrario.
        """
        user_db = self._get_item_by_id(UsersDatabaseModel, user_id)
        if not user_db:
            self.logger.warning(f"User with ID {user_id} not found for password update.")
            return False
        
        user_db.password_hash = hashed_password
        
        if not self._update_or_rollback(user_db):
            self.logger.error(f"Failed to update password for user with ID {user_id}.")
            return False
        
        return True
    
    def delete_user(self, user_id: str) -> bool:
        """
        Elimina un usuario por su ID. Elimina sólo de la base de datos.

        Args:
            user_id (str): ID del usuario.

        Returns:
            bool: True si la eliminación fue exitosa, False en caso contrario.
        """
        user_db = self._get_item_by_id(UsersDatabaseModel, user_id)
        if not user_db:
            self.logger.warning(f"User with ID {user_id} not found for deletion.")
            return False
        
        return self._delete_or_rollback(user_db)