from enum import StrEnum
from typing import List, Dict

class UserRole(StrEnum):
    ADMIN = "ADMIN"
    USER = "USER"
    GUEST = "GUEST"

    def __str__(self) -> str:
        return self.value
    
    def __repr__(self) -> str:
        return self.value
    
    @staticmethod
    def get_roles_list() -> List[str]:
        return [role.value for role in UserRole]
    
    @staticmethod
    def get_roles_map() -> Dict[str, "UserRole"]:
        return {
            "ADMIN": UserRole.ADMIN,
            "USER": UserRole.USER,
            "GUEST": UserRole.GUEST
        }