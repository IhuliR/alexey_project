from collections import defaultdict

from fastapi import Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse


class ApiValidationError(Exception):
    def __init__(self, errors: dict[str, str | list[str]]) -> None:
        self.errors = {
            field: messages if isinstance(messages, list) else [messages]
            for field, messages in errors.items()
        }


async def api_validation_error_handler(
    request: Request,
    exc: ApiValidationError,
) -> JSONResponse:
    return JSONResponse(status_code=400, content=exc.errors)


async def request_validation_error_handler(
    request: Request,
    exc: RequestValidationError,
) -> JSONResponse:
    errors: dict[str, list[str]] = defaultdict(list)
    for error in exc.errors():
        field = str(error['loc'][-1])
        message = error['msg']
        if error['type'] == 'missing':
            message = 'This field is required.'
        errors[field].append(message)
    return JSONResponse(status_code=400, content=errors)
