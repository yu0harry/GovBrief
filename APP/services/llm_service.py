"""
LLM 서비스 모듈
Gemini API 호출을 통합 관리

역할:
- Gemini 모델 초기화 및 관리
- 텍스트 생성 (요약, 분석, 채팅)
- 임베딩 생성
- 에러 핸들링 및 재시도
"""
import os
import json
import logging
from typing import Dict, List, Optional, Any
from dotenv import load_dotenv

load_dotenv()

logger = logging.getLogger(__name__)

# ============================================
# Gemini 설정
# ============================================
GOOGLE_API_KEY = os.environ.get("GOOGLE_API_KEY")

# 모델 설정
CHAT_MODEL = "gemini-2.0-flash"
EMBEDDING_MODEL = "models/text-embedding-004"

# 전역 모델 인스턴스 (싱글톤)
_chat_model = None
_genai = None


def _init_gemini():
    """Gemini 초기화 (한 번만 실행)"""
    global _chat_model, _genai
    
    if _genai is not None:
        return True
    
    if not GOOGLE_API_KEY:
        logger.error("❌ GOOGLE_API_KEY가 설정되지 않았습니다")
        return False
    
    try:
        import google.generativeai as genai
        genai.configure(api_key=GOOGLE_API_KEY)
        _genai = genai
        _chat_model = genai.GenerativeModel(CHAT_MODEL)
        logger.info(f"✅ Gemini 초기화 완료: {CHAT_MODEL}")
        return True
    except Exception as e:
        logger.error(f"❌ Gemini 초기화 실패: {e}")
        return False


def is_available() -> bool:
    """LLM 서비스 사용 가능 여부"""
    return _init_gemini()


# ============================================
# 텍스트 생성 함수들
# ============================================

def generate_text(prompt: str, max_retries: int = 2) -> Optional[str]:
    """
    텍스트 생성 (범용)
    
    Args:
        prompt: 프롬프트
        max_retries: 재시도 횟수
        
    Returns:
        생성된 텍스트 또는 None
    """
    if not _init_gemini():
        raise ValueError("Gemini API가 초기화되지 않았습니다")
    
    for attempt in range(max_retries + 1):
        try:
            response = _chat_model.generate_content(prompt)
            return response.text.strip()
        except Exception as e:
            logger.warning(f"⚠️ 생성 실패 (시도 {attempt + 1}): {e}")
            if attempt == max_retries:
                raise
    
    return None


def generate_json(prompt: str, max_retries: int = 2) -> Optional[Dict]:
    """
    JSON 형식 응답 생성
    
    Args:
        prompt: JSON 반환을 요청하는 프롬프트
        max_retries: 재시도 횟수
        
    Returns:
        파싱된 JSON 딕셔너리 또는 None
    """
    text = generate_text(prompt, max_retries)
    
    if not text:
        return None
    
    # 마크다운 코드 블록 제거
    text = text.replace("```json", "").replace("```", "").strip()
    
    try:
        return json.loads(text)
    except json.JSONDecodeError as e:
        logger.error(f"❌ JSON 파싱 실패: {e}")
        logger.debug(f"원본 응답: {text[:500]}")
        return None


# ============================================
# 임베딩 함수
# ============================================

def generate_embedding(text: str, task_type: str = "retrieval_document") -> Optional[List[float]]:
    """
    단일 텍스트 임베딩 생성
    
    Args:
        text: 임베딩할 텍스트
        task_type: "retrieval_document" 또는 "retrieval_query"
        
    Returns:
        임베딩 벡터 (768차원)
    """
    if not _init_gemini():
        raise ValueError("Gemini API가 초기화되지 않았습니다")
    
    try:
        result = _genai.embed_content(
            model=EMBEDDING_MODEL,
            content=text,
            task_type=task_type
        )
        return result['embedding']
    except Exception as e:
        logger.error(f"❌ 임베딩 생성 실패: {e}")
        return None


def generate_embeddings(texts: List[str], task_type: str = "retrieval_document") -> Optional[List[List[float]]]:
    """
    다중 텍스트 임베딩 생성 (배치)
    
    Args:
        texts: 임베딩할 텍스트 리스트
        task_type: "retrieval_document" 또는 "retrieval_query"
        
    Returns:
        임베딩 벡터 리스트
    """
    if not _init_gemini():
        raise ValueError("Gemini API가 초기화되지 않았습니다")
    
    try:
        result = _genai.embed_content(
            model=EMBEDDING_MODEL,
            content=texts,
            task_type=task_type
        )
        return result['embedding']
    except Exception as e:
        logger.error(f"❌ 배치 임베딩 생성 실패: {e}")
        return None

# ============================================
# 채팅 함수 (RAG용)
# ============================================

def chat_with_context(
    question: str,
    context: str,
    history: List[Dict] = None,
    max_retries: int = 2
) -> str:
    """
    컨텍스트 기반 채팅 (RAG용)
    
    Args:
        question: 사용자 질문
        context: 검색된 문서 컨텍스트
        history: 대화 히스토리 [{"role": "user/assistant", "content": "..."}]
        max_retries: 재시도 횟수
        
    Returns:
        AI 답변
    """
    if not _init_gemini():
        raise ValueError("Gemini API가 초기화되지 않았습니다")
    
    # 1. 히스토리 포맷팅 (최근 5개만)
    history_text = ""
    if history:
        recent_history = history[-5:]  # 최근 5개 대화만
        for msg in recent_history:
            role = "사용자" if msg["role"] == "user" else "AI"
            content = msg["content"]
            history_text += f"{role}: {content}\n"
    
    # 2. 프롬프트 구성
    prompt = f"""아래 [문서 내용]을 참고하여 [질문]에 답변해주세요.

[문서 내용]
{context}

{f"[이전 대화]\\n{history_text}\\n" if history_text else ""}[질문]
{question}

[답변 지침]
- 문서 내용에 기반하여 정확하게 답변하세요
- 문서에 없는 내용은 "문서에서 해당 정보를 찾을 수 없습니다"라고 답변하세요
- 간결하고 명확하게 답변하세요
- 필요하면 문서의 구체적인 내용을 인용하세요

[답변]"""
    
    # 3. LLM 호출
    return generate_text(prompt, max_retries)

# ============================================
# 문서 분석 함수
# ============================================

def analyze_document(text: str, doc_type: str = None) -> Optional[Dict]:
    """
    문서 분석 (요약 + 분류)
    
    Args:
        text: 문서 텍스트
        doc_type: 문서 유형 (선택)
        
    Returns:
        분석 결과 딕셔너리
    """
    from APP.services.prompts import get_analysis_prompt, detect_document_type, DocumentType
    
    # 문서 유형 감지
    if doc_type:
        try:
            doc_type_enum = DocumentType[doc_type.upper()]
        except KeyError:
            doc_type_enum = DocumentType.UNKNOWN
    else:
        doc_type_enum = detect_document_type(text)
    
    # 분석 프롬프트 생성
    prompt = get_analysis_prompt(text, doc_type_enum)
    
    # LLM 분석
    return generate_json(prompt)

# ============================================
# 테스트
# ============================================

if __name__ == "__main__":
    print("=" * 60)
    print("LLM Service 테스트")
    print("=" * 60)
    
    if is_available():
        print("✅ Gemini API 사용 가능\n")
        
        # 텍스트 생성 테스트
        result = generate_text("안녕하세요. 짧게 인사해주세요.")
        print(f"텍스트 생성: {result}\n")
        
        # 임베딩 테스트
        embedding = generate_embedding("테스트 문장입니다.")
        print(f"임베딩 차원: {len(embedding) if embedding else 'N/A'}")
    else:
        print("❌ Gemini API 사용 불가 - API 키를 확인하세요")