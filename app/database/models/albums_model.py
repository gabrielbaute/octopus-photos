import uuid
from typing import TYPE_CHECKING
from datetime import datetime, timezone
from sqlalchemy import DateTime, String, ForeignKey
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database.db_base import Base
from app.database.models.associations import album_photos
if TYPE_CHECKING:
    from app.database.models.users_model import UsersDatabaseModel
    from app.database.models.photos_model import PhotoDatabaseModel

class AlbumDatabaseModel(Base):
    """Modelo de tabla para álbumes."""
    __tablename__ = "albums"

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    user_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("users.id"))
    name: Mapped[str] = mapped_column(String, nullable=False)
    description: Mapped[str] = mapped_column(String, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=lambda: datetime.now(timezone.utc))

    # Relación con User
    user: Mapped["UsersDatabaseModel"] = relationship(back_populates="albums")
    
    # Relación N:N con las fotos
    photos: Mapped[list["PhotoDatabaseModel"]] = relationship(secondary=album_photos, back_populates="albums")