"""
채팅 관련 스키마
"""
from pydantic import BaseModel, Field
from typing import Optional


class ChatRequest(BaseModel):
    """채팅 요청"""
    document_id: str = Field(..., description="질문할 문서 ID")
    question: str = Field(..., description="질문 내용")
    
    class Config:
        json_schema_extra = {
            "example": {
                "document_id": "abc-123-def",
                "question": "이 문서의 주요 내용은 무엇인가요?"
            }
        }


class ChatResponse(BaseModel):
    """채팅 응답"""
    answer: str = Field(..., description="AI 답변")
    source: str = Field(default="document", description="답변 출처")
    confidence: float = Field(default=0.0, description="신뢰도 (0.0~1.0)")
    
    class Config:
        json_schema_extra = {
            "example": {
                "answer": "이 문서는 2025년도 지방세 납부에 관한 안내입니다...",
                "source": "document",
                "confidence": 0.85
            }
        }