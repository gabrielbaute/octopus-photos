"""
Helper to load all the api routes.
"""

from fastapi import FastAPI

from app.api.routes import auth_router, user_router, photos_router, check_router


def include_routes(app: FastAPI, prefix: str):
    """Include all API routes in the FastAPI application.

    Args:
        app (FastAPI): The FastAPI application instance.
    """
    app.include_router(auth_router, prefix=prefix)
    app.include_router(user_router, prefix=prefix)
    app.include_router(photos_router, prefix=prefix)
    app.include_router(check_router, prefix=prefix)