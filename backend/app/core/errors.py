from fastapi import HTTPException, status


class AppError(Exception):
    """Base for typed application errors mapped to HTTP by the API layer."""

    http_status: int = status.HTTP_500_INTERNAL_SERVER_ERROR
    code: str = "internal_error"

    def __init__(self, message: str, *, code: str | None = None) -> None:
        super().__init__(message)
        self.message = message
        if code is not None:
            self.code = code


class NotFoundError(AppError):
    http_status = status.HTTP_404_NOT_FOUND
    code = "not_found"


class ConflictError(AppError):
    http_status = status.HTTP_409_CONFLICT
    code = "conflict"


class AuthError(AppError):
    http_status = status.HTTP_401_UNAUTHORIZED
    code = "unauthorized"


class ForbiddenError(AppError):
    http_status = status.HTTP_403_FORBIDDEN
    code = "forbidden"


class ValidationError(AppError):
    http_status = status.HTTP_422_UNPROCESSABLE_ENTITY
    code = "validation_error"


class RateLimitError(AppError):
    http_status = status.HTTP_429_TOO_MANY_REQUESTS
    code = "rate_limit"


def to_http(exc: AppError) -> HTTPException:
    return HTTPException(
        status_code=exc.http_status,
        detail={"code": exc.code, "message": exc.message},
    )
