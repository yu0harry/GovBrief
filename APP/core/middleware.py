"""
미들웨어 모음 (메모리 누수 수정)
- LoggingMiddleware: 요청/응답 로깅
- RateLimitMiddleware: IP별 Rate Limiting (메모리 관리 개선)
"""
import time
import logging
from typing import Callable, Dict
from collections import defaultdict
from datetime import datetime, timedelta

from fastapi import Request, Response
from fastapi.responses import JSONResponse
from starlette.middleware.base import BaseHTTPMiddleware

from APP.core.exceptions import RateLimitExceededException


# 로거 설정
logger = logging.getLogger(__name__)


class LoggingMiddleware(BaseHTTPMiddleware):
    """
    요청/응답 로깅 미들웨어
    
    기능:
    - 요청 정보 로깅 (메서드, 경로, IP, User-Agent)
    - 응답 시간 측정
    - 응답 상태 코드 로깅
    - 에러 발생 시 상세 로깅
    """
    
    async def dispatch(self, request: Request, call_next: Callable):
        """요청 처리 및 로깅"""
        # 요청 시작 시간
        start_time = time.time()
        
        # 클라이언트 정보
        client_ip = request.client.host if request.client else "unknown"
        user_agent = request.headers.get("user-agent", "unknown")
        
        # 요청 정보 로깅
        logger.info(
            f"📥 REQUEST | "
            f"Method: {request.method} | "
            f"Path: {request.url.path} | "
            f"IP: {client_ip} | "
            f"User-Agent: {user_agent[:50]}"
        )
        
        try:
            # 요청 처리
            response = await call_next(request)
            
            # 처리 시간 계산
            process_time = time.time() - start_time
            
            # 응답 정보 로깅
            logger.info(
                f"📤 RESPONSE | "
                f"Status: {response.status_code} | "
                f"Time: {process_time:.3f}s | "
                f"Path: {request.url.path}"
            )
            
            # 응답 헤더에 처리 시간 추가
            response.headers["X-Process-Time"] = str(process_time)
            
            return response
            
        except Exception as e:
            # 에러 발생 시 로깅
            process_time = time.time() - start_time
            
            logger.error(
                f"❌ ERROR | "
                f"Path: {request.url.path} | "
                f"Error: {str(e)} | "
                f"Time: {process_time:.3f}s",
                exc_info=True
            )
            
            # 에러를 다시 발생시켜 Error Handler가 처리하도록 함
            raise


class RateLimitMiddleware(BaseHTTPMiddleware):
    """
    Rate Limiting 미들웨어 (메모리 관리 개선)
    
    기능:
    - IP별 요청 횟수 제한
    - 시간 윈도우 기반 제한 (Sliding Window)
    - 특정 경로 제외 가능
    - 자동 메모리 정리 (메모리 누수 방지)
    
    설정:
    - max_requests: 최대 요청 수 (기본: 100)
    - window_seconds: 시간 윈도우 (기본: 3600초 = 1시간)
    - exclude_paths: Rate Limit 제외 경로
    - cleanup_interval: 메모리 정리 주기 (기본: 600초 = 10분)
    """
    
    def __init__(
        self,
        app,
        max_requests: int = 100,
        window_seconds: int = 3600,
        exclude_paths: list = None,
        cleanup_interval: int = 600  # 10분마다 정리
    ):
        super().__init__(app)
        self.max_requests = max_requests
        self.window_seconds = window_seconds
        self.exclude_paths = exclude_paths or ["/health", "/docs", "/openapi.json"]
        self.cleanup_interval = cleanup_interval
        
        # IP별 요청 기록: {ip: [timestamp1, timestamp2, ...]}
        self.request_counts: Dict[str, list] = defaultdict(list)
        
        # 마지막 정리 시간
        self.last_cleanup = datetime.now()
        
        # 총 정리 횟수 (통계용)
        self.cleanup_count = 0
        
        logger.info(
            f"⚙️ RateLimitMiddleware initialized: "
            f"{max_requests} requests per {window_seconds}s, "
            f"cleanup every {cleanup_interval}s"
        )
    
    async def dispatch(self, request: Request, call_next: Callable):
        """Rate Limit 체크 및 요청 처리"""
        # 주기적 메모리 정리 (10분마다)
        await self._periodic_cleanup()
        
        # 제외 경로는 Rate Limit 적용 안 함
        if request.url.path in self.exclude_paths:
            return await call_next(request)
        
        # 클라이언트 IP
        client_ip = request.client.host if request.client else "unknown"
        
        # Rate Limit 체크
        if not self._is_allowed(client_ip):
            logger.warning(
                f"🚫 RATE LIMIT EXCEEDED | "
                f"IP: {client_ip} | "
                f"Path: {request.url.path}"
            )
            
            # Rate Limit 초과 응답
            return JSONResponse(
                status_code=429,
                content={
                    "error": "Rate Limit Exceeded",
                    "detail": f"요청 한도를 초과했습니다. {self.window_seconds}초 후에 다시 시도하세요.",
                    "max_requests": self.max_requests,
                    "window_seconds": self.window_seconds
                },
                headers={"Retry-After": str(self.window_seconds)}
            )
        
        # 요청 기록
        self._record_request(client_ip)
        
        # 요청 처리
        response = await call_next(request)
        
        # 남은 요청 횟수를 헤더에 추가
        remaining = self._get_remaining(client_ip)
        response.headers["X-RateLimit-Limit"] = str(self.max_requests)
        response.headers["X-RateLimit-Remaining"] = str(remaining)
        response.headers["X-RateLimit-Window"] = str(self.window_seconds)
        
        return response
    
    def _is_allowed(self, ip: str) -> bool:
        """IP의 Rate Limit 허용 여부 확인"""
        now = datetime.now()
        cutoff_time = now - timedelta(seconds=self.window_seconds)
        
        # 오래된 요청 기록 제거 (Sliding Window)
        self.request_counts[ip] = [
            timestamp for timestamp in self.request_counts[ip]
            if timestamp > cutoff_time
        ]
        
        # 현재 윈도우 내 요청 수 확인
        return len(self.request_counts[ip]) < self.max_requests
    
    def _record_request(self, ip: str):
        """요청 기록"""
        now = datetime.now()
        self.request_counts[ip].append(now)
    
    def _get_remaining(self, ip: str) -> int:
        """남은 요청 횟수 계산"""
        now = datetime.now()
        cutoff_time = now - timedelta(seconds=self.window_seconds)
        
        # 현재 윈도우 내 요청 수
        current_count = len([
            timestamp for timestamp in self.request_counts[ip]
            if timestamp > cutoff_time
        ])
        
        return max(0, self.max_requests - current_count)
    
    async def _periodic_cleanup(self):
        """
        주기적 메모리 정리 (메모리 누수 방지)
        
        - cleanup_interval 시간마다 실행
        - 오래된 IP 기록 삭제
        - 빈 리스트 제거
        """
        now = datetime.now()
        
        # 정리 주기 확인
        if (now - self.last_cleanup).total_seconds() < self.cleanup_interval:
            return
        
        # 정리 시작
        logger.info("🧹 Rate Limit 메모리 정리 시작...")
        
        old_count = len(self.request_counts)
        cutoff_time = now - timedelta(seconds=self.window_seconds * 2)  # 윈도우의 2배
        
        # 오래된 기록 삭제
        for ip in list(self.request_counts.keys()):
            # 오래된 타임스탬프 제거
            self.request_counts[ip] = [
                ts for ts in self.request_counts[ip] if ts > cutoff_time
            ]
            
            # 빈 리스트는 삭제
            if not self.request_counts[ip]:
                del self.request_counts[ip]
        
        # 정리 완료
        new_count = len(self.request_counts)
        removed = old_count - new_count
        
        self.last_cleanup = now
        self.cleanup_count += 1
        
        logger.info(
            f"✅ Rate Limit 메모리 정리 완료: "
            f"{removed}개 IP 제거, "
            f"남은 IP: {new_count}개 "
            f"(정리 횟수: {self.cleanup_count})"
        )
    
    def get_stats(self) -> Dict:
        """
        Rate Limit 통계 조회
        
        Returns:
            {
                "tracked_ips": int,
                "total_requests": int,
                "cleanup_count": int,
                "last_cleanup": str
            }
        """
        total_requests = sum(len(timestamps) for timestamps in self.request_counts.values())
        
        return {
            "tracked_ips": len(self.request_counts),
            "total_requests": total_requests,
            "cleanup_count": self.cleanup_count,
            "last_cleanup": self.last_cleanup.isoformat()
        }


class RequestIDMiddleware(BaseHTTPMiddleware):
    """
    요청 ID 추가 미들웨어 (선택사항)
    
    각 요청에 고유 ID를 부여하여 추적 가능하게 함
    """
    
    async def dispatch(self, request: Request, call_next: Callable):
        """요청 ID 생성 및 추가"""
        import uuid
        
        # 요청 ID 생성 (이미 있으면 사용)
        request_id = request.headers.get("X-Request-ID") or str(uuid.uuid4())
        
        # 요청에 ID 추가 (로깅에서 사용 가능)
        request.state.request_id = request_id
        
        # 요청 처리
        response = await call_next(request)
        
        # 응답 헤더에 요청 ID 추가
        response.headers["X-Request-ID"] = request_id
        
        return response


class SecurityHeadersMiddleware(BaseHTTPMiddleware):
    """
    보안 헤더 추가 미들웨어 (선택사항)
    
    기본 보안 헤더를 응답에 추가
    """
    
    async def dispatch(self, request: Request, call_next: Callable):
        """보안 헤더 추가"""
        response = await call_next(request)
        
        # 보안 헤더 추가
        response.headers["X-Content-Type-Options"] = "nosniff"
        response.headers["X-Frame-Options"] = "DENY"
        response.headers["X-XSS-Protection"] = "1; mode=block"
        response.headers["Strict-Transport-Security"] = "max-age=31536000; includeSubDomains"
        
        return response