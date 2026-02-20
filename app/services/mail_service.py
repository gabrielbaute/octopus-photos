import logging
from typing import Dict, Any

from app.mail import SMTPClient, MailBuilder
from app.settings import Settings

class MailService:
    """Orquestador de alto nivel para el envío de correos."""

    def __init__(self, client: SMTPClient, builder: MailBuilder, settings: Settings) -> None:
        """Inyecta las dependencias necesarias.

        Args:
            client (SMTPClient): Gestor de la conexión.
            builder (MailBuilder): Constructor de mensajes basado en Jinja2.
            settings (AppSettings): Configuración global.
        """
        self.client = client
        self.builder = builder
        self.settings = settings
        self.base_url = settings.APP_URL
        self.logger = logging.getLogger(self.__class__.__name__)

    def send_templated_email(
            self, 
            recipient: str, 
            subject: str, 
            template: str, 
            context: Dict[str, Any]
        ) -> None:
        """Renderiza una plantilla y la envía.

        Args:
            recipient (str): Email destino.
            subject (str): Asunto del correo.
            template (str): Nombre del archivo .html en /templates.
            context (Dict[str, Any]): Variables para la plantilla.
        """
        # 1. Construir el mensaje
        message = self.builder.create_message(
            sender=self.settings.MAIL_USERNAME,
            recipient=recipient,
            subject=subject,
            template_name=template,
            context=context
        )
        self.logger.info(f"Sending email to {recipient}. Subject: {subject}.")
        # 2. Enviar usando el context manager del cliente
        with self.client as active_client:
            active_client.send_mail(message)
