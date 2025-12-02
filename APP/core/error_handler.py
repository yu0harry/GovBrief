"""
전역 에러 핸들러
모든 예외를 일관된 JSON 형식으로 응답
"""
import logging
import traceback
from typing import Union

from fastapi import Request, status
from fastapi.responses import JSONResponse
from fastapi.exceptions import RequestValidationError
from starlette.exceptions import HTTPException as StarletteHTTPException

from APP.core.exceptions import APIException


logger = logging.getLogger(__name__)


async def api_exception_handler(request: Request, exc: APIException) -> JSONResponse:
    """
    커스텀 APIException 핸들러
    
    구조화된 에러 응답 반환
    """
    logger.warning(
        f"⚠️ APIException | "
        f"Path: {request.url.path} | "
        f"Status: {exc.status_code} | "
        f"Error: {exc.error_code} | "
        f"Detail: {exc.detail}"
    )
    
    return JSONResponse(
        status_code=exc.status_code,
        content={
            "error": exc.error_code,
            "detail": exc.detail,
            "path": str(request.url.path),
            "timestamp": _get_timestamp()
        },
        headers=exc.headers
    )


async def http_exception_handler(
    request: Request,
    exc: StarletteHTTPException
) -> JSONResponse:
    """
    일반 HTTPException 핸들러
    
    FastAPI/Starlette의 기본 HTTPException 처리
    """
    logger.warning(
        f"⚠️ HTTPException | "
        f"Path: {request.url.path} | "
        f"Status: {exc.status_code} | "
        f"Detail: {exc.detail}"
    )
    
    return JSONResponse(
        status_code=exc.status_code,
        content={
            "error": f"HTTP_{exc.status_code}",
            "detail": exc.detail,
            "path": str(request.url.path),
            "timestamp": _get_timestamp()
        },
        headers=getattr(exc, "headers", None)
    )


async def validation_exception_handler(
    request: Request,
    exc: RequestValidationError
) -> JSONResponse:
    """
    Pydantic Validation 에러 핸들러
    
    입력 검증 실패 시 상세 에러 정보 제공
    """
    # 에러 상세 정보 추출
    errors = []
    for error in exc.errors():
        field = " -> ".join(str(loc) for loc in error["loc"])
        errors.append({
            "field": field,
            "message": error["msg"],
            "type": error["type"]
        })
    
    logger.warning(
        f"⚠️ ValidationError | "
        f"Path: {request.url.path} | "
        f"Errors: {len(errors)}"
    )
    
    return JSONResponse(
        status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
        content={
            "error": "VALIDATION_ERROR",
            "detail": "입력 데이터 검증 실패",
            "errors": errors,
            "path": str(request.url.path),
            "timestamp": _get_timestamp()
        }
    )


async def general_exception_handler(request: Request, exc: Exception) -> JSONResponse:
    """
    예상치 못한 일반 예외 핸들러
    
    서버 에러 (500) 반환
    """
    # 스택 트레이스 로깅
    logger.error(
        f"❌ UNEXPECTED ERROR | "
        f"Path: {request.url.path} | "
        f"Error: {str(exc)}",
        exc_info=True
    )
    
    # 디버그 모드에서는 스택 트레이스 포함
    from APP.config import settings
    
    content = {
        "error": "INTERNAL_SERVER_ERROR",
        "detail": "서버 내부 오류가 발생했습니다.",
        "path": str(request.url.path),
        "timestamp": _get_timestamp()
    }
    
    # 디버그 모드에서만 상세 정보 제공
    if settings.DEBUG:
        content["debug"] = {
            "exception": str(exc),
            "type": type(exc).__name__,
            "traceback": traceback.format_exc()
        }
    
    return JSONResponse(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        content=content
    )


def _get_timestamp() -> str:
    """현재 시간 ISO 형식으로 반환"""
    from datetime import datetime
    return datetime.now().isoformat()


def register_exception_handlers(app):
    """
    FastAPI 앱에 예외 핸들러 등록
    
    사용법:
        from APP.core.error_handler import register_exception_handlers
        register_exception_handlers(app)
    """
    # 커스텀 APIException
    app.add_exception_handler(APIException, api_exception_handler)
    
    # 일반 HTTPException
    app.add_exception_handler(StarletteHTTPException, http_exception_handler)
    
    # Pydantic Validation 에러
    app.add_exception_handler(RequestValidationError, validation_exception_handler)
    
    # 예상치 못한 모든 예외
    app.add_exception_handler(Exception, general_exception_handler)
    
    logger.info("✅ Exception handlers registered")


def init_sentry():
    """
    Sentry 에러 추적 초기화 (선택사항)
    
    프로덕션 환경에서 에러 모니터링
    
    설치:
        pip install sentry-sdk[fastapi]
    
    사용법:
        from APP.core.error_handler import init_sentry
        init_sentry()
    """
    try:
        import sentry_sdk
        from sentry_sdk.integrations.fastapi import FastApiIntegration
        from sentry_sdk.integrations.starlette import StarletteIntegration
        
        from APP.config import settings
        
        if settings.SENTRY_DSN:
            sentry_sdk.init(
                dsn=settings.SENTRY_DSN,
                integrations=[
                    StarletteIntegration(),
                    FastApiIntegration(),
                ],
                traces_sample_rate=0.1,
                environment="production" if not settings.DEBUG else "development",
            )
            logger.info("✅ Sentry initialized")
        else:
            logger.info("ℹ️ Sentry DSN not configured, skipping...")
            
    except ImportError:
        logger.warning("⚠️ sentry-sdk not installed, skipping...")
    except Exception as e:
        logger.error(f"❌ Sentry initialization failed: {e}")