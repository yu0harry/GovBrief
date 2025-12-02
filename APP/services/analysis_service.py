"""
문서 분석 서비스 (리팩토링)

역할:
- 문서 분석 오케스트레이션
- LLM 서비스를 사용한 요약/분석
- 정규식 기반 정보 추출 (보조)

의존성:
- llm_service.py: LLM API 호출
- rag_service.py: RAG 시스템 (채팅용)
"""
import re
import logging
from typing import Dict, List, Optional
from datetime import datetime

from APP.services.llm_service import (
    analyze_document as llm_analyze,
    is_available as llm_available
)
from APP.services.rag_service import add_document, get_rag_system

logger = logging.getLogger(__name__)


# ============================================
# 메인 분석 함수
# ============================================

def analyze_document_with_llm(text: str, filename: str) -> Dict:
    """
    LLM을 사용한 문서 분석
    
    Args:
        text: 파싱된 문서 텍스트
        filename: 파일명
        
    Returns:
        구조화된 분석 결과:
        {
            "summary": str,
            "document_type": str,
            "importance": str,
            "key_points": List[str],
            "actions": List[Dict]
        }
    """
    if not llm_available():
        logger.warning("⚠️ LLM 서비스 불가 - 기본 분석 사용")
        return _fallback_analysis(text, filename)
    
    try:
        # LLM 분석 실행
        result = llm_analyze(text, filename)
        
        # 정규식으로 추가 정보 보강
        extracted = extract_key_info(text)
        result["extracted_entities"] = extracted
        
        logger.info(f"✅ 문서 분석 완료: {filename}")
        return result
        
    except Exception as e:
        logger.error(f"❌ LLM 분석 실패: {e}")
        return _fallback_analysis(text, filename)


def analyze_and_index(document_id: str, text: str, filename: str) -> Dict:
    """
    문서 분석 + RAG 인덱싱
    
    분석과 동시에 RAG 시스템에 문서를 추가하여
    이후 채팅에서 사용할 수 있도록 합니다.
    
    Args:
        document_id: 문서 ID
        text: 문서 텍스트
        filename: 파일명
        
    Returns:
        분석 결과 (+ chunk_count 포함)
    """
    # 1. 문서 분석
    result = analyze_document_with_llm(text, filename)
    
    # 2. RAG 인덱싱 (비동기 가능)
    try:
        chunk_count = add_document(document_id, text)
        result["rag_indexed"] = True
        result["chunk_count"] = chunk_count
        logger.info(f"✅ RAG 인덱싱 완료: {chunk_count}개 청크")
    except Exception as e:
        logger.warning(f"⚠️ RAG 인덱싱 실패: {e}")
        result["rag_indexed"] = False
        result["chunk_count"] = 0
    
    return result


# ============================================
# 정규식 기반 정보 추출
# ============================================

def extract_key_info(text: str) -> Dict:
    """
    정규식으로 주요 정보 추출
    
    Args:
        text: 문서 텍스트
        
    Returns:
        {
            "dates": [...],
            "amounts": [...],
            "phone_numbers": [...],
            "accounts": [...]
        }
    """
    info = {
        "dates": [],
        "amounts": [],
        "phone_numbers": [],
        "accounts": []
    }
    
    # 날짜 추출
    date_patterns = [
        r'(\d{4})년\s*(\d{1,2})월\s*(\d{1,2})일',  # 2025년 3월 15일
        r'(\d{4})[./-](\d{1,2})[./-](\d{1,2})',     # 2025.03.15, 2025-03-15
    ]
    
    for pattern in date_patterns:
        matches = re.findall(pattern, text)
        for match in matches:
            try:
                year, month, day = int(match[0]), int(match[1]), int(match[2])
                date_str = f"{year:04d}-{month:02d}-{day:02d}"
                if date_str not in info["dates"]:
                    info["dates"].append(date_str)
            except (ValueError, IndexError):
                continue
    
    # 금액 추출
    amount_patterns = [
        r'(\d{1,3}(?:,\d{3})+)\s*원',  # 1,000,000원
        r'(\d+)\s*원',                   # 10000원
    ]
    
    for pattern in amount_patterns:
        matches = re.findall(pattern, text)
        for match in matches:
            amount_str = match.replace(',', '')
            if amount_str.isdigit():
                amount = int(amount_str)
                if amount not in info["amounts"] and amount >= 100:  # 100원 이상만
                    info["amounts"].append(amount)
    
    # 전화번호 추출
    phone_pattern = r'(\d{2,3})-(\d{3,4})-(\d{4})'
    matches = re.findall(phone_pattern, text)
    for match in matches:
        phone = f"{match[0]}-{match[1]}-{match[2]}"
        if phone not in info["phone_numbers"]:
            info["phone_numbers"].append(phone)
    
    # 계좌번호 추출 (간단한 패턴)
    account_pattern = r'(\d{3,4})-(\d{2,4})-(\d{4,6})'
    matches = re.findall(account_pattern, text)
    for match in matches:
        account = f"{match[0]}-{match[1]}-{match[2]}"
        # 전화번호와 구분 (자릿수로)
        if len(account.replace('-', '')) >= 10 and account not in info["accounts"]:
            info["accounts"].append(account)
    
    return info


def extract_action_items(text: str) -> List[Dict]:
    """
    행동 항목 추출 (정규식 기반)
    
    LLM 분석 실패 시 폴백으로 사용
    """
    actions = []
    info = extract_key_info(text)
    
    # 납부/제출 관련 키워드 탐지
    action_keywords = {
        "납부": ["납부", "지불", "송금", "입금"],
        "제출": ["제출", "신청", "접수", "등록"],
        "방문": ["방문", "출석", "참석"],
        "연락": ["연락", "문의", "전화"],
    }
    
    for action_type, keywords in action_keywords.items():
        for keyword in keywords:
            if keyword in text:
                action = {
                    "action": f"{action_type} 필요",
                    "deadline": info["dates"][0] if info["dates"] else None,
                    "amount": info["amounts"][0] if info["amounts"] and action_type == "납부" else None,
                    "method": None
                }
                actions.append(action)
                break  # 한 유형당 하나만
    
    return actions


# ============================================
# 폴백 분석 (LLM 실패 시)
# ============================================

def _fallback_analysis(text: str, filename: str) -> Dict:
    """LLM 없이 기본 분석"""
    info = extract_key_info(text)
    actions = extract_action_items(text)
    
    # 문서 유형 추측
    doc_type = _guess_document_type(filename, text)
    
    # 요약 생성 (첫 500자)
    summary = text[:500].strip()
    if len(text) > 500:
        summary += "..."
    
    # 중요도 판단
    importance = "medium"
    if info["amounts"] and max(info["amounts"]) > 100000:
        importance = "high"
    if any(keyword in text for keyword in ["긴급", "즉시", "마감"]):
        importance = "high"
    
    return {
        "summary": summary,
        "document_type": doc_type,
        "importance": importance,
        "key_points": [
            f"날짜: {', '.join(info['dates'][:3])}" if info['dates'] else "날짜 정보 없음",
            f"금액: {', '.join(str(a) + '원' for a in info['amounts'][:3])}" if info['amounts'] else "금액 정보 없음",
            f"연락처: {', '.join(info['phone_numbers'][:2])}" if info['phone_numbers'] else "연락처 정보 없음",
        ],
        "actions": actions,
        "extracted_entities": info
    }


def _guess_document_type(filename: str, text: str = "") -> str:
    """파일명과 내용으로 문서 유형 추측"""
    combined = (filename + " " + text[:1000]).lower()
    
    type_keywords = {
        "세금고지서": ["세금", "납세", "과세", "지방세", "국세", "고지"],
        "전자처방전": ["처방", "의약품", "조제", "약국", "복용"],
        "통지서": ["통지", "안내", "알림", "공고"],
        "계약서": ["계약", "약정", "합의", "동의"],
        "증명서": ["증명", "확인서", "발급"],
        "신청서": ["신청", "접수", "등록"],
        "청구서": ["청구", "요금", "이용료"],
    }
    
    for doc_type, keywords in type_keywords.items():
        if any(kw in combined for kw in keywords):
            return doc_type
    
    return "공공문서"


# ============================================
# 테스트
# ============================================

if __name__ == "__main__":
    print("=" * 60)
    print("Analysis Service 테스트")
    print("=" * 60)
    
    test_text = """
    지방세 납부 고지서
    
    납세자: 홍길동
    주소: 서울시 강남구
    
    납부 기한: 2025년 3월 31일
    납부 금액: 250,000원
    
    납부 방법:
    - 위택스 (www.wetax.go.kr)
    - 은행 방문 납부
    - 가상계좌: 123-456-789012
    
    문의: 세무과 02-1234-5678
    
    기한 내 미납 시 가산세가 부과됩니다.
    """
    
    # 정규식 추출 테스트
    print("\n📌 정규식 추출 결과:")
    info = extract_key_info(test_text)
    print(f"  날짜: {info['dates']}")
    print(f"  금액: {info['amounts']}")
    print(f"  전화: {info['phone_numbers']}")
    
    # LLM 분석 테스트
    print("\n📌 LLM 분석 결과:")
    result = analyze_document_with_llm(test_text, "세금고지서.pdf")
    print(f"  유형: {result['document_type']}")
    print(f"  중요도: {result['importance']}")
    print(f"  요약: {result['summary'][:100]}...")