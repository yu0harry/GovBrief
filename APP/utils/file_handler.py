"""
파일 처리 유틸리티 (보안 강화)
"""
import os
import re
import uuid
from pathlib import Path
from typing import Tuple
from fastapi import UploadFile, HTTPException


def sanitize_filename(filename: str) -> str:
    """
    파일명 안전하게 정제
    
    - Path Traversal 공격 방지 (../, ..\\)
    - 특수 문자 제거
    - 최대 길이 제한
    
    Args:
        filename: 원본 파일명
        
    Returns:
        안전한 파일명
    """
    if not filename:
        return "unnamed"
    
    # Path traversal 패턴 제거
    filename = filename.replace('../', '').replace('..\\', '')
    filename = filename.replace('/', '_').replace('\\', '_')
    
    # 안전한 파일명만 허용 (영문, 숫자, 점, 언더스코어, 하이픈, 한글)
    filename = re.sub(r'[^\w\s\-\.가-힣]', '_', filename)
    
    # 연속된 언더스코어 제거
    filename = re.sub(r'_+', '_', filename)
    
    # 최대 길이 255자 제한
    if len(filename) > 255:
        name, ext = os.path.splitext(filename)
        filename = name[:250] + ext
    
    # 파일명 앞뒤 공백/점 제거
    filename = filename.strip('. ')
    
    return filename or "unnamed"


class FileHandler:
    """파일 업로드 및 저장 처리 (보안 강화)"""
    
    # 허용된 파일 확장자
    ALLOWED_EXTENSIONS = {".pdf", ".hwp", ".docx", ".jpg", ".jpeg", ".png"}
    
    # 최대 파일 크기 (10MB)
    MAX_FILE_SIZE = 10 * 1024 * 1024
    
    # 최소 파일 크기 (100 bytes) - 악의적 빈 파일 방지
    MIN_FILE_SIZE = 100
    
    def __init__(self, upload_dir: str = "./tmp/uploads"):
        """
        Args:
            upload_dir: 파일 저장 디렉토리
        """
        self.upload_dir = Path(upload_dir)
        self._ensure_upload_dir()
    
    def _ensure_upload_dir(self):
        """업로드 디렉토리 생성"""
        if not self.upload_dir.exists():
            self.upload_dir.mkdir(parents=True, exist_ok=True)
            print(f"✅ 업로드 디렉토리 생성: {self.upload_dir}")
        
        # 디렉토리 권한 확인
        if not os.access(self.upload_dir, os.W_OK):
            raise PermissionError(f"업로드 디렉토리에 쓰기 권한이 없습니다: {self.upload_dir}")
    
    def validate_file(self, file: UploadFile) -> Tuple[bool, str]:
        """
        파일 검증 (보안 강화)
        
        Args:
            file: 업로드된 파일
            
        Returns:
            (검증 성공 여부, 에러 메시지)
        """
        # 1. 파일명 존재 확인
        if not file.filename:
            return False, "파일명이 없습니다."
        
        # 2. 파일명 길이 확인
        if len(file.filename) > 255:
            return False, "파일명이 너무 깁니다. (최대 255자)"
        
        # 3. 확장자 추출 및 검증
        file_ext = Path(file.filename).suffix.lower()
        
        if not file_ext:
            return False, "파일 확장자가 없습니다."
        
        if file_ext not in self.ALLOWED_EXTENSIONS:
            return False, f"지원하지 않는 파일 형식입니다. 허용: {', '.join(self.ALLOWED_EXTENSIONS)}"
        
        # 4. 위험한 파일명 패턴 체크
        dangerous_patterns = ['../', '..\\', '<', '>', '|', '&', ';', '`']
        
        for pattern in dangerous_patterns:
            if pattern in file.filename:
                return False, f"파일명에 허용되지 않은 문자가 포함되어 있습니다."
        
        return True, ""
    
    async def save_file(self, file: UploadFile) -> Tuple[str, str, int]:
        """
        파일 저장 (보안 강화)
        
        Args:
            file: 업로드된 파일
            
        Returns:
            (문서 ID, 저장 경로, 파일 크기)
            
        Raises:
            HTTPException: 파일 저장 실패 시
        """
        # 1. 파일 검증
        is_valid, error_msg = self.validate_file(file)
        if not is_valid:
            raise HTTPException(status_code=400, detail=error_msg)
        
        # 2. 고유 문서 ID 생성
        document_id = str(uuid.uuid4())
        
        # 3. 파일 확장자 추출
        file_ext = Path(file.filename).suffix.lower()
        
        # 4. 안전한 파일명 생성: {document_id}{확장자}
        # UUID만 사용하므로 원본 파일명은 사용하지 않음 (보안)
        save_filename = f"{document_id}{file_ext}"
        save_path = self.upload_dir / save_filename
        
        # 5. 파일 저장
        try:
            content = await file.read()
            
            # 6. 파일 크기 검증
            file_size = len(content)
            
            if file_size < self.MIN_FILE_SIZE:
                raise HTTPException(
                    status_code=400,
                    detail=f"파일이 너무 작습니다. 최소: {self.MIN_FILE_SIZE} bytes"
                )
            
            if file_size > self.MAX_FILE_SIZE:
                raise HTTPException(
                    status_code=400,
                    detail=f"파일 크기가 너무 큽니다. 최대: {self.MAX_FILE_SIZE / 1024 / 1024}MB"
                )
            
            # 7. 파일 쓰기
            with open(save_path, "wb") as f:
                f.write(content)
            
            # 8. 파일 권한 설정 (읽기 전용으로 변경)
            try:
                os.chmod(save_path, 0o644)  # rw-r--r--
            except:
                pass  # Windows에서는 chmod가 제한적으로 작동
            
            print(f"✅ 파일 저장 완료: {save_path} ({file_size} bytes)")
            
            return document_id, str(save_path), file_size
            
        except HTTPException:
            # HTTP 예외는 그대로 전달
            raise
        except Exception as e:
            # 저장 실패 시 파일 삭제
            if save_path.exists():
                try:
                    save_path.unlink()
                except:
                    pass
            raise HTTPException(
                status_code=500,
                detail=f"파일 저장 중 오류 발생: {str(e)}"
            )
    
    def get_file_path(self, document_id: str, file_type: str) -> Path:
        """
        문서 ID로 파일 경로 조회
        
        Args:
            document_id: 문서 ID (UUID)
            file_type: 파일 확장자 (.pdf 등)
            
        Returns:
            파일 경로
        """
        # UUID 형식 검증
        try:
            uuid.UUID(document_id)
        except ValueError:
            raise ValueError(f"잘못된 문서 ID 형식: {document_id}")
        
        # 확장자 검증
        if file_type not in self.ALLOWED_EXTENSIONS:
            raise ValueError(f"잘못된 파일 타입: {file_type}")
        
        filename = f"{document_id}{file_type}"
        file_path = self.upload_dir / filename
        
        # Path traversal 방어: 결과 경로가 upload_dir 안에 있는지 확인
        if not str(file_path.resolve()).startswith(str(self.upload_dir.resolve())):
            raise ValueError("잘못된 파일 경로")
        
        return file_path
    
    def delete_file(self, document_id: str, file_type: str) -> bool:
        """
        파일 삭제
        
        Args:
            document_id: 문서 ID
            file_type: 파일 확장자
            
        Returns:
            삭제 성공 여부
        """
        try:
            file_path = self.get_file_path(document_id, file_type)
            
            if file_path.exists():
                file_path.unlink()
                print(f"✅ 파일 삭제: {file_path}")
                return True
            
            return False
            
        except ValueError as e:
            print(f"❌ 파일 삭제 실패 (검증 오류): {e}")
            return False
        except Exception as e:
            print(f"❌ 파일 삭제 실패: {e}")
            return False


# 싱글톤 인스턴스
file_handler = FileHandler()