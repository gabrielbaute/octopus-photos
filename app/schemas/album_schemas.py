from uuid import UUID
from datetime import datetime
from typing import Optional
from pydantic import BaseModel, ConfigDict

from app.schemas.photos_schemas import PhotoResponseList

class AlbumResponse(BaseModel):
    """
    Modelo de respuesta para un álbum.

    Args:
        id (UUID): ID del álbum.
        user_id (UUID): ID del propietario.
        name (str): Nombre del álbum.
        description (Optional[str]): Descripción del álbum.
        created_at (datetime): Fecha de creación.
        photos (PhotoResponseList): Lista de fotos en el álbum.
    """
    id: UUID
    user_id: UUID
    name: str
    description: Optional[str]
    created_at: datetime
    photos: Optional[PhotoResponseList]

    model_config = ConfigDict(from_attributes=True)