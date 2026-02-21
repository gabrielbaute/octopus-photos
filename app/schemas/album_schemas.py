from uuid import UUID
from datetime import datetime
from typing import Optional, List
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

    model_config = ConfigDict(
        from_attributes=True,
        json_schema_extra={
            "examples":[
                {
                    "id": "xxxx-xxxx-xxxx-xxxx",
                    "user_id": "xxxx-xxxx-xxxx-xxxx",
                    "name": "Mi álbum",
                    "description": "Descripción del álbum",
                    "created_at": "2023-01-01T00:00:00",
                    "photos": {
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
                }
            ]
        }
    )

class AlbumCreate(BaseModel):
    """
    Modelo para crear un álbum.

    Args:
        user_id (UUID): ID del propietario.
        name (str): Nombre del album
        description (Optional[str]): Descripción del álbum.
        photos Optional[PhotoResponseList]: Lista de fotos en el álbum en caso de crearlo a partir de una lsita.
    """
    user_id: UUID
    name: str
    description: Optional[str] = None
    photos: List[UUID] = []