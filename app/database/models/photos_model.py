import uuid
from datetime import datetime
from typing import TYPE_CHECKING, List
from sqlalchemy import Integer, DateTime, String, ForeignKey
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database.db_base import Base
from app.database.models.associations import album_photos
if TYPE_CHECKING:
    from app.database.models.users_model import UsersDatabaseModel
    from app.database.models.albums_model import AlbumDatabaseModel

class PhotoDatabaseModel(Base):
    """Modelo de tabla para fotos."""
    __tablename__ = "photos"

    # Almacenamiento y control
    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    user_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("users.id"))
    storage_date: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    storage_path: Mapped[str] = mapped_column(String, nullable=False)
    file_name: Mapped[str] = mapped_column(String, nullable=False)
    description: Mapped[str] = mapped_column(String, nullable=True)
    tags: Mapped[List[str]] = mapped_column(String, nullable=True)

    # Metadatos
    date_taken: Mapped[datetime] = mapped_column(DateTime, nullable=True)
    camera_make: Mapped[str] = mapped_column(String, nullable=True)
    camera_model: Mapped[str] = mapped_column(String, nullable=True)
    focal_length: Mapped[float] = mapped_column(Integer, nullable=True)
    iso: Mapped[float] = mapped_column(Integer, nullable=True)
    exposure_time: Mapped[float] = mapped_column(Integer, nullable=True)
    aperture: Mapped[float] = mapped_column(Integer, nullable=True)
    shutter_speed: Mapped[float] = mapped_column(Integer, nullable=True)
    latitude: Mapped[float] = mapped_column(Integer, nullable=True)
    longitude: Mapped[float] = mapped_column(Integer, nullable=True)

    # Relación con User
    user: Mapped["UsersDatabaseModel"] = relationship(back_populates="photos")

    # Relación N:N con los albums usando la tabla importada
    albums: Mapped[list["AlbumDatabaseModel"]] = relationship(
        secondary=album_photos, 
        back_populates="photos"
    )