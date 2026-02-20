import smtplib
import logging
import ssl
from typing import Optional
from app.settings.app_settings import Settings

class SMTPClient:
    """Maneja la conexión y autenticación con el servidor SMTP."""

    def __init__(self, settings: Settings) -> None:
        """
        Inicializa los parámetros de conexión.

        Args:
            settings (Settings): Objeto de configuración con los parámetros del servidor.
        """
        self.settings = settings
        self.server: Optional[smtplib.SMTP] = None
        self._context = ssl.create_default_context()
        self.logger = logging.getLogger(self.__class__.__name__)

    def __enter__(self) -> "SMTPClient":
        """
        Permite el uso de 'with SMTPClient(...) as client'.
        """
        self.connect()
        return self

    def __exit__(self, exc_type, exc_val, exc_tb) -> None:
        """
        Asegura el cierre de la conexión al salir del bloque 'with'.
        """
        self.logger.debug("Finalizando conexión SMTP")
        self.disconnect()

    def connect(self) -> None:
        """
        Establece la conexión física y lógica con el servidor SMTP.
        
        Aquí es donde 'self.server' deja de ser None para convertirse en el objeto de conexión.
        """
        try:
            if self.settings.MAIL_USE_SSL:
                # Conexión implícita SSL (Puerto 465)
                self.server = smtplib.SMTP_SSL(
                    self.settings.MAIL_HOST, 
                    self.settings.MAIL_PORT, 
                    context=self._context
                )
            else:
                # Conexión estándar o STARTTLS (Puerto 587 o 25)
                self.server = smtplib.SMTP(
                    self.settings.MAIL_HOST, 
                    self.settings.MAIL_PORT
                )
                if self.settings.MAIL_USE_TLS:
                    self.server.starttls(context=self._context)
            
            # Autenticación
            if self.settings.MAIL_USERNAME and self.settings.MAIL_PASSWORD:
                self.server.login(
                    self.settings.MAIL_USERNAME, 
                    self.settings.MAIL_PASSWORD
                )
        except smtplib.SMTPException as e:
            self.logger.error(f"Error al conectar al servidor SMTP: {e}")
            raise

    def send_mail(self, message) -> None:
        """
        Envía un mensaje ya construido.
        
        Args:
            message: Objeto email.message.Message (o MIMEMultipart).
        """
        try:
            if not self.server:
                raise ConnectionError("El servidor no está conectado. Llama a connect() primero.")
            self.logger.debug(f"Enviando correo a {message['To']}")
            self.server.send_message(message)
        except smtplib.SMTPException as e:
            self.logger.error(f"Error al enviar el correo: {e}")
            raise

    def disconnect(self) -> None:
        """Cierra la conexión de forma segura."""
        if self.server:
            self.logger.debug("Cerrando conexión SMTP")
            self.server.quit()
            self.server = None  # Lo devolvemos a None tras cerrar el socket