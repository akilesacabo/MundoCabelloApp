class AppError(Exception):
    """Base application error. Mapped to an HTTP response by a handler in main.py."""

    status_code = 500
    detail = "Internal server error"

    def __init__(self, detail: str | None = None) -> None:
        super().__init__(detail or self.detail)
        if detail is not None:
            self.detail = detail


class NotFound(AppError):
    status_code = 404
    detail = "Resource not found"


class PermissionDenied(AppError):
    status_code = 403
    detail = "Permission denied"


class Conflict(AppError):
    status_code = 409
    detail = "Resource conflict"


class BadRequest(AppError):
    status_code = 400
    detail = "Bad request"
