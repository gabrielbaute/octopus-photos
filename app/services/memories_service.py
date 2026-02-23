"""
Módulo de servicio para obtener fotos de recuerdos
"""
import logging
from pytz import timezone
from uuid import UUID, uuid4
from sqlalchemy.orm import Session
from datetime import datetime, timedelta, date
from apscheduler.schedulers.background import BackgroundScheduler

from app.settings import Settings
from app.errors import OctopusError
from app.services.photos_service import PhotoService
from app.controllers import PhotoController, UserController
from app.schemas import PhotosYear, PhotosYearList, MemoriesOfDay, PhotoResponseList

class MemoriesService:
    def __init__(self, settings: Settings, session: Session):
        self.logger = logging.getLogger(self.__class__.__name__)
        self.settings = settings
        self.photo_controller = PhotoController(session=session)
        self.user_controller = UserController(session=session)
        self.photo_service = PhotoService(session=session)
        self.scheduler = BackgroundScheduler(timezone=timezone(settings.TIMEZONE))

    def get_user_memories(self, user_id: UUID) -> PhotosYearList:
        """
        Obtiene los recuerdos de un usuario para el día de hoy.

        Args:
            user_id (UUID): ID del usuario.

        Returns:
            PhotosYearList: Lista de objetos de PhotosYear ordenados por año.
        """
        today = date.today()
        # 1. Obtenemos el PhotoResponseList desde el controlador
        photo_response_list = self.photo_controller.get_photos_this_day(user_id, today)
        
        # 2. Agrupamos por año usando los objetos PhotoResponse
        memories_by_year = {}
        for p in photo_response_list.photos:
            # Aseguramos que date_taken existe para agrupar, de lo contrario usamos storage_date
            photo_date = p.date_taken or p.storage_date
            year = photo_date.year
            
            if year not in memories_by_year:
                memories_by_year[year] = []
            memories_by_year[year].append(p)

        # 3. Construimos la lista de PhotosYear
        years_list = []
        for year, photos in memories_by_year.items():
            years_list.append(PhotosYear(
                id=uuid4(),
                date=today,
                year=year,
                photos=PhotoResponseList(count=len(photos), photos=photos)
            ))

        # 4. Retornamos el esquema final (Usando .count del objeto original)
        return PhotosYearList(
            user_id=user_id,
            years_count=len(years_list),
            photos_years_count=photo_response_list.count,
            years=sorted(years_list, key=lambda x: x.year, reverse=True)
        )

    def get_all_users_memories(self) -> MemoriesOfDay:
        """
        Obtiene todos los recuerdos/fotos de todos los usuarios desde la mas antigua hasta la actual, para un día como hoy.

        Returns:
            MemoriesOfDay: Lista de objetos de MemoriesOfDay ordenados por usuario.
        """
        self.logger.info("Iniciando consulta de Recuerdos de Fotos de todos los usuarios.")
        users = self.user_controller.get_all_users()
        if not users:
            raise OctopusError(
                message="Error al realizar la consulta.",
                details="No se encontraron usuarios."
            )
        
        user_photos = []

        for user in users.users:
            user_photos.append(self.get_user_memories(user.id))
        
        memories_of_day = MemoriesOfDay(
            user_ids=[user.id for user in users.users],
            user_count=len(users.users),
            date=date.today(),
            photos=user_photos
        )
        return memories_of_day
    
    def scheduler_jobs(self) -> None:
        """
        Programa una consulta diaria de todos los usuarios.
        """
        self.scheduler.add_job(
            self.get_all_users_memories,
            trigger="cron",
            hour=8)

    def start(self) -> None:
        """
        Inicia el servicio de scheduler.
        """
        self.logger.info("Iniciando scheduler...")
        self.scheduler_jobs()
        self.scheduler.start()