"""
해시 유틸리티 (캐싱용)
"""
import hashlib


def generate_file_hash(content: bytes) -> str:
    """
    파일 내용의 MD5 해시 생성
    
    Args:
        content: 파일 내용 (bytes)
        
    Returns:
        MD5 해시 문자열
    """
    return hashlib.md5(content).hexdigest()


def generate_text_hash(text: str) -> str:
    """
    텍스트의 MD5 해시 생성
    
    Args:
        text: 텍스트
        
    Returns:
        MD5 해시 문자열
    """
    return hashlib.md5(text.encode('utf-8')).hexdigest()