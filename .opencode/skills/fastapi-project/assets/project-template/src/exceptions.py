class AppError(Exception):
    """Base application error. Mapped to an HTTP response by a handler in main.py."""

    status_code = 500
    detail = "Internal server error"


class NotFound(AppError):
    status_code = 404
    detail = "Resource not found"


class PermissionDenied(AppError):
    status_code = 403
    detail = "Permission denied"
