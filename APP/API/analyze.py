"""
문서 분석 API (3단계 개선 - 인자값 오류 수정)

수정사항:
- parse_document 호출 시 인자 개수 오류(2개->1개) 수정
"""
from fastapi import APIRouter, HTTPException, BackgroundTasks
import logging
from typing import Optional

from APP.schemas.analyze import AnalyzeRequest, AnalyzeResponse, ActionItem
from APP.db.mock_db import mock_db

# 서비스 import
from APP.services.llm_service import is_available as llm_available, generate_json
from APP.services.prompts import (
    detect_document_type,
    get_analysis_prompt,
    DocumentType
)
from APP.services.rag_service import get_rag_system
from APP.services.chunker import SmartChunker, ChunkingConfig

# 파서 import
from APP.services.document_parser import parse_document

logger = logging.getLogger(__name__)

router = APIRouter()

# 청커 인스턴스
_chunker = SmartChunker(ChunkingConfig(
    chunk_size=800,
    chunk_overlap=150,
    preserve_tables=True
))


@router.post("/analyze", response_model=AnalyzeResponse)
async def analyze_document(
    request: AnalyzeRequest,
    background_tasks: BackgroundTasks
):
    """
    문서 분석 (AI 분석 + RAG 인덱싱)
    """
    document_id = request.document_id
    
    # 1. 문서 존재 확인
    document = mock_db.get_document(document_id)
    
    if not document:
        raise HTTPException(
            status_code=404,
            detail=f"문서를 찾을 수 없습니다: {document_id}"
        )
    
    # 2. 파싱된 텍스트 확인 및 자동 파싱
    extracted_text = document.get("extracted_text")
    
    if not extracted_text:
        logger.info(f"⚙️ 텍스트 미발견. 즉시 파싱 시작: {document.get('filename')}")
        try:
            # ⭐ [수정됨] 인자를 2개에서 1개(file_path)만 보내도록 수정
            parsing_result = await parse_document(document["file_path"])
            
            extracted_text = parsing_result.get("text", "")
            
            if not extracted_text:
                raise ValueError("문서에서 텍스트를 추출할 수 없습니다.")

            # DB에 추출된 텍스트 저장
            mock_db.update_document(
                document_id, 
                {
                    "extracted_text": extracted_text,
                    "page_count": parsing_result.get("pages", 1)
                }
            )
        except Exception as e:
            logger.error(f"❌ 파싱 실패: {str(e)}")
            raise HTTPException(
                status_code=500, 
                detail=f"문서 파싱 실패: {str(e)}"
            )
    
    # 3. LLM 서비스 확인
    if not llm_available():
        raise HTTPException(
            status_code=503,
            detail="AI 서비스를 사용할 수 없습니다. API 키를 확인해주세요."
        )
    
    filename = document.get("filename", "")
    
    try:
        logger.info(f"🤖 AI 분석 시작: {filename}")
        
        # 4. 문서 유형 감지
        doc_type = detect_document_type(extracted_text, filename)
        logger.info(f"📋 감지된 문서 유형: {doc_type.value}")
        
        # 5. 유형별 맞춤 프롬프트로 분석
        prompt = get_analysis_prompt(extracted_text, doc_type, filename)
        llm_result = generate_json(prompt)
        
        if not llm_result:
            raise ValueError("LLM 분석 결과가 비어있습니다")
        
        # 6. 분석 결과 구조화
        analysis_result = {
            "document_id": document_id,
            "summary": llm_result.get("summary", "요약 생성 실패"),
            "document_type": llm_result.get("document_type", doc_type.value),
            "importance": llm_result.get("importance", "medium"),
            "key_points": llm_result.get("key_points", []),
            "actions": [
                ActionItem(
                    action=action.get("action", ""),
                    deadline=action.get("deadline"),
                    amount=action.get("amount"),
                    method=action.get("method")
                )
                for action in llm_result.get("actions", [])
            ]
        }
        
        # 7. 추가 세부 정보 (문서 유형별)
        extra_details = {}
        for key in ["tax_details", "prescription_details", "contract_details", 
                    "notice_details", "insurance_details"]:
            if key in llm_result:
                extra_details[key] = llm_result[key]
        
        if extra_details:
            analysis_result["details"] = extra_details
        
        # 8. DB에 분석 결과 저장
        mock_db.update_document(
            document_id,
            {
                "status": "analyzed",
                "analysis_result": analysis_result,
                "document_type": doc_type.value
            }
        )
        
        # 9. 백그라운드에서 RAG 인덱싱
        background_tasks.add_task(
            _index_document_for_rag,
            document_id,
            extracted_text,
            doc_type.value
        )
        
        logger.info(f"✅ AI 분석 완료: {document_id}")
        
        return AnalyzeResponse(**analysis_result)
        
    except ValueError as e:
        logger.error(f"❌ 설정 오류: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail=f"AI 분석 설정 오류: {str(e)}"
        )
    
    except Exception as e:
        logger.error(f"❌ 분석 실패: {str(e)}")
        
        # 분석 실패 상태 저장
        mock_db.update_document(
            document_id,
            {"status": "analysis_failed", "error": str(e)}
        )
        
        raise HTTPException(
            status_code=500,
            detail=f"문서 분석 중 오류 발생: {str(e)}"
        )


async def _index_document_for_rag(document_id: str, text: str, doc_type: str):
    """
    백그라운드 RAG 인덱싱
    """
    try:
        logger.info(f"📚 RAG 인덱싱 시작: {document_id}")
        
        rag = get_rag_system()
        
        if rag.has_document(document_id):
            logger.info(f"⏭️ 이미 인덱싱됨: {document_id}")
            return
        
        chunks = _chunker.chunk(text, document_id)
        
        chunk_count = rag.add_document(
            document_id,
            text,
            metadata={"document_type": doc_type}
        )
        
        mock_db.update_document(
            document_id,
            {
                "rag_indexed": True,
                "chunk_count": chunk_count
            }
        )
        
        logger.info(f"✅ RAG 인덱싱 완료: {chunk_count}개 청크")
        
    except Exception as e:
        logger.error(f"❌ RAG 인덱싱 실패: {e}")


@router.get("/status/{document_id}")
async def get_analysis_status(document_id: str):
    """
    분석 상태 조회
    """
    document = mock_db.get_document(document_id)
    
    if not document:
        raise HTTPException(
            status_code=404,
            detail=f"문서를 찾을 수 없습니다: {document_id}"
        )
    
    rag = get_rag_system()
    rag_indexed = rag.has_document(document_id)
    
    return {
        "document_id": document_id,
        "filename": document.get("filename"),
        "status": document["status"],
        "document_type": document.get("document_type"),
        "has_analysis": document.get("analysis_result") is not None,
        "has_text": document.get("extracted_text") is not None,
        "rag_indexed": rag_indexed,
        "chunk_count": document.get("chunk_count", 0)
    }


@router.post("/reanalyze/{document_id}")
async def reanalyze_document(
    document_id: str,
    background_tasks: BackgroundTasks,
    force_type: Optional[str] = None
):
    """
    문서 재분석
    """
    document = mock_db.get_document(document_id)
    
    if not document:
        raise HTTPException(
            status_code=404,
            detail=f"문서를 찾을 수 없습니다: {document_id}"
        )
    
    extracted_text = document.get("extracted_text")
    
    if not extracted_text:
        raise HTTPException(
            status_code=400,
            detail="문서 텍스트가 없습니다."
        )
    
    mock_db.update_document(document_id, {"status": "reanalyzing"})
    
    rag = get_rag_system()
    rag.remove_document(document_id)
    
    request = AnalyzeRequest(document_id=document_id)
    return await analyze_document(request, background_tasks)


@router.get("/types")
async def get_supported_document_types():
    """
    지원되는 문서 유형 목록
    """
    return {
        "supported_types": [
            {"code": dt.name, "name": dt.value}
            for dt in DocumentType
        ],
        "total": len(DocumentType)
    }