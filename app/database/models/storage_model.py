import uuid
from datetime import datetime
from typing import TYPE_CHECKING
from sqlalchemy import Integer, DateTime, String, ForeignKey, BigInteger
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database.db_base import Base
if TYPE_CHECKING:
    from app.database.models.users_model import UsersDatabaseModel

class UserStorageDatabaseModel(Base):
    """Modelo de tabla para estadísticas de almacenamiento."""
    __tablename__ = "user_storages"

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    user_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("users.id"), unique=True)
    storage_path: Mapped[str] = mapped_column(String, nullable=False)
    count_files: Mapped[int] = mapped_column(Integer, default=0)
    storage_bytes_size: Mapped[int] = mapped_column(BigInteger, default=0)  # BigInt para bytes
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

    # Relación con User
    user: Mapped["UsersDatabaseModel"] = relationship(back_populates="storage")