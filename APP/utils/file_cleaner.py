"""
파일 자동 정리 유틸리티

기능:
- TTL 기반 오래된 파일 삭제
- Mock DB에 없는 고아 파일 삭제
- 주기적 백그라운드 실행
"""
import os
import asyncio
import logging
from pathlib import Path
from datetime import datetime, timedelta
from typing import Optional

logger = logging.getLogger(__name__)


class FileCleaner:
    """
    파일 자동 정리 클래스
    
    Usage:
        cleaner = FileCleaner(upload_dir="./tmp/uploads", ttl_seconds=3600)
        await cleaner.start(interval_seconds=600)  # 10분마다 실행
    """
    
    def __init__(
        self,
        upload_dir: str = "./tmp/uploads",
        ttl_seconds: int = 3600,  # 기본 1시간
    ):
        self.upload_dir = Path(upload_dir)
        self.ttl_seconds = ttl_seconds
        self._running = False
        self._task: Optional[asyncio.Task] = None
        
        # 통계
        self.total_cleaned = 0
        self.last_cleanup = None
    
    async def start(self, interval_seconds: int = 600):
        """주기적 정리 시작"""
        if self._running:
            logger.warning("⚠️ FileCleaner가 이미 실행 중입니다")
            return
        
        self._running = True
        self._task = asyncio.create_task(
            self._cleanup_loop(interval_seconds)
        )
        
        logger.info(
            f"🧹 FileCleaner 시작: "
            f"TTL={self.ttl_seconds}초, "
            f"주기={interval_seconds}초"
        )
    
    async def stop(self):
        """정리 작업 중지"""
        self._running = False
        
        if self._task:
            self._task.cancel()
            try:
                await self._task
            except asyncio.CancelledError:
                pass
        
        logger.info("🛑 FileCleaner 중지됨")
    
    async def _cleanup_loop(self, interval_seconds: int):
        """주기적 정리 루프"""
        while self._running:
            try:
                await self.cleanup()
            except Exception as e:
                logger.error(f"❌ 정리 중 오류: {e}")
            
            await asyncio.sleep(interval_seconds)
    
    async def cleanup(self) -> dict:
        """파일 정리 실행"""
        if not self.upload_dir.exists():
            return {"deleted_count": 0, "deleted_files": [], "orphan_count": 0, "error_count": 0}
        
        # Mock DB import (순환 참조 방지)
        from APP.db.mock_db import mock_db
        
        now = datetime.now()
        cutoff_time = now - timedelta(seconds=self.ttl_seconds)
        
        deleted_files = []
        orphan_files = []
        error_count = 0
        
        # 업로드 디렉토리의 모든 파일 검사
        for file_path in self.upload_dir.iterdir():
            if not file_path.is_file():
                continue
            
            try:
                # 파일 수정 시간 확인
                file_mtime = datetime.fromtimestamp(file_path.stat().st_mtime)
                
                # 파일명에서 document_id 추출 (UUID 형식)
                file_stem = file_path.stem  # 확장자 제외한 파일명
                
                # Mock DB에 존재하는지 확인
                document = mock_db.get_document(file_stem)
                
                should_delete = False
                reason = ""
                
                # 케이스 1: DB에 없는 고아 파일
                if document is None:
                    should_delete = True
                    reason = "고아 파일 (DB에 없음)"
                    orphan_files.append(file_path.name)
                
                # 케이스 2: TTL 초과
                elif file_mtime < cutoff_time:
                    should_delete = True
                    reason = f"TTL 초과 ({self.ttl_seconds}초)"
                
                # 삭제 실행
                if should_delete:
                    file_path.unlink()
                    deleted_files.append(file_path.name)
                    
                    # DB에서도 제거 (존재하면)
                    if document:
                        mock_db.delete_document(file_stem)
                    
                    logger.debug(f"🗑️ 삭제: {file_path.name} ({reason})")
                    
            except Exception as e:
                logger.warning(f"⚠️ 파일 처리 실패 {file_path.name}: {e}")
                error_count += 1
        
        # 통계 업데이트
        self.total_cleaned += len(deleted_files)
        self.last_cleanup = now
        
        # 결과 로깅 (삭제된 파일이 있을 때만)
        if deleted_files:
            logger.info(
                f"🧹 정리 완료: {len(deleted_files)}개 삭제 "
                f"(고아: {len(orphan_files)}개, 오류: {error_count}개)"
            )
        
        return {
            "deleted_count": len(deleted_files),
            "deleted_files": deleted_files,
            "orphan_count": len(orphan_files),
            "error_count": error_count
        }
    
    def get_stats(self) -> dict:
        """정리 통계 조회"""
        file_count = 0
        total_size = 0
        
        if self.upload_dir.exists():
            for file_path in self.upload_dir.iterdir():
                if file_path.is_file():
                    file_count += 1
                    total_size += file_path.stat().st_size
        
        return {
            "upload_dir": str(self.upload_dir),
            "ttl_seconds": self.ttl_seconds,
            "current_files": file_count,
            "current_size_mb": round(total_size / 1024 / 1024, 2),
            "total_cleaned": self.total_cleaned,
            "last_cleanup": self.last_cleanup.isoformat() if self.last_cleanup else None,
            "running": self._running
        }


# ============================================
# 전역 인스턴스
# ============================================

_cleaner_instance: Optional[FileCleaner] = None


def get_file_cleaner() -> FileCleaner:
    """전역 FileCleaner 인스턴스 반환"""
    global _cleaner_instance
    if _cleaner_instance is None:
        from APP.config import settings
        _cleaner_instance = FileCleaner(
            upload_dir=settings.UPLOAD_DIR,
            ttl_seconds=3600  # 1시간
        )
    return _cleaner_instance


async def start_file_cleaner(
    interval_seconds: int = 600,
    ttl_seconds: int = 3600
):
    """파일 정리 시작 (편의 함수)"""
    cleaner = get_file_cleaner()
    cleaner.ttl_seconds = ttl_seconds
    await cleaner.start(interval_seconds)


async def stop_file_cleaner():
    """파일 정리 중지"""
    cleaner = get_file_cleaner()
    await cleaner.stop()


async def manual_cleanup() -> dict:
    """수동 정리 실행"""
    cleaner = get_file_cleaner()
    return await cleaner.cleanup()
