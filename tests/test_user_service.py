from uuid import UUID

from app.enums import UserRole
from app.schemas import UserCreate
from app.services.users_service import UserService

def test_register_user_success(db_session, monkeypatch):
    # Mockeamos el MailService dentro de UserService si es necesario
    service = UserService(db_session)
    
    user_in = UserCreate(
        username="testuser",
        email="test@example.com",
        password="strong_password",
        role=UserRole.USER
    )
    
    user_db = service.register_user(user_in)
    
    assert user_db.username == "testuser"
    assert isinstance(user_db.id, UUID)
    # Verificamos que se creó el registro de storage asociado
    user = service.user_controller.get_by_email(user_in.email)
    assert user.storage is not None