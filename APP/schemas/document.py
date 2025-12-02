"""
문서 관련 스키마
"""
from pydantic import BaseModel, Field
from typing import Optional
from datetime import datetime


class DocumentUploadResponse(BaseModel):
    """문서 업로드 응답"""
    document_id: str = Field(..., description="문서 고유 ID")
    filename: str = Field(..., description="파일명")
    file_size: int = Field(..., description="파일 크기 (bytes)")
    file_type: str = Field(..., description="파일 확장자")
    status: str = Field(default="uploaded", description="상태")
    created_at: datetime = Field(..., description="업로드 시간")
    parsed_result: Optional[dict] = Field(None, description="파싱 결과 (텍스트, 페이지 수 등)")
    
    class Config:
        json_schema_extra = {
            "example": {
                "document_id": "abc-123-def",
                "filename": "세금고지서.pdf",
                "file_size": 1024000,
                "file_type": ".pdf",
                "status": "completed",
                "created_at": "2025-11-20T14:30:00",
                "parsed_result": {
                    "text": "추출된 텍스트 내용...",
                    "page_count": 3,
                    "confidence": 1.0
                }
            }
        }


class DocumentResponse(BaseModel):
    """문서 조회 응답"""
    document_id: str
    filename: str
    file_size: int
    file_type: str
    status: str
    created_at: datetime
    analysis_result: Optional[dict] = None
    extracted_text: Optional[str] = Field(None, description="추출된 텍스트")
    page_count: Optional[int] = Field(None, description="페이지 수")
    
    class Config:
        json_schema_extra = {
            "example": {
                "document_id": "abc-123-def",
                "filename": "세금고지서.pdf",
                "file_size": 1024000,
                "file_type": ".pdf",
                "status": "completed",
                "created_at": "2025-11-20T14:30:00",
                "extracted_text": "추출된 문서 내용...",
                "page_count": 3,
                "analysis_result": {
                    "summary": "요약 내용",
                    "actions": []
                }
            }
        }
