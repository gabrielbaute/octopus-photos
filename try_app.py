import sys
import uvicorn
import threading
import webbrowser
from PIL import Image
from typing import Optional
from pystray import Icon, Menu, MenuItem

from app.api.app_factory import create_app
from app.database.db_config import init_db
from app.settings import settings, OctopusLogger
from app.api.errors import register_error_handlers

class OctopusTrayApp:
    def __init__(self) -> None:
        # Configuración inicial (tu lógica existente)
        OctopusLogger.setup_logging(level=settings.API_LOG_LEVEL)
        init_db(settings=settings)
        self.app = create_app(settings=settings)
        register_error_handlers(self.app)
        
        self.server_thread: threading.Thread | None = None
        self.icon = None

    def _run_server(self) -> None:
        """Ejecuta el servidor Uvicorn (Bloqueante, debe ir en un hilo)."""
        uvicorn.run(
            self.app,
            host=settings.API_HOST,
            port=settings.API_PORT,
            log_level=settings.API_LOG_LEVEL,
            reload=False
        )

    def _open_browser(self) -> None:
        """Abre la interfaz de usuario en el navegador."""
        webbrowser.open(f"http://localhost:{settings.API_PORT}")

    def _quit_app(self) -> None:
        """Detiene el icono y cierra la aplicación."""
        if self.icon:
            self.icon.stop()
        sys.exit(0)

    def _restart_server(self) -> None:
        """Reinicia el servidor Uvicorn."""
        if self.server_thread:
            self.server_thread.join()
        self._run_server()

    def run(self) -> None:
        """Lanza la aplicación completa."""
        # 1. Iniciar servidor en segundo plano
        self.server_thread = threading.Thread(target=self._run_server, daemon=True)
        self.server_thread.start()

        # 2. Configurar el icono de la barra de tareas
        # Usamos el favicon de tu carpeta static
        icon_img = Image.open(settings.STATIC_PATH / "favicon.png")
        
        menu = Menu(
            MenuItem("Abrir Octopus Photos", self._open_browser, default=True),
            MenuItem("Reiniciar Servidor", self._restart_server),
            MenuItem("Detener Servidor", self._quit_app)
        )
        
        self.icon = Icon(
            "octopus_photos", 
            icon_img, 
            f"{settings.APP_NAME} (v{settings.APP_VERSION})", 
            menu
        )
        
        # 3. Iniciar el bucle del icono (Bloqueante en el hilo principal)
        print(f"Servidor iniciado en http://{settings.API_HOST}:{settings.API_PORT}")
        self.icon.run()

if __name__ == "__main__":
    tray_app = OctopusTrayApp()
    tray_app.run()