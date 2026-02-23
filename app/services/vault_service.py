"""
Módulo de servicio para la gestión del Baúl Seguro (Vault).
"""
import os
import io
import logging
from pathlib import Path
from uuid import UUID, uuid4
from sqlalchemy.orm import Session
from typing import Tuple, Generator
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.ciphers.aead import AESGCM
from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC

from app.controllers import PhotoController
from app.services.storage_service import StorageService
from app.errors import StorageError, PermissionDeniedError, ResourceNotFoundError

class VaultService:
    def __init__(self, session: Session):
        self.logger = logging.getLogger(self.__class__.__name__)
        self.storage_service = StorageService(session)
        self.photo_controller = PhotoController(session)
        self.session = session

    # =========== LÓGICA CRIPTOGRÁFICA ===========
    def _derive_key(self, password: str, salt: bytes) -> bytes:
        """
        Deriva una clave simétrica de 32 bytes usando PBKDF2.

        Args:
            password (str): Contraseña única del usuario para encriptar la información. No se almacena.
            salt (bytes): Salt aleatorio para encriptado.

        Returns:
            bytes: Clave simétrica de 32 bytes.s
        """
        kdf = PBKDF2HMAC(
            algorithm=hashes.SHA256(),
            length=32,
            salt=salt,
            iterations=100000,
        )
        return kdf.derive(password.encode())

    def _encrypt_data(self, data: bytes, password: str) -> Tuple[bytes, bytes]:
        """
        Cifra bytes y retorna (salt, encrypted_blob).

        Args:
            data (bytes): Bytes de la fotografia.
            password (str): Contraseña única del usuario para encriptar la información. No se almacena.

        Returns:
            Tuple[bytes, bytes]: Salt y blob cifrado.
        """
        salt = os.urandom(16)
        nonce = os.urandom(12)
        key = self._derive_key(password, salt)
        aesgcm = AESGCM(key)
        
        # El blob final contiene el nonce concatenado para poder descifrar luego
        encrypted_content = aesgcm.encrypt(nonce, data, None)
        return salt, nonce + encrypted_content

    def _decrypt_data(self, encrypted_blob: bytes, password: str, salt: bytes) -> bytes:
        """
        Descifra los bytes en memoria.

        Args:
            encrypted_blob (bytes): Blob cifrado.
            password (str): Contraseña única del usuario.
            salt (bytes): Salt
        """
        # El blob que guardamos era: NONCE (12b) + DATA_CIFRADA
        nonce = encrypted_blob[:12]
        ciphertext = encrypted_blob[12:]
        
        key = self._derive_key(password, salt)
        aesgcm = AESGCM(key)
        
        try:
            return aesgcm.decrypt(nonce, ciphertext, None)
        except Exception:
            raise PermissionDeniedError(
                message="Permiso denegado.",
                details="Contraseña del baúl incorrecta o archivo corrupto."
                )

    # =========== OPERACIONES DEL BAÚL ===========
    def lock_photo(self, photo_id: UUID, user_id: UUID, vault_password: str) -> bool:
        """
        Cifra original y miniatura, y actualiza el registro en DB.
        """
        photo_db = self.photo_controller.get_by_id(photo_id)
        if not photo_db or str(photo_db.user_id) != str(user_id):
            raise PermissionDeniedError("Recurso no encontrado o acceso denegado.")

        # Rutas de origen (usando la lógica de tu StorageService)
        original_path = Path(photo_db.storage_path)
        thumb_dir = self.storage_service.get_user_thubnail_path(user_id)
        thumb_path = thumb_dir / original_path.name

        try:
            # 1. Cifrar Original
            with open(original_path, "rb") as f:
                salt_hex, blob_o = self._encrypt_data(f.read(), vault_password)
            
            # Definimos la nueva ruta en el baúl
            vault_photo_path = self.storage_service.get_user_path(user_id, "vault/photos") / f"{photo_id}.vault"
            
            with open(vault_photo_path, "wb") as f:
                # Guardamos: SALT (16b) + NONCE (12b) + DATA_CIFRADA
                f.write(blob_o) # Asumiendo que _encrypt_data ya concatenó el nonce al principio

            # 2. Cifrar Miniatura (si existe)
            if thumb_path.exists():
                with open(thumb_path, "rb") as f:
                    # Usamos el mismo salt por simplicidad o uno nuevo para mayor seguridad
                    _, blob_t = self._encrypt_data(f.read(), vault_password)
                
                vault_thumb_path = self.storage_service.get_user_path(user_id, "vault/thumbnails") / f"{photo_id}.tmb.vault"
                with open(vault_thumb_path, "wb") as f:
                    f.write(blob_t)

            # 3. Actualizar DB vía Controller
            self.photo_controller.mark_as_encrypted(
                photo_id=photo_id,
                new_storage_path=str(vault_photo_path),
                salt=salt_hex
            )

            # 4. Cleanup físico
            original_path.unlink()
            if thumb_path.exists():
                thumb_path.unlink()

            return True
        except Exception as e:
            raise StorageError(
                message="No se pudo encriptar y asegurar tu foto",
                details={"photo_id": str(photo_id), "os_error": str(e)}
            )

    def get_decrypted_stream(
        self, 
        photo_id: UUID, 
        user_id: UUID, 
        vault_password: str, 
        is_thumbnail: bool = False
    ) -> io.BytesIO:
        """
        Descifra los datos y los devuelve como un objeto binario en memoria.

        Args:
            photo_id (UUID): ID de la foto.
            user_id (UUID): ID del propietario.
            vault_password (str): Contraseña del baúl.
            is_thumbnail (bool): Si es True, desencripta y envía el Thumbnail. Si es False, busca la foto original.

        Returns:
            io.BytesIO: Cadena de bits con la imagen.
        """
        photo_db = self.photo_controller.get_by_id(photo_id)
        if not photo_db or not photo_db.is_encrypted:
            raise ResourceNotFoundError(
                message="Recurso no disponible en el baúl.",
                details={"photo_id": str(photo_id)}
                )
        
        if photo_db.user_id != user_id:
            raise PermissionDeniedError(
                message="Acceso denegado. No eres el propietario de esta foto.",
                details={"photo_id": str(photo_id)}
                )

        # Lógica de rutas
        if is_thumbnail:
            file_path = self.storage_service.get_user_path(user_id, "vault/thumbnails") / f"{photo_id}.tmb.vault"
        else:
            file_path = Path(photo_db.storage_path)

        if not file_path.exists():
            raise StorageError(
                    message="Archivo físico no encontrado.",
                    details={"path": str(file_path)}
                    )

        salt = bytes.fromhex(photo_db.encryption_salt)
        
        with open(file_path, "rb") as f:
            encrypted_content = f.read()

        # Desciframos y devolvemos el buffer
        decrypted_bytes = self._decrypt_data(encrypted_content, vault_password, salt)
        
        return io.BytesIO(decrypted_bytes)