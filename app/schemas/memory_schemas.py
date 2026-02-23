from uuid import UUID
from typing import List
from datetime import date
from pydantic import BaseModel, ConfigDict

from app.schemas.photos_schemas import PhotoResponseList

class PhotosYear(BaseModel):
    """
    Modelo que contiene las fotos de un día como hoy para un año en concreto.

    Args:
        id (UUID): ID de la consulta.
        date (date): Fecha del día (para validación, debe ser igual al día de la consulta, pero sin el año).
        year (int): Año de las fotos.
        photos (PhotoResponseList): Lista de fotos obtenidas en la consulta.
    """
    id: UUID
    date: date
    year: int
    photos: PhotoResponseList

    model_config = ConfigDict(
        from_attributes=True,
        json_schema_extra={
            "examples": [
                            {
                                "id": "xxxx-xxxx-xxxx-xxxx",
                                "year": 2023,
                                "today": "2023-01-01T00:00:00",
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
                                                    "is_deleted": False,
                                                    "deleted_at": None,
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


class PhotosYearList(BaseModel):
    """
    Modelo que contiene todas las fotos de los últimos años.

    Args:
        user_id (UUID): ID del usuario para el que se obtuvieron las fotos.
        years_count (int): Número de años en los que se obtuvieron fotos de la DB.
        photos_years_count (int): Número total de fotos obtenidas en la consulta.
        years (List[PhotosYear]): Lista de años con sus fotos.
    """
    user_id: UUID
    years_count: int
    photos_years_count: int
    years: List[PhotosYear]

class MemoriesOfDay(BaseModel):
    """
    Lista de recuerdos de todos los usuarios para un día concreto

    Args:
        user_ids (List[UUID]): Lista de usuarios para lo que se realizó la consulta
        user_count (int): Conteo de usuarios para los que se realizó la consulta.
        date (date): Fecha del día (para validación, debe ser igual al día de la consulta, pero sin el año).
        photos (List[PhotoResponseList]): Lista de PhotoResponseList con la metadata de cada una.
    """
    user_ids: List[UUID]
    user_count: int
    date: date
    photos: List[PhotoResponseList]