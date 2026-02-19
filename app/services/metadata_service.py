"""
Modulo de servicio de extración de metadata de las fotos
"""
import logging
import exifread
from pathlib import Path
from datetime import datetime
from typing import Optional, Any, Dict
from app.schemas.metadata_schemas import PhotoMetadata

class MetadataService:
    """Servicio para extraer y normalizar metadatos EXIF de imágenes."""

    def __init__(self):
        self.logger = logging.getLogger(self.__name__)

    def _convert_to_float(self, value: Any) -> Optional[float]:
        """
        Convierte fracciones EXIF (como '1/125') a float.

        Args:
            value (Any): valor a convertir en float.
        
        Returns:
            Optional[float]: valor convertido o None si falla.
        """
        try:
            if isinstance(value, list):
                value = value[0]
            if hasattr(value, 'num') and hasattr(value, 'den'):
                return float(value.num) / float(value.den)
            return float(str(value))
        except (ValueError, ZeroDivisionError, TypeError):
            return None

    def _parse_gps(self, tags: Dict[str, Any]) -> tuple[Optional[float], Optional[float]]:
        """
        Convierte coordenadas GPS EXIF a grados decimales.
        
        Args:
            tags (Dict[str, Any]): Diccionario de metadatos EXIF.
        
        Returns:
            tuple[Optional[float], Optional[float]]: (latitud, longitud) o (None, None) si falla.
        """
        def _to_decimal(values: Any, reference: Any) -> Optional[float]:
            if not values or not reference:
                return None
            try:
                # Los valores vienen como [grados, minutos, segundos]
                d = self._convert_to_float(values.values[0])
                m = self._convert_to_float(values.values[1])
                s = self._convert_to_float(values.values[2])
                
                decimal = d + (m / 60.0) + (s / 3600.0)
                # Referencia S (Sur) o W (Oeste) implica valor negativo
                if str(reference.values) in ['S', 'W']:
                    decimal = -decimal
                return decimal
            except Exception:
                return None

        lat = _to_decimal(tags.get('GPS GPSLatitude'), tags.get('GPS GPSLatitudeRef'))
        lon = _to_decimal(tags.get('GPS GPSLongitude'), tags.get('GPS GPSLongitudeRef'))
        return lat, lon

    def _parse_date(self, date_str: Any) -> Optional[datetime]:
        """
        Convierte el string de fecha EXIF (YYYY:MM:DD HH:MM:SS) a objeto datetime.

        Args:
            date_str (Any): String de fecha EXIF.
        
        Returns:
            Optional[datetime]: Objeto datetime o None si falla.
        """
        if not date_str:
            return None
        try:
            return datetime.strptime(str(date_str), '%Y:%M:%D %H:%M:%S')
        except ValueError:
            return None

    def extract_metadata(self, file_path: Path) -> Optional[PhotoMetadata]:
        """
        Extrae y normaliza la metadata de una foto.
        
        Args:
            file_path (Path): Ruta al archivo de imagen.
        
        Returns:
            Optional[PhotoMetadata]: Metadata extraída o None si falla.
        """
        try:
            with open(file_path, 'rb') as f:
                tags = exifread.process_file(f, details=False)
            
            if not tags:
                return None

            lat, lon = self._parse_gps(tags)

            # Normalización de etiquetas a tipos nativos de Python
            metadata = PhotoMetadata(
                date_taken=self._parse_date(tags.get('EXIF DateTimeOriginal')),
                camera_make=str(tags.get('Image Make')) if tags.get('Image Make') else None,
                camera_model=str(tags.get('Image Model')) if tags.get('Image Model') else None,
                focal_length=self._convert_to_float(tags.get('EXIF FocalLength')),
                iso=self._convert_to_float(tags.get('EXIF ISOSpeedRatings')),
                exposure_time=self._convert_to_float(tags.get('EXIF ExposureTime')),
                aperture=self._convert_to_float(tags.get('EXIF FNumber')),
                shutter_speed=self._convert_to_float(tags.get('EXIF ShutterSpeedValue')),
                latitude=lat,
                longitude=lon
            )
            return metadata

        except Exception as e:
            self.logger.error(f"Error procesando metadata de {file_path}: {e}")
            return None