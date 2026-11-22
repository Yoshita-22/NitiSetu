class AppException(Exception):
    """Base application exception."""

    def __init__(self, message: str, status_code: int = 500):
        super().__init__(message)
        self.message = message
        self.status_code = status_code


class NotFoundError(AppException):
    """Raised when a requested resource is not found."""

    def __init__(self, message: str = "Resource not found"):
        super().__init__(message, status_code=404)


class ValidationError(AppException):
    """Raised when input validation fails."""

    def __init__(self, message: str = "Validation failed"):
        super().__init__(message, status_code=422)


class UpstreamAPIError(AppException):
    """Raised when an external API call fails."""

    def __init__(self, message: str = "Upstream API error"):
        super().__init__(message, status_code=502)


class FileProcessingError(AppException):
    """Raised when document processing fails."""

    def __init__(self, message: str = "Document processing failed"):
        super().__init__(message, status_code=400)


class AuthorizationError(AppException):
    """Raised when an unauthorized resource access is attempted."""

    def __init__(self, message: str = "Access unauthorized"):
        super().__init__(message, status_code=403)
