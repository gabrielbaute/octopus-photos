import logging
from pathlib import Path
from typing import Dict, Any
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from jinja2 import Environment, FileSystemLoader

class MailBuilder:
    """Clase para construir mensajes MIME utilizando plantillas Jinja2."""

    def __init__(self, template_dir: Path):
        """
        Configura el entorno de plantillas.

        Args:
            template_dir (Path): Ruta al directorio de plantillas.
        """
        self.logger = logging.getLogger(self.__class__.__name__)
        self.env = Environment(loader=FileSystemLoader(str(template_dir)))

    def create_message(
            self, 
            sender: str, 
            recipient: str, 
            subject: str, 
            template_name: str, 
            context: Dict[str, Any]
        ) -> MIMEMultipart:
        """
        Crea un objeto MIMEMultipart renderizando una plantilla.

        Args:
            sender (str): Email del remitente.
            recipient (str): Email del destinatario.
            subject (str): Asunto del correo.
            template_name (str): Nombre del archivo de plantilla.
            context (Dict[str, Any]): Datos para renderizar en la plantilla.

        Returns:
            MIMEMultipart: Objeto de mensaje listo para ser enviado.
        """
        self.logger.debug(f"Creando mensaje para {recipient} con asunto {subject}")
        try:
            message = MIMEMultipart("alternative")
            message["From"] = sender
            message["To"] = recipient
            message["Subject"] = subject

            template = self.env.get_template(template_name)
            html_content = template.render(context)
            
            message.attach(MIMEText(html_content, "html"))
            return message
        except Exception as e:
            self.logger.error(f"Error al construir el mensaje: {e}")
            raise