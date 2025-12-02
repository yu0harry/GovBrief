"""
Core 패키지
미들웨어, 예외, 에러 핸들러 등 핵심 기능
"""
from APP.core.middleware import (
    LoggingMiddleware,
    RateLimitMiddleware,
    RequestIDMiddleware,
    SecurityHeadersMiddleware,
)

from APP.core.exceptions import (
    APIException,
    DocumentNotFoundException,
    DocumentAlreadyProcessingException,
    InvalidFileTypeException,
    FileSizeExceededException,
    AnalysisFailedException,
    ParsingFailedException,
    RateLimitExceededException,
    UnauthorizedException,
    ForbiddenException,
    ValidationException,
    ExternalAPIException,
    ServiceUnavailableException,
)

from APP.core.error_handler import (
    register_exception_handlers,
    init_sentry,
)

__all__ = [
    # Middleware
    "LoggingMiddleware",
    "RateLimitMiddleware",
    "RequestIDMiddleware",
    "SecurityHeadersMiddleware",
    
    # Exceptions
    "APIException",
    "DocumentNotFoundException",
    "DocumentAlreadyProcessingException",
    "InvalidFileTypeException",
    "FileSizeExceededException",
    "AnalysisFailedException",
    "ParsingFailedException",
    "RateLimitExceededException",
    "UnauthorizedException",
    "ForbiddenException",
    "ValidationException",
    "ExternalAPIException",
    "ServiceUnavailableException",
    
    # Error Handler
    "register_exception_handlers",
    "init_sentry",
]