"""
로거 설정 유틸리티

구조화된 로깅을 위한 설정
- 콘솔 출력 (개발 환경)
- 파일 출력 (프로덕션 환경)
- JSON 형식 로깅 (선택사항)
"""

import logging
import sys
from pathlib import Path
from typing import Optional
from datetime import datetime


class ColoredFormatter(logging.Formatter):
    """컬러 출력 포매터 (개발 환경용)"""
    
    # ANSI 색상 코드
    COLORS = {
        'DEBUG': '\033[36m',      # Cyan
        'INFO': '\033[32m',       # Green
        'WARNING': '\033[33m',    # Yellow
        'ERROR': '\033[31m',      # Red
        'CRITICAL': '\033[35m',   # Magenta
        'RESET': '\033[0m'        # Reset
    }
    
    def format(self, record):
        # 로그 레벨에 따라 색상 적용
        levelname = record.levelname
        if levelname in self.COLORS:
            record.levelname = f"{self.COLORS[levelname]}{levelname}{self.COLORS['RESET']}"
        
        return super().format(record)


def setup_logger(
    name: str = "app",
    level: str = "INFO",
    log_dir: Optional[str] = None,
    use_json: bool = False
) -> logging.Logger:
    """
    로거 설정
    
    Args:
        name: 로거 이름
        level: 로그 레벨 (DEBUG, INFO, WARNING, ERROR, CRITICAL)
        log_dir: 로그 파일 저장 디렉토리 (None이면 콘솔만)
        use_json: JSON 형식 로깅 사용 여부
        
    Returns:
        설정된 Logger 인스턴스
    """
    logger = logging.getLogger(name)
    logger.setLevel(getattr(logging, level.upper()))
    
    # 기존 핸들러 제거 (중복 방지)
    logger.handlers.clear()
    
    # ============================================
    # 1. 콘솔 핸들러 (개발 환경)
    # ============================================
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setLevel(logging.DEBUG)
    
    if use_json:
        # JSON 형식 (프로덕션)
        console_format = logging.Formatter(
            '{"time":"%(asctime)s", "level":"%(levelname)s", "name":"%(name)s", "message":"%(message)s"}'
        )
    else:
        # 컬러 형식 (개발)
        console_format = ColoredFormatter(
            '%(asctime)s | %(levelname)-8s | %(name)s | %(message)s',
            datefmt='%Y-%m-%d %H:%M:%S'
        )
    
    console_handler.setFormatter(console_format)
    logger.addHandler(console_handler)
    
    # ============================================
    # 2. 파일 핸들러 (프로덕션 환경)
    # ============================================
    if log_dir:
        log_path = Path(log_dir)
        log_path.mkdir(parents=True, exist_ok=True)
        
        # 날짜별 로그 파일
        today = datetime.now().strftime("%Y-%m-%d")
        log_file = log_path / f"{name}_{today}.log"
        
        file_handler = logging.FileHandler(log_file, encoding='utf-8')
        file_handler.setLevel(logging.INFO)
        
        file_format = logging.Formatter(
            '%(asctime)s | %(levelname)-8s | %(name)s | %(funcName)s:%(lineno)d | %(message)s',
            datefmt='%Y-%m-%d %H:%M:%S'
        )
        file_handler.setFormatter(file_format)
        logger.addHandler(file_handler)
        
        logger.info(f"로그 파일 생성: {log_file}")
    
    return logger


# ============================================
# 전역 로거 인스턴스
# ============================================
logger = setup_logger(
    name="app",
    level="INFO",
    log_dir=None,  # 개발 환경에서는 콘솔만
    use_json=False
)


# ============================================
# 편의 함수
# ============================================
def get_logger(name: str) -> logging.Logger:
    """
    모듈별 로거 반환
    
    Usage:
        from app.utils.logger import get_logger
        logger = get_logger(__name__)
        logger.info("메시지")
    """
    return logging.getLogger(name)