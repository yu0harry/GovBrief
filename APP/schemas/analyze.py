"""
분석 관련 스키마 (v2)

개선사항:
- 문서 유형별 세부 정보 (details)
- RAG 인덱싱 상태
- 분석 메타데이터
"""
from pydantic import BaseModel, Field
from typing import List, Optional, Dict, Any


class AnalyzeRequest(BaseModel):
    """분석 요청"""
    document_id: str = Field(..., description="분석할 문서 ID")
    force_type: Optional[str] = Field(None, description="강제 지정할 문서 유형")
    
    class Config:
        json_schema_extra = {
            "example": {
                "document_id": "abc-123-def",
                "force_type": None
            }
        }


class ActionItem(BaseModel):
    """행동 안내 항목"""
    action: str = Field(..., description="해야 할 행동")
    deadline: Optional[str] = Field(None, description="마감일 (YYYY-MM-DD)")
    amount: Optional[int] = Field(None, description="금액")
    method: Optional[str] = Field(None, description="방법")
    
    class Config:
        json_schema_extra = {
            "example": {
                "action": "지방세입계좌로 납부하세요",
                "deadline": "2025-10-20",
                "amount": 130000,
                "method": "위택스 또는 은행"
            }
        }


class TaxDetails(BaseModel):
    """세금 고지서 세부 정보"""
    tax_type: Optional[str] = Field(None, description="세금 종류")
    principal: Optional[int] = Field(None, description="원금")
    penalty: Optional[int] = Field(None, description="가산금")
    total: Optional[int] = Field(None, description="총액")


class PrescriptionMedication(BaseModel):
    """처방 약품 정보"""
    name: str = Field(..., description="약품명")
    dosage: Optional[str] = Field(None, description="용량")
    frequency: Optional[str] = Field(None, description="복용 횟수")
    duration: Optional[str] = Field(None, description="복용 기간")


class PrescriptionDetails(BaseModel):
    """처방전 세부 정보"""
    hospital: Optional[str] = Field(None, description="처방 병원")
    doctor: Optional[str] = Field(None, description="처방 의사")
    medications: List[PrescriptionMedication] = Field(default_factory=list, description="처방 약품 목록")
    valid_until: Optional[str] = Field(None, description="처방전 유효기간")


class ContractDetails(BaseModel):
    """계약서 세부 정보"""
    parties: List[str] = Field(default_factory=list, description="계약 당사자")
    subject: Optional[str] = Field(None, description="계약 대상")
    period: Optional[str] = Field(None, description="계약 기간")
    amount: Optional[int] = Field(None, description="계약 금액")
    termination_clause: Optional[str] = Field(None, description="해지 조건")


class NoticeDetails(BaseModel):
    """통지서 세부 정보"""
    issuer: Optional[str] = Field(None, description="발송 기관")
    purpose: Optional[str] = Field(None, description="통지 목적")
    contact: Optional[str] = Field(None, description="연락처")


class InsuranceDetails(BaseModel):
    """보험 서류 세부 정보"""
    type: Optional[str] = Field(None, description="보험 종류")
    coverage: Optional[str] = Field(None, description="보장 내용")
    premium: Optional[int] = Field(None, description="보험료")
    period: Optional[str] = Field(None, description="보험 기간")


class DocumentDetails(BaseModel):
    """문서 유형별 세부 정보 (통합)"""
    tax_details: Optional[TaxDetails] = None
    prescription_details: Optional[PrescriptionDetails] = None
    contract_details: Optional[ContractDetails] = None
    notice_details: Optional[NoticeDetails] = None
    insurance_details: Optional[InsuranceDetails] = None


class AnalyzeResponse(BaseModel):
    """분석 결과 응답"""
    document_id: str = Field(..., description="문서 ID")
    summary: str = Field(..., description="문서 요약")
    document_type: str = Field(..., description="문서 유형")
    importance: str = Field(..., description="중요도 (high/medium/low)")
    key_points: List[str] = Field(default_factory=list, description="핵심 포인트")
    actions: List[ActionItem] = Field(default_factory=list, description="행동 안내")
    details: Optional[Dict[str, Any]] = Field(None, description="문서 유형별 세부 정보")
    
    # 메타데이터
    rag_indexed: Optional[bool] = Field(None, description="RAG 인덱싱 여부")
    chunk_count: Optional[int] = Field(None, description="청크 수")
    
    class Config:
        json_schema_extra = {
            "example": {
                "document_id": "abc-123-def",
                "summary": "2025년 지방세 납부 고지서입니다. 3월 31일까지 250,000원을 납부해야 합니다.",
                "document_type": "세금고지서",
                "importance": "high",
                "key_points": [
                    "납부 기한: 2025년 3월 31일",
                    "납부 금액: 250,000원",
                    "미납 시 3% 가산세 부과"
                ],
                "actions": [
                    {
                        "action": "재산세 납부",
                        "deadline": "2025-03-31",
                        "amount": 250000,
                        "method": "위택스 또는 은행"
                    }
                ],
                "details": {
                    "tax_details": {
                        "tax_type": "재산세",
                        "principal": 250000,
                        "penalty": 0,
                        "total": 250000
                    }
                },
                "rag_indexed": True,
                "chunk_count": 5
            }
        }


class AnalysisStatusResponse(BaseModel):
    """분석 상태 응답"""
    document_id: str
    filename: Optional[str] = None
    status: str
    document_type: Optional[str] = None
    has_analysis: bool = False
    has_text: bool = False
    rag_indexed: bool = False
    chunk_count: int = 0