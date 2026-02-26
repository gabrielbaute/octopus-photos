"""
Módulo para gestionar el servicio del cliente Flutter (JS/WASM)
"""
import mimetypes
from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from starlette.responses import FileResponse, JSONResponse

from app.settings import Settings

def setup_web_client(app: FastAPI, settings: Settings) -> None:
    """
    Configura los requerimientos para levantar el frontend de flutter
    
    Args:
        app (FastAPI): Instancia de la aplicación FastAPI.
        settings (Settings): Configuración de la aplicación.
    
    Returns:
        None
    """
    
    static_path = settings.STATIC_PATH
    
    # 1. Configuración de tipos MIME para WASM
    mimetypes.add_type('application/wasm', '.wasm')
    mimetypes.add_type('application/javascript', '.js')

    # 2. Middleware local para cabeceras de aislamiento (WASM)
    @app.middleware("http")
    async def add_wasm_headers(request, call_next):
        response = await call_next(request)
        if request.url.path.startswith("/api"):
            return response
        
        response.headers["Cross-Origin-Opener-Policy"] = "same-origin"
        response.headers["Cross-Origin-Embedder-Policy"] = "credentialless"
        return response

    # 3. Manejo de rutas SPA (Deep Linking)
    @app.exception_handler(404)
    async def spa_handler(request, exc):
        if request.url.path.startswith("/api"):
            return JSONResponse(status_code=404, content={"detail": "API Route Not Found"})
        
        index_path = static_path / "index.html"
        if index_path.exists():
            return FileResponse(index_path)
        
        return JSONResponse(
            status_code=404, 
            content={"detail": "Frontend assets not found. Run flutter build web."}
        )

    # 4. Montaje de archivos estáticos
    if static_path.exists():
        app.mount("/", StaticFiles(directory=str(static_path), html=True), name="static")