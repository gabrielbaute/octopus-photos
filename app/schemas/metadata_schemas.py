from datetime import datetime
from typing import Optional
from pydantic import BaseModel, Field, ConfigDict

class PhotoMetadata(BaseModel):
    """
    Modelo de respuesta para la metadata de una foto.

    Args:
        date_taken (datetime): Fecha de la foto.
        camera_make (str): Marca de la cámara.
        camera_model (str): Modelo de la cámara.
        focal_length (float): Longitud focal de la cámara.
        iso (float): ISO de la cámara.
        exposure_time (float): Tiempo de exposición de la cámara.
        aperture (float): Apertura de la cámara.
        shutter_speed (float): Velocidad de apertura de la cámara.
        latitude (float): Latitud de la foto.
        longitude (float): Longitud de la foto.
    """
    date_taken: Optional[datetime] = None
    camera_make: Optional[str] = None
    camera_model: Optional[str] = None
    focal_length: Optional[float] = None
    iso: Optional[float] = None
    exposure_time: Optional[float] = None
    aperture: Optional[float] = None
    shutter_speed: Optional[float] = None
    latitude: Optional[float] = None
    longitude: Optional[float] = None

    model_config = ConfigDict(from_attributes=True)