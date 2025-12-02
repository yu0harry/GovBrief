"""
FastAPI 애플리케이션 진입점 (Phase 4: 미들웨어 추가)
"""
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from contextlib import asynccontextmanager
import os
import sys
import logging
from pathlib import Path
# ===== 파일 자동 정리 =====
from APP.utils.file_cleaner import start_file_cleaner, stop_file_cleaner, get_file_cleaner

# 프로젝트 루트를 Python 경로에 추가
ROOT_DIR = Path(__file__).parent.parent
sys.path.insert(0, str(ROOT_DIR))

from APP.config import settings, validate_settings

# API 라우터 import
from APP.API import documents, analyze, chat

# ===== Phase 4: 미들웨어 및 에러 핸들러 추가 =====
from APP.core.middleware import (
    LoggingMiddleware,
    RateLimitMiddleware,
    RequestIDMiddleware,
    SecurityHeadersMiddleware,
)
from APP.core.error_handler import register_exception_handlers, init_sentry


# ===== 로깅 설정 =====
logging.basicConfig(
    level=getattr(logging, settings.LOG_LEVEL),
    format='%(asctime)s | %(levelname)s | %(name)s | %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S'
)
logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """애플리케이션 시작/종료 이벤트"""
    # Startup
    print("=" * 60)
    print("🚀 애플리케이션 시작 중...")
    print("=" * 60)
    
    try:
        validate_settings()
        logger.info("✅ 설정 검증 완료")
    except ValueError as e:
        logger.error(f"❌ 설정 오류: {e}")
        raise
    
    # 업로드 디렉토리 생성
    upload_dir = settings.UPLOAD_DIR
    if not os.path.exists(upload_dir):
        os.makedirs(upload_dir)
        logger.info(f"✅ 업로드 디렉토리 생성: {upload_dir}")
    
    # Sentry 초기화 (선택사항)
    if settings.SENTRY_DSN:
        init_sentry()
    
    # ===== 파일 자동 정리 시작 =====
    await start_file_cleaner(
        interval_seconds=600,  # 10분마다 정리
        ttl_seconds=3600       # 1시간 후 삭제
    )
    logger.info("✅ 파일 자동 정리 시작 (10분 주기, 1시간 TTL)")
    
    print("=" * 60)
    print(f"✅ {settings.PROJECT_NAME} 시작 완료!")
    print(f"📍 API 문서: http://localhost:8000/docs")
    print(f"📍 Health Check: http://localhost:8000/health")
    print("=" * 60)
    
    yield
    
    # Shutdown
    print("\n" + "=" * 60)
    print("👋 애플리케이션 종료 중...")
    print("=" * 60)
    
    # ===== 파일 자동 정리 중지 =====
    await stop_file_cleaner()
    logger.info("✅ 파일 자동 정리 중지")
    
    logger.info("✅ 종료 완료")

# ===== FastAPI 앱 생성 =====
app = FastAPI(
    title=settings.PROJECT_NAME,
    description="공공문서 AI 분석 서비스 - 문서 업로드, 분석, 챗봇 Q&A",
    version="1.0.0",
    openapi_url=f"{settings.API_V1_STR}/openapi.json",
    docs_url="/docs",
    redoc_url="/redoc",
    lifespan=lifespan,
    debug=settings.DEBUG,
)


# ===== Phase 4: 에러 핸들러 등록 =====
register_exception_handlers(app)


# ===== Phase 4: 미들웨어 등록 (순서 중요!) =====

# 1. CORS (가장 먼저)
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.ALLOWED_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# 2. Security Headers
app.add_middleware(SecurityHeadersMiddleware)

# 3. Request ID
app.add_middleware(RequestIDMiddleware)

# 4. Logging (요청/응답 로깅)
app.add_middleware(LoggingMiddleware)

# 5. Rate Limiting (마지막 - 실제 요청 처리 직전)
app.add_middleware(
    RateLimitMiddleware,
    max_requests=100,          # IP당 100회
    window_seconds=3600,       # 1시간 윈도우
    exclude_paths=[            # Rate Limit 제외 경로
        "/health",
        "/docs",
        "/redoc",
        "/openapi.json",
        "/",
    ]
)

logger.info("✅ 모든 미들웨어 등록 완료")


# ===== 라우터 등록 =====
app.include_router(
    documents.router,
    prefix=f"{settings.API_V1_STR}/documents",
    tags=["documents"]
)

app.include_router(
    analyze.router,
    prefix=settings.API_V1_STR,
    tags=["analyze"]
)

app.include_router(
    chat.router,
    prefix=settings.API_V1_STR,
    tags=["chat"]
)


# ===== 기본 엔드포인트 =====
@app.get("/")
async def root():
    """
    루트 엔드포인트
    API 기본 정보 반환
    """
    return {
        "message": f"Welcome to {settings.PROJECT_NAME} API",
        "version": "1.0.0",
        "phase": "Phase 4: Middleware Enabled",
        "features": [
            "✅ Logging Middleware",
            "✅ Rate Limiting (100 req/hour per IP)",
            "✅ Request ID Tracking",
            "✅ Security Headers",
            "✅ Global Error Handling"
        ],
        "docs": "/docs",
        "health": "/health",
        "endpoints": {
            "upload": f"{settings.API_V1_STR}/documents/upload",
            "analyze": f"{settings.API_V1_STR}/analyze",
            "chat": f"{settings.API_V1_STR}/chat"
        }
    }


@app.get("/health")
async def health_check():
    """
    헬스 체크 엔드포인트
    서버 상태 확인용
    """
    return {
        "status": "healthy",
        "service": settings.PROJECT_NAME,
        "version": "1.0.0",
        "phase": "Phase 4",
        "middleware": {
            "logging": True,
            "rate_limiting": True,
            "request_id": True,
            "security_headers": True,
            "error_handling": True
        }
    }


# ===== 개발 서버 실행 =====
if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "APP.main:app",
        host="0.0.0.0",
        port=8000,
        reload=True,
        log_level="info"
    )