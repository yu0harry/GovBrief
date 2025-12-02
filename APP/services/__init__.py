"""
Services 패키지

문서 처리, AI 분석, RAG 시스템 등 비즈니스 로직 모듈

모듈 구조:
- llm_service: LLM API 호출 (Gemini)
- rag_service: RAG 시스템 (검색 증강 생성)
- analysis_service: 문서 분석 오케스트레이션
- document_parser: 문서 파싱 (PDF, DOCX, HWP, 이미지)
"""

# LLM 서비스
from APP.services.llm_service import (
    is_available as llm_available,
    generate_text,
    generate_json,
    generate_embedding,
    generate_embeddings,
    analyze_document as llm_analyze_document,
    chat_with_context,
)

# RAG 서비스
from APP.services.rag_service import (
    RAGSystem,
    get_rag_system,
    add_document as rag_add_document,
    query_document as rag_query_document,
)

# 분석 서비스
from APP.services.analysis_service import (
    analyze_document_with_llm,
    analyze_and_index,
    extract_key_info,
)

# 문서 파서
from APP.services.document_parser import (
    parse_document,
    DocumentParserFactory,
)

__all__ = [
    # LLM
    "llm_available",
    "generate_text",
    "generate_json",
    "generate_embedding",
    "generate_embeddings",
    "llm_analyze_document",
    "chat_with_context",
    
    # RAG
    "RAGSystem",
    "get_rag_system",
    "rag_add_document",
    "rag_query_document",
    
    # Analysis
    "analyze_document_with_llm",
    "analyze_and_index",
    "extract_key_info",
    
    # Parser
    "parse_document",
    "DocumentParserFactory",
]