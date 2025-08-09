# errors.py - Manejadores de excepción personalizados

from fastapi import FastAPI, HTTPException
from fastapi.responses import JSONResponse


def register_exception_handlers(app: FastAPI) -> None:
    @app.exception_handler(HTTPException)
    async def http_exception_handler(request, exc: HTTPException):
        return JSONResponse(
            status_code=exc.status_code,
            content={"detail": exc.detail}
        )

    @app.exception_handler(Exception)
    async def generic_exception_handler(request, exc: Exception):
        # Loguear error aquí si es necesario
        return JSONResponse(
            status_code=500,
            content={"detail": "Internal server error"}
        )