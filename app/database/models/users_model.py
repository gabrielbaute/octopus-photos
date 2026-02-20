import uuid
from typing import TYPE_CHECKING
from datetime import datetime, timezone
from sqlalchemy import DateTime, Enum, String, Boolean
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.enums import UserRole
from app.database.db_base import Base
if TYPE_CHECKING:
    from app.database.models.photos_model import PhotoDatabaseModel
    from app.database.models.albums_model import AlbumDatabaseModel
    from app.database.models.storage_model import UserStorageDatabaseModel

class UsersDatabaseModel(Base):
    """Modelo de tabla de usuarios."""
    __tablename__ = "users"

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    username: Mapped[str] = mapped_column(unique=True)
    email: Mapped[str] = mapped_column(unique=True)
    password_hash: Mapped[str] = mapped_column(String(255))
    created_at: Mapped[datetime] = mapped_column(DateTime, default=lambda: datetime.now(timezone.utc))
    role: Mapped[UserRole] = mapped_column(Enum(UserRole), default=UserRole.USER)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    
    # Relación 1:1 con el storage
    storage: Mapped["UserStorageDatabaseModel"] = relationship(back_populates="user", uselist=False)
    
    # Relación 1:N con las fotos
    photos: Mapped[list["PhotoDatabaseModel"]] = relationship(back_populates="user")

    # Dentro de la clase UsersDatabaseModel
    albums: Mapped[list["AlbumDatabaseModel"]] = relationship(back_populates="user", cascade="all, delete-orphan")