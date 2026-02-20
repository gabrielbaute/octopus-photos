"""
Módulo de servicio para la gestión de los usuarios 
"""
import logging
from uuid import UUID
from typing import Optional
from sqlalchemy.orm import Session
from fastapi import HTTPException, status

from app.enums import UserRole
from app.controllers import UserController
from app.services.mail_service import MailService
from app.services.storage_service import StorageService
from app.services.security_service import SecurityService
from app.schemas import UserCreate, UserResponse, UserUpdate, UserLogin, UserListResponse

class UserService:
    """
    Servicio de alto nivel para gestionar la lógica de negocio de los usuarios.
    """
    def __init__(self, session: Session):
        self.logger = logging.getLogger(self.__class__.__name__)
        self.session = session
        self.user_controller = UserController(session)
        self.storage_service = StorageService(session)
        self.security_service = SecurityService()

    # ========= METODOS PRIVADOS =========
    def _is_user_admin(self, user_id: UUID) -> bool:
        """
        Verifica si un usuario es un administrador.

        Args:
            user_id (str): ID del usuario.

        Returns:
            bool: True si el usuario es un administrador, False en caso contrario.
        """
        user = self.user_controller.get_by_id(user_id)
        return user is not None and user.role == UserRole.ADMIN
    
    def _check_permissions(self, user_id: UUID) -> bool:
        """
        Verifica si un usuario tiene los permisos necesarios.

        Args:
            user_id (str): ID del usuario.

        Returns:
            bool: True si el usuario tiene los permisos, False en caso contrario.
        """
        user = self.user_controller.get_by_id(user_id)
        if not user:
            self.logger.warning(f"User with ID {user_id} not found for permission check.")
            return False
        return user.role == UserRole.ADMIN
    
    # ========= METODOS DE AUTENTICACIÓN =========
    def register_user(self, user_data: UserCreate) -> Optional[UserResponse]:
        """
        Orquesta el registro completo de un nuevo usuario:
        1. Hashea la contraseña.
        2. Crea el registro en la tabla de usuarios.
        3. Inicializa el almacenamiento físico y su registro de cuotas.
        
        Args:
            user_data (UserCreate): Datos de registro del usuario.

        Returns:
            Optional[UserResponse]: Datos del usuario creado o None si falla.
        """
        try:
            # 1. Seguridad: Hashear contraseña
            hashed_password = self.security_service.get_password_hash(user_data.password)
            
            # 2. Persistencia: Crear usuario en DB
            new_user_db = self.user_controller.create(user_data, hashed_password)
            if not new_user_db:
                return None

            # 3. Infraestructura: Inicializar Storage (Físico + DB)
            storage_init = self.storage_service.init_user_storage(new_user_db.id)
            
            if not storage_init:
                self.logger.error(f"Fallo crítico: No se pudo crear el storage para {new_user_db.id}")
                # Podríamos implementar un rollback aquí si fuera necesario
                return None

            self.logger.info(f"Usuario {new_user_db.username} registrado exitosamente con ID {new_user_db.id}")
            return new_user_db

        except Exception as e:
            self.logger.error(f"Error en el proceso de registro: {e}")
            return None
    
    def authenticate_user(self, login_credentials: UserLogin) -> Optional[UserResponse]:
        """
        Autenticación de usuario a partir de credenciales de inicio de sesión.
        
        Args:
            login_data (UserLogin): Credenciales de inicio de sesión.
            
        Returns:
            Optional[UserResponse]: Datos del usuario autenticado o None si falla.
        """
        user = self.user_controller.get_by_email(login_credentials.email)
        if not user:
            return None
        
        user_credentials = self.user_controller.get_user_hash(user.id)
        if not user_credentials:
            return None
        
        if not self.security_service.verify_password(login_credentials.password, user_credentials["password_hash"]):
            return None
        
        return user
    
    def request_password_recovery(self, email: str, mail_service: MailService) -> None:
        """
        Inicia el proceso de recuperación de contraseña por medio de un token. Se envía un correo con el token.

        Args:
            email (str): Email del usuario.
            mail_service (MailService): Servicio de envío de correos.
        Returns:
            None
        """
        user = self.user_controller.get_by_email(email)

        if user and user.is_active:
            # Creamos el token con el scope específico que definimos en SecurityService
            token = self.security_service.create_password_reset_token(user.id)

            # URL que apunta a tu frontend (Flutter o Web)
            recovery_url = f"{mail_service.base_url}/reset-password?token={token}"
            
            self.logger.info(f"Generating recovery token for user_id: {user.id}")
            mail_service.send_templated_email(
                recipient=user.email,
                subject="Recuperar contraseña",
                template="emails/recuperar_password.html",
                context={
                    "user_name": user.username,
                    "recovery_url": recovery_url
                }
            )
    
    def update_user_password(self, user_id: UUID, hashed_password: str) -> bool:
        """
        Actualiza la contraseña de un usuario.

        Args:
            user_id (str): ID del usuario.
            hashed_password (str): Contraseña hasheada.

        Returns:
            bool: True si la actualización fue exitosa, False en caso contrario.
        """
        return self.user_controller.update_user_password(user_id, hashed_password)

    # ========= CRUD =========
    def get_user_by_id(self, user_id: UUID) -> Optional[UserResponse]:
        """
        Obtiene un usuario por su ID.

        Args:
            user_id (str): ID del usuario.

        Returns:
            Optional[UserResponse]: Datos del usuario o None si no se encuentra.
        """
        user = self.user_controller.get_by_id(user_id)
        if not user:
            return None
        return user
    
    def list_all_users(self) -> UserListResponse:
        """
        Obtiene una lista de todos los usuarios.

        Returns:
            UserListResponse: Lista de usuarios.
        """
        return self.user_controller.get_all_users()

    def list_active_users(self, skip: int = 0, limit: int = 100) -> UserListResponse:
        """
        Obtiene la lista paginada de usuarios.

        Args:
            skip (int): Desplazamiento.
            limit (int): Tamaño de página.

        Returns:
            UserListResponse: Lista de usuarios.
        """
        return self.user_controller.get_multi(skip=skip, limit=limit)
    
    def update_user_info(self, user_id: UUID, update_data: UserUpdate) -> Optional[UserResponse]:
        """
        Actualiza la información de un usuario.

        Args:
            user_id (str): ID del usuario.
            update_data (UserUpdate): Datos de actualización.

        Returns:
            Optional[UserResponse]: Datos del usuario actualizado o None si falla.
        """
        updated_user = self.user_controller.update_user(user_id, update_data)
        if not updated_user:
            return None
        return updated_user
    
    def deactivate_user(self, user_id: str) -> UserResponse:
        """
        Desactiva un usuario.

        Args:
            user_id (str): ID del usuario.

        Returns:
            UserResponse: Datos del usuario desactivado.
        """
        user_update = UserUpdate(is_active=False)
        updated_user = self.user_controller.update_user(user_id, user_update)
        if not updated_user:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"User with ID {user_id} not found."
            )
        return updated_user

    def activate_user(self, user_id: str) -> UserResponse:
        """
        Activa un usuario.
        
        Args:
            user_id (str): ID del usuario.
        
        Returns:
            UserResponse: Datos del usuario activado.
        """
        user_update = UserUpdate(is_active=True)
        updated_user = self.user_controller.update_user(user_id, user_update)
        if not updated_user:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"User with ID {user_id} not found."
            )
        return updated_user
    
    def delete_user(self, user_id: UUID, requester_user_id: UUID) -> None:
        """
        Elimina un usuario.

        Args:
            user_id (str): ID del usuario.
            requester_user_id (str): ID del usuario que realiza la acción.

        Raises:
            HTTPException: Si el usuario no es un administrador.
        """
        if not self._is_user_admin(requester_user_id):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Only admins can delete users."
            )

        success = self.user_controller.delete_user(user_id)
        if not success:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"User with ID {user_id} not found."
            )