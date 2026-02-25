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
from app.schemas import PhotoCreate, PhotoResponse, PhotoResponseList, PhotoUpdate
from app.errors import ValidationError, ResourceNotFoundError, PermissionDeniedError, OctopusError

class PhotoService:
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
    def _validate_ownership(self, photo_ids: List[UUID], user_id: UUID) -> List[UUID]:
        """
        Verifica que una lista de fotos pertenezca a un usuario.
        
        Args:
            photo_ids: Lista de IDs a verificar.
            user_id: ID del usuario propietario.
            
        Returns:
            List[UUID]: Lista de IDs que efectivamente pertenecen al usuario.
            
        Raises:
            PermissionDeniedError: Si algún ID no pertenece al usuario y no es ADMIN.
        """
        # Si es ADMIN, saltamos la validación de propiedad (opcional según tu política)
        if self.user_service._is_user_admin(user_id):
            return photo_ids

        # Consultamos al controlador (quien sí conoce los modelos) 
        # para que nos devuelva solo las fotos que coinciden con el dueño.
        owned_ids = self.photo_controller.filter_owned_photos(photo_ids, user_id)
        
        if len(owned_ids) != len(photo_ids):
            raise PermissionDeniedError(
                message="Uno o más recursos no te pertenecen.",
                details={"requested": len(photo_ids), "authorized": len(owned_ids)}
            )
            
        return owned_ids

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
    def upload_photo(
            self, 
            user_id: UUID, 
            file_stream: BinaryIO, 
            filename: str, 
            description: Optional[str] = None, 
            tags: Optional[List[str]] = None
        ) -> PhotoResponse:
        """
        Sube una foto al servidor desde la API y en stream.

        Args:
            user_id (UUID): ID del propietario.
            file_stream (BinaryIO): El objeto de flujo binario del archivo.
            filename (str): Nombre original del archivo.
            description (Optional[str]): Descripción opcional.
            tags (Optional[List[str]]): Lista de etiquetas.

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
                tags=tags,
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

    # =========== MÉTODOS GET ===========
    def get_photo_by_id(self, photo_id: UUID, requester_id: UUID) -> Optional[PhotoResponse]:
        """
        Recupera una foto por su ID.

        Args:
            photo_id (UUID): ID de la foto.
            requester_id (UUID): ID del usuario que solicita la operación.

        Returns:
            Optional[PhotoResponse]: El esquema de respuesta o None.
        """
        self._validate_ownership([photo_id], requester_id)
        return self.photo_controller.get_by_id(photo_id)
    
    def get_user_photos(self, user_id: UUID, skip: int = 0, limit: int = 100, only_deleted: bool = False) -> PhotoResponseList:
        """
        Recupera la lista de fotos de un usuario con paginación.

        Args:
            user_id (UUID): ID del propietario.
            skip (int): Desplazamiento.
            limit (int): Tamaño de página.
            only_deleted (bool): Flag para determinar si filtramos por fotos borradas o no.

        Returns:
            PhotoResponseList: Objeto con la lista de fotos y el total.
        """
        return self.photo_controller.get_user_photos(user_id, skip, limit, only_deleted)
    
    # =========== MÉTODOS PUT ===========
    def update_photo_metadata(self, photo_id: UUID, photo_update: PhotoUpdate, requester_id: UUID) -> Optional[PhotoResponse]:
        """
        Actualiza los metadatos de una foto.

        Args:
            photo_id (UUID): ID de la foto.
            photo_update (PhotoUpdate): Datos actualizados.
            requester_id (UUID): ID del usuario que solicita la actualización.

        Returns:
            Optional[PhotoResponse]: El esquema de respuesta o None.
        """
        photo = self.photo_controller.get_by_id(photo_id)
        if not photo:
            raise ResourceNotFoundError(
                message="Foto no encontrada",
                details={"photo_id": str(photo_id)}
            )
        
        self._validate_ownership([photo_id], requester_id)
        return self.photo_controller.update_photo(photo_id, photo_update)
    
    # =========== MÉTODOS DELETE ===========
    def trash_photo(self, photo_id: UUID, requester_id: UUID) -> bool:
        """
        Mueve una foto a la papelera. No borra archivos físicos.
        """
        # 1. Validar existencia y propiedad
        self._validate_ownership([photo_id], requester_id)

        # 2. Marcar en DB
        success = self.photo_controller.trash_photo(photo_id)
        if success:
            self.logger.info(f"Foto {photo_id} movida a la papelera por {requester_id}")
        return success

    def delete_photo_permanently(self, photo_id: UUID, requester_id: UUID) -> bool:
        """
        Elimina una fotografia permanentemente a petición de requester_id.

        Args:
            photo_id (UUID): ID de la foto.
            requester_id (UUID): ID del usuario que solicita la eliminación.

        Returns:
            bool: True si se eliminó, False si no se pudo eliminar.
        
        Raises:
            ResourceNotFoundError: Si la foto no existe.
            PermissionDeniedError: Si el usuario no tiene permisos.
        """
        # 1. Obtener metadatos necesarios para el borrado físico posterior
        photo = self.photo_controller.get_by_id(photo_id)
        if not photo:
            raise ResourceNotFoundError(
                message="Foto no encontrada",
                details={"photo_id": str(photo_id)}
            )

        # 2. Validación de permisos (Rigor de seguridad)
        # Reutilizamos _validate_ownership para mantener la lógica centralizada
        self._validate_ownership([photo_id], requester_id)

        # 3. BORRADO EN BASE DE DATOS (Primero la DB para asegurar integridad)
        # Si esto falla, lanzará una excepción y no tocaremos el disco.
        success = self.photo_controller.delete_photo(photo_id)
        
        if not success:
            raise OctopusError("No se pudo eliminar el registro de la base de datos.")

        # 4. BORRADO FÍSICO (Post-Commit)
        # En este punto, el registro ya no existe en la DB. 
        # Si el borrado físico falla, al menos no tenemos registros huérfanos.
        try:
            original_path = Path(photo.storage_path)
            
            # El storage_service.delete_photo_file actualiza la cuota
            self.storage_service.delete_photo_file(photo.user_id, original_path)

            # 5. BORRADO DE MINIATURA
            thumb_dir = self.storage_service.get_user_thubnail_path(photo.user_id)
            thumb_path = thumb_dir / original_path.name
            if thumb_path.exists():
                thumb_path.unlink()
                
            self.logger.info(f"Foto {photo_id} y sus archivos eliminados por {requester_id}")
            
        except Exception as e:
            # Si llegamos aquí, tenemos "basura" en disco, pero la API es consistente.
            # Se podría implementar un worker de limpieza (Garbage Collector) posterior.
            self.logger.error(f"Error en borrado físico de foto {photo_id}: {e}")
            
        return True