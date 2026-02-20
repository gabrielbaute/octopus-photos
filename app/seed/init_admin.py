"""
Módulo seed para cargar admin inicial
"""
from app.enums import UserRole
from app.database.db_config import SessionLocal
from app.services.users_service import UserService
from app.schemas import UserCreate

def create_initial_admin() -> bool:
    """
    Crea el admin inicial gestionando correctamente el ciclo de vida de la sesión.
    """
    # 1. Instanciar la sesión real llamando a la fábrica
    db = SessionLocal()
    
    # 2. Inyectar la sesión en el servicio
    user_service = UserService(session=db)

    new_admin = UserCreate(
        username="admin",
        email="admin@admin.com",
        password="admin2026",
        role=UserRole.ADMIN,
    )

    print(f"Preparando nuevo admin: {new_admin.model_dump_json(indent=2)}")
    
    try:
        # 3. Ejecutar el registro
        admin = user_service.register_user(user_data=new_admin)
        print(f"✅ Admin creado exitosamente: {admin.username}")
        return True
    except Exception as e:
        print(f"❌ Error al crear el admin: {e}")
        return False
    finally:
        # 4. RIGOR: Cerrar la sesión siempre, pase lo que pase
        db.close()
    
if __name__ == "__main__":
    create_initial_admin()