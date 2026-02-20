from uuid import UUID
from pathlib import Path
from typing import Optional
from datetime import datetime
from pydantic import BaseModel, Field, ConfigDict

class UserStorage(BaseModel):
    """
    Modelo de respuesta para el almacenamiento de un usuario.

    Args:
        user_id (UUID): ID del usuario.
        storage_path (Path): Ruta del directorio de almacenamiento.
        count_files (int): Número de archivos en el directorio de almacenamiento.
        storage_bytes_size (Optional[int]): Tamaño del almacenamiento en bytes.
    """
    id: UUID = Field(..., description="ID del almacenamiento")
    user_id: UUID = Field(..., description="ID del usuario")
    storage_path: Path = Field(..., description="Ruta del directorio de almacenamiento")
    count_files: int = Field(..., description="Número de archivos en el directorio de almacenamiento")
    storage_bytes_size: Optional[int] = Field(..., description="Tamaño del almacenamiento en bytes")
    created_at: Optional[datetime] = Field(..., description="Fecha de creación del almacenamiento")

    model_config = ConfigDict(
        from_attributes=True,
        json_schema_extra={
            "examples": [
                {
                    "id": "xxxx-xxxx-xxxx-xxxx",
                    "user_id": "xxxx-xxxx-xxxx-xxxx",
                    "storage_path": "/path/to/storage",
                    "count_files": 10,
                    "storage_bytes_size": 1000000,
                    "created_at": "2023-01-01T00:00:00"
                }
            ]
        }
    )