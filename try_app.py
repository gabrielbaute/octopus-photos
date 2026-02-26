import os
import sys
import uvicorn
import logging
import threading
import webbrowser
from PIL import Image
from pystray import Icon, Menu, MenuItem

from app.api.app_factory import create_app
from app.database.db_config import init_db
from app.settings import settings, OctopusLogger
from app.api.errors import register_error_handlers

class OctopusTrayApp:
    def __init__(self) -> None:
        """Inicializa la aplicación."""
        OctopusLogger.setup_logging(level=settings.API_LOG_LEVEL)
        init_db(settings=settings)
        self.app = create_app(settings=settings)
        self.logger = logging.getLogger(self.__class__.__name__)
        register_error_handlers(self.app)
        
        self.server_thread: threading.Thread | None = None
        self.icon = None

    def _run_server(self) -> None:
        """Ejecuta el servidor Uvicorn (Bloqueante, debe ir en un hilo)."""
        try:
            self.logger.info("Iniciando servidor Uvicorn...")
            uvicorn.run(
                self.app,
                host=settings.API_HOST,
                port=settings.API_PORT,
                log_config=None if getattr(sys, 'frozen', False) else uvicorn.config.LOGGING_CONFIG,
                log_level=settings.API_LOG_LEVEL,
                reload=False
            )
        except Exception as e:
            self.logger.error(f"Uvicorn Error: {str(e)}")
            with open(settings.LOGS_PATH / "critical_error.log", "a") as f:
                f.write(f"Uvicorn Error: {str(e)}\n")

    def _open_logs(self) -> None:
        """Abre el archivo de logs con el editor predeterminado."""
        log_file = settings.LOGS_PATH / f"{settings.APP_NAME}.log"
        if log_file.exists():
            os.startfile(log_file) # Solo Windows

    def _open_config(self) -> None:
        """Abre el archivo .env para edición."""
        from app.utils.get_environment_path import get_env_paths
        env_path = get_env_paths()[0] # La del usuario
        if env_path.exists():
            os.startfile(env_path)

    def _restart_app(self) -> None:
        """Reinicia la aplicación completa."""
        if self.icon:
            self.icon.stop()
        # Reinicia el proceso actual
        os.execl(sys.executable, sys.executable, *sys.argv)

    def _quit_app(self) -> None:
        if self.icon:
            self.icon.stop()
        os._exit(0)

    def _open_browser(self) -> None:
        """Abre la interfaz de usuario en el navegador."""
        webbrowser.open(f"http://localhost:{settings.API_PORT}", default=True)

    def _quit_app(self) -> None:
        """Detiene el icono y cierra la aplicación."""
        if self.icon:
            self.icon.stop()
        sys.exit(0)

    def run(self) -> None:
        """Ejecuta la aplicación."""
        server_thread = threading.Thread(target=self._run_server, daemon=True)
        server_thread.start()

        icon_img = Image.open(settings.STATIC_PATH / "favicon.png")
        
        menu = Menu(
            MenuItem("Abrir Octopus Photos", lambda: webbrowser.open(f"http://localhost:{settings.API_PORT}"), default=True),
            MenuItem("Editar Configuración (.env)", self._open_config),
            MenuItem("Ver Logs", self._open_logs),
            Menu.SEPARATOR,
            MenuItem("Reiniciar Aplicación", self._restart_app),
            MenuItem("Salir", self._quit_app)
        )
        
        # 3. Iniciar el bucle del icono (Bloqueante en el hilo principal)
        self.icon = Icon("octopus_photos", icon_img, f"{settings.APP_NAME}", menu)
        self.logger.info(f"Servidor iniciado en http://{settings.API_HOST}:{settings.API_PORT}")
        self.icon.run()

if __name__ == "__main__":
    tray_app = OctopusTrayApp()
    tray_app.run()