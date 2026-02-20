import pytest
from PIL import Image
from uuid import uuid4
from io import BytesIO
from pathlib import Path

from app.schemas import UserCreate
from app.enums import UserRole
from app.services.users_service import UserService
from app.services.photos_service import PhotosService

@pytest.fixture
def real_small_image():
    """Genera un stream de una imagen real de 1x1 píxeles."""
    img_byte_arr = BytesIO()
    img = Image.new('RGB', (100, 100), color='red')
    img.save(img_byte_arr, format='JPEG')
    img_byte_arr.seek(0)
    return img_byte_arr

def test_upload_photo_full_workflow(db_session, temp_storage, real_small_image):
    # 1. Necesitamos un usuario real en la DB para que el FK de la foto no falle
    user_service = UserService(db_session)
    user = user_service.register_user(UserCreate(
        username="photoguy", email="guy@test.com", password="password123", role=UserRole.USER
    ))
    
    photo_service = PhotosService(db_session)
    
    # 2. Ejecutar el servicio

    asset_path = Path(__file__).parent / "assets" / "vacaciones.jpg"
    
    with open(asset_path, "rb") as f:
        image_stream = BytesIO(f.read())

    photo_res = photo_service.upload_photo(
        user_id=user.id,
        file_stream=image_stream,
        filename="vacaciones.jpg",
        description="Mi primera foto"
    )
    
    # 3. Aseveraciones (Assertions)
    assert photo_res is not None
    assert photo_res.description == "Mi primera foto"
    
    # Verificar que existe la foto original y la miniatura
    original_path = Path(photo_res.storage_path)
    assert original_path.exists(), f"La foto original no se encontró en {original_path}"
    
    thumb_path = temp_storage / str(user.id) / "thumbnails" / photo_res.file_name
    assert thumb_path.exists(), f"La miniatura no existe en: {thumb_path}"
    
    # Verificar que se intentó extraer metadatos (aunque sea 1x1, el modelo estará ahí)
    assert hasattr(photo_res, "camera_make")