from datetime import datetime, timezone

def get_now() -> datetime:
    """Retorna el timestamp actual en UTC con información de zona horaria."""
    return datetime.now(timezone.utc)