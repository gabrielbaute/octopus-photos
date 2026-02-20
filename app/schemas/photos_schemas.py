from uuid import UUID, uuid4
from datetime import datetime
from typing import List, Optional
from pydantic import BaseModel, Field, ConfigDict, computed_field

from app.schemas.metadata_schemas import PhotoMetadata

class PhotoBase(BaseModel):
    """Atributos base para una fotografía."""
    description: Optional[str] = Field(None, description="Descripción de la foto")
    tags: Optional[List[str]] = Field(None, description="Lista de etiquetas")

class PhotoCreate(PhotoBase, PhotoMetadata):
    """
    Modelo para la creación (Upload). 
    Los campos de sistema (id, storage_path) no se piden al cliente.
    """
    file_name: str

class PhotoUpdate(BaseModel):
    """Esquema para actualizar metadatos editables por el usuario."""
    description: Optional[str] = Field(None, max_length=500)
    tags: Optional[List[str]] = Field(None)

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "description": "Una descripción nueva para mi foto de vacaciones",
                "tags": ["verano", "playa", "2026"]
            }
        }
    )

class PhotoResponse(PhotoBase, PhotoMetadata):
    """
    Modelo de respuesta completo. 
    Hereda tanto de PhotoBase como de PhotoMetadata para aplanar la respuesta 
    y que coincida con los atributos del modelo de SQLAlchemy.
    """
    id: UUID
    user_id: UUID
    storage_date: datetime
    storage_path: str
    file_name: str
    
    model_config = ConfigDict(
        from_attributes=True,
        json_schema_extra={
            "examples": [
                {
                    "id": "xxxx-xxxx-xxxx-xxxx",
                    "user_id": "xxxx-xxxx-xxxx-xxxx",
                    "storage_date": "2023-01-01T00:00:00",
                    "storage_path": "path/to/file",
                    "file_name": "photo.jpg",
                    "description": "Descripción de la foto",
                    "tags": ["tag1", "tag2"],
                    "date_taken": "2023-01-01T00:00:00",
                    "camera_make": "Canon",
                    "camera_model": "Canon EOS 5D Mark IV",
                    "focal_length": 24.1,
                    "iso": 100,
                    "exposure_time": 1/100,
                    "aperture": 2.8,
                    "shutter_speed": 1,
                    "latitude": 40.7128,
                    "longitude": -74.0060
                }
            ]
        }
    )

    @computed_field
    @property
    def url_original(self) -> str:
        """URL dinámica para descargar el archivo original."""
        return f"/api/v1/photos/{self.id}/download"

    @computed_field
    @property
    def url_thumbnail(self) -> str:
        """URL dinámica para obtener la miniatura de previsualización."""
        return f"/api/v1/photos/{self.id}/thumbnail"

class PhotoResponseList(BaseModel):
    """Contenedor para respuestas paginadas o listados."""
    count: int
    photos: List[PhotoResponse]
    
    model_config = ConfigDict(
        from_attributes=True,
        json_schema_extra={
            "examples": [
                {
                    "count": 10,
                    "photos": [
                        {
                            "id": "xxxx-xxxx-xxxx-xxxx",
                            "user_id": "xxxx-xxxx-xxxx-xxxx",
                            "storage_date": "2023-01-01T00:00:00",
                            "storage_path": "path/to/file",
                            "file_name": "photo.jpg",
                            "description": "Descripción de la foto",
                            "tags": ["tag1", "tag2"],
                            "date_taken": "2023-01-01T00:00:00",
                            "camera_make": "Canon",
                            "camera_model": "Canon EOS 5D Mark IV",
                            "focal_length": 24.1,
                            "iso": 100,
                            "exposure_time": 1/100,
                            "aperture": 2.8,
                            "shutter_speed": 1,
                            "latitude": 40.7128,
                            "longitude": -74.0060
                        }
                    ]
                }
            ]
        }
    )