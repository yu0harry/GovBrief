"""
커스텀 예외 정의
API에서 사용할 구조화된 예외 클래스들
"""
from typing import Any, Optional, Dict


class APIException(Exception):
    """
    API 커스텀 예외 기본 클래스
    
    모든 커스텀 예외는 이 클래스를 상속받아야 함
    """
    def __init__(
        self,
        status_code: int,
        detail: str,
        error_code: Optional[str] = None,
        headers: Optional[Dict[str, str]] = None
    ):
        self.status_code = status_code
        self.detail = detail
        self.error_code = error_code or self.__class__.__name__
        self.headers = headers or {}
        super().__init__(detail)


class DocumentNotFoundException(APIException):
    """문서를 찾을 수 없음"""
    def __init__(self, document_id: str):
        super().__init__(
            status_code=404,
            detail=f"문서를 찾을 수 없습니다: {document_id}",
            error_code="DOCUMENT_NOT_FOUND"
        )


class DocumentAlreadyProcessingException(APIException):
    """문서가 이미 처리 중"""
    def __init__(self, document_id: str):
        super().__init__(
            status_code=409,
            detail=f"문서가 이미 처리 중입니다: {document_id}",
            error_code="DOCUMENT_ALREADY_PROCESSING"
        )


class InvalidFileTypeException(APIException):
    """지원하지 않는 파일 형식"""
    def __init__(self, file_type: str, allowed_types: list):
        super().__init__(
            status_code=400,
            detail=f"지원하지 않는 파일 형식입니다: {file_type}. "
                   f"허용된 형식: {', '.join(allowed_types)}",
            error_code="INVALID_FILE_TYPE"
        )


class FileSizeExceededException(APIException):
    """파일 크기 초과"""
    def __init__(self, file_size: int, max_size: int):
        super().__init__(
            status_code=400,
            detail=f"파일 크기가 너무 큽니다. "
                   f"업로드: {file_size / 1024 / 1024:.2f}MB, "
                   f"최대: {max_size / 1024 / 1024:.2f}MB",
            error_code="FILE_SIZE_EXCEEDED"
        )


class AnalysisFailedException(APIException):
    """문서 분석 실패"""
    def __init__(self, reason: str = "알 수 없는 오류"):
        super().__init__(
            status_code=500,
            detail=f"문서 분석 중 오류가 발생했습니다: {reason}",
            error_code="ANALYSIS_FAILED"
        )


class ParsingFailedException(APIException):
    """문서 파싱 실패"""
    def __init__(self, file_type: str, reason: str):
        super().__init__(
            status_code=500,
            detail=f"{file_type} 파일 파싱 실패: {reason}",
            error_code="PARSING_FAILED"
        )


class RateLimitExceededException(APIException):
    """Rate Limit 초과"""
    def __init__(self, retry_after: int = 60):
        super().__init__(
            status_code=429,
            detail=f"요청 한도를 초과했습니다. {retry_after}초 후에 다시 시도하세요.",
            error_code="RATE_LIMIT_EXCEEDED",
            headers={"Retry-After": str(retry_after)}
        )


class UnauthorizedException(APIException):
    """인증 실패"""
    def __init__(self, detail: str = "인증이 필요합니다"):
        super().__init__(
            status_code=401,
            detail=detail,
            error_code="UNAUTHORIZED"
        )


class ForbiddenException(APIException):
    """권한 없음"""
    def __init__(self, detail: str = "접근 권한이 없습니다"):
        super().__init__(
            status_code=403,
            detail=detail,
            error_code="FORBIDDEN"
        )


class ValidationException(APIException):
    """입력 검증 실패"""
    def __init__(self, detail: str, field: Optional[str] = None):
        error_detail = f"{field}: {detail}" if field else detail
        super().__init__(
            status_code=422,
            detail=error_detail,
            error_code="VALIDATION_ERROR"
        )


class ExternalAPIException(APIException):
    """외부 API 호출 실패"""
    def __init__(self, service: str, reason: str):
        super().__init__(
            status_code=502,
            detail=f"{service} API 호출 실패: {reason}",
            error_code="EXTERNAL_API_ERROR"
        )


class ServiceUnavailableException(APIException):
    """서비스 이용 불가"""
    def __init__(self, detail: str = "서비스를 일시적으로 사용할 수 없습니다"):
        super().__init__(
            status_code=503,
            detail=detail,
            error_code="SERVICE_UNAVAILABLE"
        )