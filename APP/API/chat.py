"""
챗봇 Q&A API (v2)

개선사항:
- RAG 연동
- 문서 유형별 맞춤 응답
- 소스 하이라이트 제공
- 대화 히스토리 관리
"""
from fastapi import APIRouter, HTTPException
import logging
from typing import Optional, List, Dict

from APP.schemas.chat import ChatRequest, ChatResponse  # ✅ 추가!
from APP.db.mock_db import mock_db
from APP.services.rag_service import get_rag_system, add_document
from APP.services.prompts import detect_document_type

logger = logging.getLogger(__name__)

router = APIRouter()

# 대화 히스토리 저장 (메모리)
_chat_history: Dict[str, List[Dict]] = {}


@router.post("/chat", response_model=ChatResponse)
async def chat_with_document(request: ChatRequest):
    """
    문서 기반 Q&A (RAG v2) + 텍스트 세탁 기능 추가됨
    """
    print(f"🚀 [Chat] 요청 도착: DocID={request.document_id}, Q={request.question}")

    document_id = request.document_id
    question = request.question.strip()
    
    if not question:
        raise HTTPException(status_code=400, detail="질문을 입력해주세요.")
    
    # 1. 문서 확인
    document = mock_db.get_document(document_id)
    
    if not document:
        raise HTTPException(status_code=404, detail=f"문서를 찾을 수 없습니다: {document_id}")
    
    if document["status"] not in ["completed", "analyzed"]:
        raise HTTPException(status_code=400, detail="문서 분석이 완료되지 않았습니다.")
    
    # 2. RAG 시스템 가져오기
    try:
        rag = get_rag_system()
    except Exception as e:
        logger.error(f"RAG 시스템 로드 실패: {e}")
        raise HTTPException(status_code=500, detail="AI 시스템 연결 실패")
    
    # 3. 인덱싱 확인 및 텍스트 세탁 (핵심 수정 부분! ✨)
    if not rag.has_document(document_id):
        print(f"📥 [Chat] 문서 인덱싱 시작: {document_id}")
        extracted_text = document.get("extracted_text")
        
        if extracted_text:
            # ✅ [Fix] 특수문자(\u200b 등) 제거하여 AI가 텍스트를 잘 읽도록 수정
            cleaned_text = extracted_text.replace("\u200b", "").replace("\xa0", " ").strip()
            print(f"✨ [Chat] 텍스트 세탁 완료: {len(extracted_text)}자 -> {len(cleaned_text)}자")
            
            # 깨끗해진 텍스트로 저장
            add_document(document_id, cleaned_text)
        else:
            raise HTTPException(status_code=400, detail="문서 텍스트가 없습니다.")
    
    # 4. 히스토리 가져오기
    history = _chat_history.get(document_id, [])
    
    # 5. RAG 질의
    try:
        logger.info(f"💬 질의: {question[:50]}...")
        
        result = rag.query(
            document_id=document_id,
            question=question,
            history=history
        )
        
        answer = result["answer"]
        confidence = result.get("confidence", 0.0)
        
        logger.info(f"✅ 답변 생성 완료 (신뢰도: {confidence})")
        
    except Exception as e:
        logger.error(f"❌ 질의 실패: {e}")
        # 디버깅을 위해 상세 에러 출력
        import traceback
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=f"답변 생성 실패: {str(e)}")
    
    # 6. 히스토리 업데이트
    if document_id not in _chat_history:
        _chat_history[document_id] = []
    
    _chat_history[document_id].append({"role": "user", "content": question})
    _chat_history[document_id].append({"role": "assistant", "content": answer})
    
    # 최대 30개 메시지 유지
    if len(_chat_history[document_id]) > 30:
        _chat_history[document_id] = _chat_history[document_id][-30:]
    
    # 7. 응답
    return ChatResponse(
        answer=answer,
        source="document",
        confidence=confidence
    )


@router.post("/chat/extended")
async def chat_with_document_extended(request: ChatRequest):
    """
    확장 채팅 응답 (소스 정보 포함)
    
    기본 채팅 + 소스 하이라이트, 문서 유형 정보
    """
    document_id = request.document_id
    question = request.question.strip()
    
    if not question:
        raise HTTPException(status_code=400, detail="질문을 입력해주세요.")
    
    document = mock_db.get_document(document_id)
    if not document:
        raise HTTPException(status_code=404, detail="문서를 찾을 수 없습니다.")
    
    rag = get_rag_system()
    
    # 인덱싱 확인
    if not rag.has_document(document_id):
        extracted_text = document.get("extracted_text")
        if extracted_text:
            add_document(document_id, extracted_text)
    
    history = _chat_history.get(document_id, [])
    
    result = rag.query(
        document_id=document_id,
        question=question,
        history=history
    )
    
    # 히스토리 업데이트
    if document_id not in _chat_history:
        _chat_history[document_id] = []
    _chat_history[document_id].append({"role": "user", "content": question})
    _chat_history[document_id].append({"role": "assistant", "content": result["answer"]})
    
    return {
        "answer": result["answer"],
        "confidence": result["confidence"],
        "sources": result.get("sources", []),
        "history_length": len(_chat_history.get(document_id, []))
    }


@router.get("/chat/history/{document_id}")
async def get_chat_history(document_id: str, limit: int = 20):
    """대화 히스토리 조회"""
    document = mock_db.get_document(document_id)
    if not document:
        raise HTTPException(status_code=404, detail="문서를 찾을 수 없습니다.")
    
    history = _chat_history.get(document_id, [])
    
    return {
        "document_id": document_id,
        "message_count": len(history),
        "history": history[-limit:] if limit else history
    }


@router.delete("/chat/history/{document_id}")
async def clear_chat_history(document_id: str):
    """대화 히스토리 삭제"""
    if document_id in _chat_history:
        del _chat_history[document_id]
        logger.info(f"🗑️ 히스토리 삭제: {document_id}")
    
    return {"message": "대화 히스토리가 삭제되었습니다.", "document_id": document_id}


@router.get("/chat/stats")
async def get_chat_stats():
    """채팅 통계"""
    rag = get_rag_system()
    rag_stats = rag.get_stats()
    
    total_messages = sum(len(h) for h in _chat_history.values())
    
    return {
        "rag": rag_stats,
        "chat": {
            "active_conversations": len(_chat_history),
            "total_messages": total_messages
        }
    }


@router.post("/chat/feedback")
async def submit_chat_feedback(
    document_id: str,
    message_index: int,
    rating: int,
    comment: Optional[str] = None
):
    """
    채팅 피드백 제출
    
    - rating: 1-5 (1=불만족, 5=매우 만족)
    """
    if rating < 1 or rating > 5:
        raise HTTPException(status_code=400, detail="rating은 1-5 사이여야 합니다.")
    
    # TODO: 피드백 저장 (현재는 로깅만)
    logger.info(f"📝 피드백: doc={document_id}, msg={message_index}, rating={rating}")
    
    return {
        "message": "피드백이 제출되었습니다.",
        "document_id": document_id,
        "rating": rating
    }
    