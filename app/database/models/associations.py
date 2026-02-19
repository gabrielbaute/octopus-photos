"""
Modulo de tablas asociativas para relaciones Many-to-Many
"""
from sqlalchemy import Column, ForeignKey, Table
from app.database.db_base import Base

# Tabla intermedia para la relación N:N entre Photos y Albums
album_photos = Table(
    "album_photos",
    Base.metadata,
    Column(
        "photo_id", 
        ForeignKey("photos.id", ondelete="CASCADE"), 
        primary_key=True
    ),
    Column(
        "album_id", 
        ForeignKey("albums.id", ondelete="CASCADE"), 
        primary_key=True
    )
)