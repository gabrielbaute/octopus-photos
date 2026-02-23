"""
Módulo de servicio para la gestión física del almacenamiento.
"""
import uuid
import shutil
import logging
from uuid import UUID
from pathlib import Path
from sqlalchemy.orm import Session
from typing import Optional, BinaryIO

from app.settings import settings
from app.enums import FormatImage
from app.schemas.storage_schemas import UserStorage
from app.controllers.storage_controller import StorageController
from app.errors import ValidationError, ResourceNotFoundError, StorageError, PermissionDeniedError

class StorageService:
    """
    Servicio de alto nivel para gestionar el almacenamiento físico de los usuarios.
    Orquesta la creación de directorios y la actualización de cuotas en DB.
    """

    def __init__(self, session: Session):
        self.logger = logging.getLogger(self.__class__.__name__)
        self.controller = StorageController(session)
        self.base_path = Path(settings.STORAGE_BASE_PATH)
        self._ensure_base_path()

    # CREACIÓN DE RUTAS
    def _ensure_base_path(self) -> None:
        """Garantiza que el directorio raíz de la aplicación exista."""
        try:
            self.base_path.mkdir(parents=True, exist_ok=True)
        except OSError as e:
            raise StorageError(
                message="No se pudo inicializar el almacenamiento base en el servidor.",
                details={"path": str(self.base_path), "os_error": str(e)}
            )
    
    def init_user_storage(self, user_id: UUID) -> Optional[UserStorage]:
        """
        Crea la estructura de carpetas física y el registro en DB para un nuevo usuario.

        Args:
            user_id (UUID): ID del usuario.

        Returns:
            Optional[UserStorage]: El esquema de respuesta o None.
        """
        user_path = self.base_path / str(user_id)
        
        try:
            # 0. Verificar si ya existe para evitar el UNIQUE constraint error
            existing = self.get_user_storage(user_id)
            if existing:
                return existing
            
            # 1. Crear directorios físicos (incluyendo subcarpeta para fotos y miniaturas si deseas)
            user_path.mkdir(parents=True, exist_ok=True)
            (user_path / "photos").mkdir(exist_ok=True)
            (user_path / "thumbnails").mkdir(exist_ok=True)
            (user_path / "vault").mkdir(exist_ok=True)
            (user_path / "vault" / "photos").mkdir(exist_ok=True)
            (user_path / "vault" / "thumbnails").mkdir(exist_ok=True)
            
            self.logger.info(f"Physical storage created for user {user_id} at {user_path}")
            
            # 2. Registrar en la base de datos usando el controlador
            return self.controller.create_initial_storage(
                user_id=str(user_id), 
                path=str(user_path)
            )
            
        except OSError as e:
            raise StorageError(
                message="No se pudo inicializar el almacenamiento físico para el usuario.",
                details={"user_id": str(user_id), "os_error": str(e)}
            )

    # CONSULTAS
    def get_user_path(self, user_id: UUID, subfolder: str = "photos") -> Path:
        """
        Obtiene la ruta a una subcarpeta específica del usuario.
        
        Args:
            user_id (UUID): ID del usuario.
            subfolder (str): Nombre de la subcarpeta.

        Returns:
            Path: Ruta a la subcarpeta de fotos.
        """
        return self.base_path / str(user_id) / subfolder
    
    def get_user_thubnail_path(self, user_id: UUID) -> Path:
        """
        Obtiene la ruta a la subcarpeta de miniaturas del usuario.

        Args:
            user_id (UUID): ID del usuario.

        Returns:
            Path: Ruta a la subcarpeta de miniaturas.
        """
        return self.base_path / str(user_id) / "thumbnails"

    def get_user_storage(self, user_id: UUID) -> Optional[UserStorage]:
        """
        Obtiene información del almacenamiento de un usuario.

        Args:
            user_id (UUID): ID del usuario.
        """
        if isinstance(user_id, str):
            user_id = UUID(user_id)
        return self.controller.get_uses_storage(user_id)

    # SUBIDA Y ACTUALIZACIÓN
    def prepare_new_photo_path(self, user_id: UUID, original_filename: str) -> Optional[Path]:
        """
        Genera una ruta única para evitar colisiones de nombres. Retorna la ruta completa hacia la subcarpeta 'photos'.

        Args:
            user_id (UUID): ID del usuario.
            original_filename (str): Nombre original del archivo.
        
        Returns:
            Optional[Path]: Ruta de destino o None si falla.
        """
        user_photos_dir = self.get_user_path(user_id, "photos")
        
        if not user_photos_dir.exists():
            self.logger.warning(f"Storage no inicializado para {user_id}. Intentando crear...")
            user_photos_dir.mkdir(parents=True, exist_ok=True)

        extension = Path(original_filename).suffix.lower()
        unique_name = f"{uuid.uuid4()}{extension}"
        return user_photos_dir / unique_name

    def register_file_upload(self, user_id: UUID, file_size_bytes: int) -> bool:
        """
        Notifica al sistema que se ha guardado un nuevo archivo para actualizar estadísticas.

        Args:
            user_id (UUID): ID del usuario.
            file_size_bytes (int): Tamaño del archivo en bytes.

        Returns:
            bool: True si la actualización fue exitosa, False en caso contrario.
        """
        return self.controller.update_usage(
            user_id=str(user_id), 
            size_delta=file_size_bytes, 
            files_delta=1
        )

    def save_photo_stream(self, user_id: UUID, file_stream: BinaryIO, original_filename: str) -> Path:
        """
        Guarda una foto desde un stream binario, gestiona el archivo físico y actualiza la DB.
        
        Asegura la integridad eliminando el archivo físico si la actualización de la base 
        de datos falla. Utiliza shutil para un manejo eficiente del buffer de memoria.
        
        Args:
            user_id (UUID): ID del propietario.
            file_stream (BinaryIO): El objeto de flujo binario del archivo.
            original_filename (str): Nombre original para extraer la extensión.
            
        Returns:
            Path: La ruta absoluta del archivo guardado o None si ocurre un error.
        """
        target_path = self.prepare_new_photo_path(user_id, original_filename)
        
        # 1. Verificar si el usuario tiene almacenamiento inicializado
        if not target_path:
            raise ResourceNotFoundError(
                message="El almacenamiento del usuario no ha sido inicializado.",
                details={"user_id": str(user_id)}
            )

        try:
            if file_stream.seekable():
                file_stream.seek(0)

            # 2. Escritura física con captura de errores de disco (disco lleno, etc)
            try:
                with open(target_path, "wb") as buffer:
                    shutil.copyfileobj(file_stream, buffer)
            except OSError as e:
                raise StorageError(
                    message="Error de escritura en disco duro.",
                    details={"user_id": str(user_id), "os_error": str(e)}
                )
            
            file_size = target_path.stat().st_size
            
            # 3. Actualización en DB (si el controller falla, lanzamos error)
            success = self.register_file_upload(user_id, file_size)
            
            if not success:
                # Rollback físico inmediato
                target_path.unlink(missing_ok=True)
                raise StorageError(
                    message="No se pudo actualizar la cuota de almacenamiento en la base de datos.",
                    details={"user_id": str(user_id), "file": original_filename}
                )

            return target_path

        except Exception as e:
            if target_path and target_path.exists():
                target_path.unlink()
            
            # Si ya es un error nuestro, lo re-lanzamos; si no, lo envolvemos
            if isinstance(e, (StorageError, ResourceNotFoundError)):
                raise e
            raise StorageError(f"Fallo inesperado en el almacenamiento: {str(e)}")

    def sync_db_stats_with_disk(self, user_id: UUID) -> bool:
        """
        Repara/Sincroniza las estadísticas de la DB escaneando el disco. Útil para tareas de mantenimiento o tras fallos críticos.

        Args:
            user_id (UUID): ID del usuario.

        Returns:
            bool: True si la actualización fue exitosa, False en caso contrario.
        """
        user_photos_dir = self.get_user_path(user_id, "photos")
        if not user_photos_dir.exists():
            return False

        # Solo contamos archivos que coincidan con nuestros formatos soportados
        valid_exts = [f".{fmt.value.lower()}" for fmt in FormatImage]
        files = [f for f in user_photos_dir.glob("*") if f.is_file() and f.suffix.lower() in valid_exts]
        
        total_size = sum(f.stat().st_size for f in files)
        total_count = len(files)

        # Actualizamos la DB con los valores reales absolutos
        # Nota: Aquí el controller necesitaría un método update_absolute o similar
        # Por ahora usaremos la lógica de deltas calculando la diferencia si es necesario
        return self.controller.update_usage(
            user_id=str(user_id),
            size_delta=total_size, # Esto asume un reset previo o un método dedicado
            files_delta=total_count
        )

    def move_to_vault(self, user_id: UUID, file_path: Path) -> bool:
        """
        Mueve una foto de la ubicación de foto al baúl de seguridad del usuario

        Args:
            user_id (UUID): ID del usuario.
            file_path (Path): Ruta al archivo a mover.

        Returns:
            bool: True si la operación fue exitosa, False en caso contrario.
        """
        vault_path = self.get_user_path(user_id, "vault")
        try:
            shutil.move(file_path, vault_path / "photos" / file_path.name)
            return True
        except OSError as e:
            raise StorageError(
                message="No se pudo mover el archivo a la carpeta de seguridad.",
                details={"path": str(file_path), "os_error": str(e)}
            )

    # ELIMINACIÓN
    def register_file_deletion(self, user_id: UUID, file_size_bytes: int) -> bool:
        """
        Notifica al sistema que se ha eliminado un archivo para restar de las estadísticas.

        Args:
            user_id (UUID): ID del usuario.
            file_size_bytes (int): Tamaño del archivo en bytes.

        Returns:
            bool: True si la actualización fue exitosa, False en caso contrario.
        """
        return self.controller.update_usage(
            user_id=str(user_id), 
            size_delta=-file_size_bytes, 
            files_delta=-1
        )

    def delete_photo_file(self, user_id: UUID, file_path: Path) -> bool:
        """
        Elimina el archivo físico y actualiza estadísticas.
        
        Args:
            user_id (UUID): ID del usuario.
            file_path (Path): Ruta al archivo a eliminar
        
        Returns:
            bool: True si la eliminación fue exitosa, False en caso contrario.
        """
        if not file_path.exists():
            # Si no existe, quizás ya se borró, lanzamos un error informativo
            raise ResourceNotFoundError(
                message="El archivo físico no existe en el servidor.",
                details={"path": str(file_path)}
            )

        try:
            file_size = file_path.stat().st_size
            file_path.unlink()
            
            success = self.register_file_deletion(user_id, file_size)
            if not success:
                self.logger.error(f"Archivo borrado pero falló actualización de cuota para {user_id}")
                # Aquí no lanzamos error porque el archivo YA se borró, pero marcamos la inconsistencia en el log.
                
            return True
        except OSError as e:
            raise StorageError(
                message="No se pudo eliminar el archivo físico.",
                details={"path": str(file_path), "os_error": str(e)}
            )

    def delete_all_user_data(self, user_id: UUID) -> bool:
        """
        Elimina físicamente TODA la carpeta del usuario. Peligroso y definitivo.

        Args:
            user_id (UUID): ID del usuario.

        Returns:
            bool: True si la eliminación fue exitosa, False en caso contrario.
        """
        user_path = self.base_path / str(user_id)
        if user_path.exists() and user_path.is_dir():
            try:
                shutil.rmtree(user_path)
                self.logger.warning(f"All physical data for user {user_id} has been deleted.")
                return True
            except OSError as e:
                raise StorageError(
                    message="No se pudo eliminar la carpeta física del usuario.",
                    details={"path": str(user_path), "os_error": str(e)}
                )
        return True