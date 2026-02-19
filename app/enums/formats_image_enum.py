from enum import StrEnum
from typing import List, Dict

class FormatImage(StrEnum):
    JPG = "JPG"
    JPEG = "JPEG"
    PNG = "PNG"
    WEBP = "WEBP"
    GIF = "GIF"

    def __str__(self) -> str:
        return self.value
    
    def __repr__(self) -> str:
        return self.value
    
    @staticmethod
    def get_formats_list() -> List[str]:
        return [fmt.value for fmt in FormatImage]
    
    @staticmethod
    def get_formats_map() -> Dict[str, "FormatImage"]:
        return {
            "JPG": FormatImage.JPG,
            "JPEG": FormatImage.JPEG,
            "PNG": FormatImage.PNG,
            "WEBP": FormatImage.WEBP,
            "GIF": FormatImage.GIF
        }
