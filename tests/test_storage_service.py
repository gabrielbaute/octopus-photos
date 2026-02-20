import pytest
from uuid import uuid4
from io import BytesIO
from pathlib import Path

from app.enums import UserRole
from app.schemas import UserCreate
from app.services.users_service import UserService
from app.services.storage_service import StorageService


def test_init_user_storage_creates_folders(db_session, temp_storage):
    service = StorageService(db_session)
    user_id = uuid4()
    
    storage_data = service.init_user_storage(user_id)
    
    # Verificar DB
    assert storage_data.user_id == user_id
    # Verificar carpetas físicas
    user_path = temp_storage / str(user_id)
    assert (user_path / "photos").exists()
    assert (user_path / "thumbnails").exists()

def test_save_photo_stream_updates_quota(db_session, temp_storage):
    # 1. PREPARACIÓN
    user_service = UserService(db_session)
    user = user_service.register_user(UserCreate(
        username="storage_tester",
        email="storage@test.com",
        password="password123",
        role=UserRole.USER
    ))
    
    storage_service = StorageService(db_session)
    user_id = user.id

    # Forzamos que el registro de storage exista si register_user no lo hizo
    # Si ya existe, get_user_storage nos lo dará. Si no, lo creamos.
    storage_info = storage_service.get_user_storage(user_id)
    if not storage_info:
        storage_service.init_user_storage(user_id)
        # Hacemos un flush para que los cambios sean visibles en esta sesión
        db_session.flush() 

    # 2. EJECUCIÓN
    asset_path = Path(__file__).parent / "assets" / "vacaciones.jpg"
    with open(asset_path, "rb") as f:
        file_bytes = f.read()
        file_size = len(file_bytes)
        asset_file = BytesIO(file_bytes)

    # Ahora save_photo_stream DEBE encontrar el registro para actualizar la cuota
    path = storage_service.save_photo_stream(user_id, asset_file, original_filename="vacaciones.jpg")

    # 3. VERIFICACIÓN
    assert path.exists()
    
    # Recargamos el objeto de la sesión para ver el cambio de la cuota
    db_session.expire_all() 
    updated_storage = storage_service.get_user_storage(user_id)
    
    assert updated_storage is not None, f"Fallo crítico: No se encontró storage para {user_id}"
    assert updated_storage.storage_bytes_size == file_size