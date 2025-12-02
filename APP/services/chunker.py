"""
고품질 문서 청킹 모듈

기능:
- 의미 단위 분할 (문장/문단 경계 인식)
- 테이블 데이터 보존
- 제목/소제목 기반 분할
- 중첩(overlap) 최적화
- 메타데이터 보존
"""
import re
import logging
from typing import List, Dict, Optional, Tuple
from dataclasses import dataclass, field
from enum import Enum

logger = logging.getLogger(__name__)


class ChunkType(Enum):
    """청크 유형"""
    PARAGRAPH = "paragraph"
    TABLE = "table"
    TITLE = "title"
    LIST = "list"
    MIXED = "mixed"


@dataclass
class Chunk:
    """청크 데이터 클래스"""
    text: str
    index: int
    chunk_type: ChunkType = ChunkType.PARAGRAPH
    start_char: int = 0
    end_char: int = 0
    metadata: Dict = field(default_factory=dict)
    
    @property
    def length(self) -> int:
        return len(self.text)


@dataclass
class ChunkingConfig:
    """청킹 설정"""
    chunk_size: int = 800           # 목표 청크 크기
    chunk_overlap: int = 150        # 중첩 크기
    min_chunk_size: int = 100       # 최소 청크 크기
    max_chunk_size: int = 1500      # 최대 청크 크기
    preserve_tables: bool = True    # 테이블 보존
    preserve_titles: bool = True    # 제목 보존
    sentence_boundary: bool = True  # 문장 경계 분할


class SmartChunker:
    """
    스마트 문서 청커
    
    의미 단위를 보존하면서 문서를 청크로 분할합니다.
    
    Usage:
        chunker = SmartChunker()
        chunks = chunker.chunk(text)
    """
    
    def __init__(self, config: ChunkingConfig = None):
        self.config = config or ChunkingConfig()
        
        # 문장 종결 패턴 (한국어 + 영어)
        self.sentence_endings = re.compile(
            r'(?<=[.!?。！？])\s+|'  # 마침표/물음표/느낌표 + 공백
            r'(?<=다\.)\s+|'        # ~다. 형태
            r'(?<=요\.)\s+|'        # ~요. 형태
            r'(?<=음\.)\s+|'        # ~음. 형태
            r'(?<=습니다\.)\s+'     # ~습니다. 형태
        )
        
        # 제목 패턴
        self.title_patterns = [
            r'^#{1,6}\s+.+$',                    # 마크다운 제목
            r'^[0-9]+\.\s+.+$',                  # 숫자. 제목
            r'^[가-힣]\.\s+.+$',                 # 가. 나. 다. 형태
            r'^[一二三四五六七八九十]+\.\s+.+$',  # 한자 숫자
            r'^【.+】$',                         # 【제목】
            r'^\[.+\]$',                         # [제목]
            r'^<.+>$',                           # <제목>
            r'^제[0-9]+조',                      # 제1조, 제2조
            r'^[0-9]+\)',                        # 1) 2) 형태
        ]
        
        # 테이블 패턴
        self.table_patterns = [
            r'\|.+\|',                           # 마크다운 테이블
            r'┌.*┐',                             # 박스 테이블 시작
            r'─{3,}',                            # 가로선
            r'\t.+\t',                           # 탭 구분 데이터
        ]
        
        # 리스트 패턴
        self.list_patterns = [
            r'^[-•●○◆◇▶▷]\s+',                  # 불릿 리스트
            r'^\d+[\.\)]\s+',                    # 번호 리스트
            r'^[가-힣][\.\)]\s+',                # 가) 나) 형태
        ]
    
    def chunk(self, text: str, document_id: str = "") -> List[Chunk]:
        """
        문서를 청크로 분할
        
        Args:
            text: 원본 텍스트
            document_id: 문서 ID (메타데이터용)
            
        Returns:
            청크 리스트
        """
        if not text or not text.strip():
            return []
        
        # 1. 텍스트 정규화
        text = self._normalize_text(text)
        
        # 2. 구조 분석 (섹션 분리)
        sections = self._split_into_sections(text)
        
        # 3. 섹션별 청킹
        all_chunks = []
        current_index = 0
        
        for section in sections:
            section_chunks = self._chunk_section(
                section["text"],
                section["type"],
                start_index=current_index,
                start_char=section["start"]
            )
            
            for chunk in section_chunks:
                chunk.metadata["document_id"] = document_id
                chunk.metadata["section_type"] = section["type"]
                all_chunks.append(chunk)
            
            current_index += len(section_chunks)
        
        # 4. 후처리 (너무 작은 청크 병합)
        all_chunks = self._merge_small_chunks(all_chunks)
        
        # 5. 인덱스 재정렬
        for i, chunk in enumerate(all_chunks):
            chunk.index = i
        
        logger.info(f"청킹 완료: {len(all_chunks)}개 청크 생성")
        return all_chunks
    
    def _normalize_text(self, text: str) -> str:
        """텍스트 정규화"""
        # 연속 공백 정리
        text = re.sub(r'[ \t]+', ' ', text)
        
        # 연속 줄바꿈 정리 (3개 이상 → 2개)
        text = re.sub(r'\n{3,}', '\n\n', text)
        
        # 특수 공백 문자 정규화
        text = text.replace('\xa0', ' ')
        text = text.replace('\u200b', '')
        
        return text.strip()
    
    def _split_into_sections(self, text: str) -> List[Dict]:
        """
        텍스트를 의미 단위 섹션으로 분리
        
        Returns:
            [{"text": "...", "type": "paragraph/table/title", "start": 0}, ...]
        """
        sections = []
        lines = text.split('\n')
        
        current_section = {"text": "", "type": "paragraph", "start": 0}
        current_pos = 0
        
        for line in lines:
            line_type = self._detect_line_type(line)
            
            # 테이블은 별도 섹션으로
            if line_type == "table":
                if current_section["text"].strip():
                    sections.append(current_section)
                
                # 테이블 시작
                table_text = line + "\n"
                table_start = current_pos
                
                current_section = {
                    "text": table_text,
                    "type": "table",
                    "start": table_start
                }
            
            # 제목은 다음 섹션의 시작점
            elif line_type == "title" and self.config.preserve_titles:
                if current_section["text"].strip():
                    sections.append(current_section)
                
                current_section = {
                    "text": line + "\n",
                    "type": "title",
                    "start": current_pos
                }
            
            # 일반 텍스트
            else:
                if current_section["type"] == "table" and line_type != "table":
                    # 테이블 종료
                    sections.append(current_section)
                    current_section = {
                        "text": line + "\n",
                        "type": "paragraph",
                        "start": current_pos
                    }
                else:
                    current_section["text"] += line + "\n"
            
            current_pos += len(line) + 1
        
        # 마지막 섹션 추가
        if current_section["text"].strip():
            sections.append(current_section)
        
        return sections
    
    def _detect_line_type(self, line: str) -> str:
        """라인 유형 감지"""
        line = line.strip()
        
        if not line:
            return "empty"
        
        # 테이블 체크
        for pattern in self.table_patterns:
            if re.search(pattern, line):
                return "table"
        
        # 제목 체크
        for pattern in self.title_patterns:
            if re.match(pattern, line):
                return "title"
        
        # 리스트 체크
        for pattern in self.list_patterns:
            if re.match(pattern, line):
                return "list"
        
        return "paragraph"
    
    def _chunk_section(
        self,
        text: str,
        section_type: str,
        start_index: int,
        start_char: int
    ) -> List[Chunk]:
        """섹션을 청크로 분할"""
        
        # 테이블은 분할하지 않음
        if section_type == "table" and self.config.preserve_tables:
            return [Chunk(
                text=text.strip(),
                index=start_index,
                chunk_type=ChunkType.TABLE,
                start_char=start_char,
                end_char=start_char + len(text),
                metadata={"is_table": True}
            )]
        
        # 짧은 텍스트는 그대로
        if len(text) <= self.config.chunk_size:
            chunk_type = ChunkType.TITLE if section_type == "title" else ChunkType.PARAGRAPH
            return [Chunk(
                text=text.strip(),
                index=start_index,
                chunk_type=chunk_type,
                start_char=start_char,
                end_char=start_char + len(text)
            )]
        
        # 문장 기반 분할
        if self.config.sentence_boundary:
            return self._split_by_sentences(text, start_index, start_char)
        else:
            return self._split_by_size(text, start_index, start_char)
    
    def _split_by_sentences(
        self,
        text: str,
        start_index: int,
        start_char: int
    ) -> List[Chunk]:
        """문장 경계 기반 분할"""
        # 문장 분리
        sentences = self.sentence_endings.split(text)
        sentences = [s.strip() for s in sentences if s.strip()]
        
        chunks = []
        current_chunk = ""
        current_start = start_char
        chunk_index = start_index
        
        for sentence in sentences:
            # 현재 청크 + 새 문장이 목표 크기 이하면 추가
            if len(current_chunk) + len(sentence) <= self.config.chunk_size:
                current_chunk += sentence + " "
            else:
                # 현재 청크 저장
                if current_chunk.strip():
                    chunks.append(Chunk(
                        text=current_chunk.strip(),
                        index=chunk_index,
                        chunk_type=ChunkType.PARAGRAPH,
                        start_char=current_start,
                        end_char=current_start + len(current_chunk)
                    ))
                    chunk_index += 1
                
                # 오버랩 적용
                overlap_text = self._get_overlap_text(current_chunk)
                current_start = current_start + len(current_chunk) - len(overlap_text)
                current_chunk = overlap_text + sentence + " "
        
        # 마지막 청크
        if current_chunk.strip():
            chunks.append(Chunk(
                text=current_chunk.strip(),
                index=chunk_index,
                chunk_type=ChunkType.PARAGRAPH,
                start_char=current_start,
                end_char=current_start + len(current_chunk)
            ))
        
        return chunks
    
    def _split_by_size(
        self,
        text: str,
        start_index: int,
        start_char: int
    ) -> List[Chunk]:
        """크기 기반 분할 (폴백)"""
        chunks = []
        start = 0
        chunk_index = start_index
        
        while start < len(text):
            end = start + self.config.chunk_size
            
            # 단어 경계에서 자르기
            if end < len(text):
                # 공백 위치 찾기
                space_pos = text.rfind(' ', start + self.config.min_chunk_size, end)
                if space_pos > start:
                    end = space_pos
            
            chunk_text = text[start:end].strip()
            
            if chunk_text:
                chunks.append(Chunk(
                    text=chunk_text,
                    index=chunk_index,
                    chunk_type=ChunkType.PARAGRAPH,
                    start_char=start_char + start,
                    end_char=start_char + end
                ))
                chunk_index += 1
            
            # 오버랩 적용
            start = end - self.config.chunk_overlap
        
        return chunks
    
    def _get_overlap_text(self, text: str) -> str:
        """오버랩 텍스트 추출 (문장 경계 유지)"""
        if len(text) <= self.config.chunk_overlap:
            return text
        
        overlap_start = len(text) - self.config.chunk_overlap
        
        # 문장 시작점 찾기
        sentence_start = text.find('. ', overlap_start)
        if sentence_start > 0 and sentence_start < len(text) - 10:
            return text[sentence_start + 2:]
        
        # 공백 위치 찾기
        space_pos = text.find(' ', overlap_start)
        if space_pos > 0:
            return text[space_pos + 1:]
        
        return text[overlap_start:]
    
    def _merge_small_chunks(self, chunks: List[Chunk]) -> List[Chunk]:
        """작은 청크 병합"""
        if not chunks:
            return chunks
        
        merged = []
        current = None
        
        for chunk in chunks:
            if current is None:
                current = chunk
                continue
            
            # 현재 청크가 너무 작으면 다음과 병합
            if current.length < self.config.min_chunk_size:
                # 테이블은 병합하지 않음
                if current.chunk_type != ChunkType.TABLE and chunk.chunk_type != ChunkType.TABLE:
                    current.text = current.text + "\n\n" + chunk.text
                    current.end_char = chunk.end_char
                    continue
            
            merged.append(current)
            current = chunk
        
        if current:
            merged.append(current)
        
        return merged


# ============================================
# 편의 함수
# ============================================

_default_chunker: Optional[SmartChunker] = None


def get_chunker(config: ChunkingConfig = None) -> SmartChunker:
    """기본 청커 인스턴스 반환"""
    global _default_chunker
    if _default_chunker is None or config is not None:
        _default_chunker = SmartChunker(config)
    return _default_chunker


def chunk_text(text: str, document_id: str = "") -> List[Chunk]:
    """텍스트 청킹 (편의 함수)"""
    return get_chunker().chunk(text, document_id)


def chunk_text_simple(text: str) -> List[str]:
    """텍스트 청킹 (문자열 리스트 반환)"""
    chunks = get_chunker().chunk(text)
    return [c.text for c in chunks]


# ============================================
# 테스트
# ============================================

if __name__ == "__main__":
    print("=" * 60)
    print("Smart Chunker 테스트")
    print("=" * 60)
    
    test_text = """
# 2025년도 지방세 납부 안내

## 1. 개요
납세자 여러분께 2025년도 지방세 납부에 대해 안내드립니다.
올해 재산세는 전년 대비 5% 인상되었습니다.

## 2. 납부 정보

| 항목 | 내용 |
|------|------|
| 세금 종류 | 재산세 |
| 납부 금액 | 250,000원 |
| 납부 기한 | 2025년 3월 31일 |

## 3. 납부 방법
가. 위택스 온라인 납부 (www.wetax.go.kr)
나. 은행 방문 납부
다. 가상계좌 이체

## 4. 주의사항
- 납부 기한 내 미납 시 3%의 가산세가 부과됩니다.
- 분할 납부를 원하시면 세무과로 문의하세요.
- 문의: 세무과 02-1234-5678

감사합니다.
"""
    
    chunker = SmartChunker(ChunkingConfig(
        chunk_size=500,
        chunk_overlap=100
    ))
    
    chunks = chunker.chunk(test_text, "test-doc")
    
    print(f"\n📊 생성된 청크: {len(chunks)}개\n")
    
    for i, chunk in enumerate(chunks):
        print(f"--- 청크 #{i} ({chunk.chunk_type.value}, {chunk.length}자) ---")
        print(chunk.text[:150] + "..." if len(chunk.text) > 150 else chunk.text)
        print()