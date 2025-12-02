"""
RAG (Retrieval-Augmented Generation) 서비스

역할:
- 문서 청킹 (SmartChunker 사용)
- 벡터 임베딩 생성 및 저장
- 유사도 검색
- 컨텍스트 기반 답변 생성
"""
import logging
import re  # ✅ [필수] 정규표현식(강력 세탁용)
from typing import Dict, List, Optional
from dataclasses import dataclass, field
import numpy as np

from APP.services.llm_service import (
    generate_embeddings,
    generate_embedding,
    chat_with_context,
    is_available
)
from APP.services.chunker import SmartChunker, ChunkingConfig, Chunk

logger = logging.getLogger(__name__)


# ============================================
# 데이터 클래스
# ============================================

@dataclass
class SearchResult:
    """검색 결과"""
    chunk: Chunk
    score: float


# ============================================
# RAG 시스템 클래스
# ============================================

class RAGSystem:
    def __init__(
        self,
        chunk_size: int = 1500,  # ✅ [수정] 1페이지를 통째로 인식하도록 크기 증가
        chunk_overlap: int = 300, # ✅ [수정] 문맥 끊김 방지
        top_k: int = 3
    ):
        self.top_k = top_k
        
        # SmartChunker 초기화
        self.chunker = SmartChunker(ChunkingConfig(
            chunk_size=chunk_size,
            chunk_overlap=chunk_overlap,
            preserve_tables=True,
            preserve_titles=True,
            sentence_boundary=True
        ))
        
        self._storage: Dict[str, Dict] = {}
        logger.info(f"RAG 시스템 초기화: chunk_size={chunk_size}, overlap={chunk_overlap}")
    
    # ============================================
    # 문서 처리
    # ============================================
    
    def add_document(self, document_id: str, text: str, metadata: Dict = None) -> int:
        if not is_available():
            raise ValueError("LLM 서비스를 사용할 수 없습니다")
        
        # ✅ [핵심 수정] 텍스트 강력 세탁 (줄바꿈, 이상한 공백 싹 정리)
        if text:
            # 1. 투명 특수문자 제거
            text = text.replace("\u200b", "").replace("\xa0", " ")
            # 2. 과도한 줄바꿈/공백을 공백 하나로 통일 (PDF 인식률 200% 상승 비법)
            text = re.sub(r'\s+', ' ', text).strip()
            
            print(f"🧹 [DEBUG] 텍스트 강력 세탁 완료: {text[:100]}...")  # 로그로 확인

        chunks = self.chunker.chunk(text, document_id)
        
        if not chunks:
            logger.warning(f"⚠️ 문서 {document_id}: 청크 생성 실패")
            return 0
        
        if metadata:
            for chunk in chunks:
                chunk.metadata.update(metadata)
        
        chunk_texts = [c.text for c in chunks]
        embeddings = generate_embeddings(chunk_texts, task_type="retrieval_document")
        
        if embeddings is None:
            logger.error(f"❌ 문서 {document_id}: 임베딩 생성 실패")
            return 0
        
        self._storage[document_id] = {
            "chunks": chunks,
            "embeddings": np.array(embeddings)
        }
        
        logger.info(f"✅ 문서 {document_id}: {len(chunks)}개 청크 저장 완료")
        return len(chunks)
    
    def remove_document(self, document_id: str) -> bool:
        if document_id in self._storage:
            del self._storage[document_id]
            return True
        return False
    
    def has_document(self, document_id: str) -> bool:
        return document_id in self._storage

    # ============================================
    # 검색 및 질의
    # ============================================

    def search(self, document_id: str, query: str, top_k: int = None) -> List[SearchResult]:
        if document_id not in self._storage:
            return []
        
        top_k = top_k or self.top_k
        query_embedding = generate_embedding(query, task_type="retrieval_query")
        if query_embedding is None:
            return []
        
        query_vec = np.array(query_embedding)
        doc_data = self._storage[document_id]
        embeddings = doc_data["embeddings"]
        chunks = doc_data["chunks"]
        
        similarities = self._cosine_similarity(query_vec, embeddings)
        top_indices = np.argsort(similarities)[::-1][:top_k]
        
        results = []
        for idx in top_indices:
            results.append(SearchResult(
                chunk=chunks[idx],
                score=float(similarities[idx])
            ))
        return results

    def query(
        self,
        document_id: str,
        question: str,
        history: List[Dict] = None
    ) -> Dict:
        # 1. 관련 청크 검색
        results = self.search(document_id, question)
        
        if not results:
            return {
                "answer": "문서에서 관련 정보를 찾을 수 없습니다.",
                "sources": [],
                "confidence": 0.0
            }
        
        # 2. 컨텍스트 구성
        context = "\n\n".join([r.chunk.text for r in results])
        
        # ✅ [디버깅 추가] AI가 실제로 읽는 내용 눈으로 확인하기
        print("="*50)
        print(f"🧐 [DEBUG] AI에게 들어가는 컨텍스트 내용:\n{context[:500]}...") # 너무 길면 잘라서 보여줌
        print("="*50)
        
        # 3. 답변 생성
        answer = chat_with_context(question, context, history)
        
        # 4. 신뢰도 계산
        avg_score = sum(r.score for r in results) / len(results)
        
        return {
            "answer": answer,
            "sources": [
                {
                    "text": r.chunk.text[:200],
                    "score": r.score,
                    "chunk_type": r.chunk.chunk_type.value,
                    "index": r.chunk.index
                }
                for r in results
            ],
            "confidence": round(avg_score, 2)
        }
    
    def _cosine_similarity(self, query_vec: np.ndarray, doc_vecs: np.ndarray) -> np.ndarray:
        query_norm = query_vec / np.linalg.norm(query_vec)
        doc_norms = doc_vecs / np.linalg.norm(doc_vecs, axis=1, keepdims=True)
        return np.dot(doc_norms, query_norm)
    
    def get_stats(self) -> Dict:
        total_chunks = sum(len(data["chunks"]) for data in self._storage.values())
        return {
            "document_count": len(self._storage),
            "total_chunks": total_chunks,
            "documents": list(self._storage.keys()),
            "chunker_config": {
                "chunk_size": self.chunker.config.chunk_size,
                "chunk_overlap": self.chunker.config.chunk_overlap,
                "preserve_tables": self.chunker.config.preserve_tables
            }
        }

# ============================================
# 전역 인스턴스 (싱글톤)
# ============================================

_rag_instance: Optional[RAGSystem] = None

def get_rag_system() -> RAGSystem:
    global _rag_instance
    if _rag_instance is None:
        _rag_instance = RAGSystem()
    return _rag_instance

def add_document(document_id: str, text: str) -> int:
    return get_rag_system().add_document(document_id, text)

def query_document(document_id: str, question: str) -> Dict:
    return get_rag_system().query(document_id, question)