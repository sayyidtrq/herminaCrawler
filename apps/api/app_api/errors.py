from __future__ import annotations

from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse


def _error_response(status_code: int, code: str, message: str) -> JSONResponse:
    return JSONResponse(
        status_code=status_code,
        content={
            "error": {
                "code": code,
                "message": message,
            }
        },
    )


def register_exception_handlers(app: FastAPI) -> None:
    @app.exception_handler(ValueError)
    async def value_error_handler(
        request: Request, exc: ValueError
    ) -> JSONResponse:
        message = str(exc) or "Invalid request."
        code = message.lower().replace(" ", "_").replace(".", "")
        status_code = 404 if "not found" in message.lower() else 400
        return _error_response(status_code, code, message)

