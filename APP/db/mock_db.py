"""
Mock 데이터베이스
실제 DB가 없으므로 메모리에 데이터 저장
"""
from typing import Dict, Optional
from datetime import datetime


class MockDatabase:
    """메모리 기반 Mock 데이터베이스"""
    
    def __init__(self):
        # 문서 저장소: {document_id: document_data}
        self.documents: Dict[str, dict] = {}
    
    def create_document(
        self,
        document_id: str,
        filename: str,
        file_path: str,
        file_size: int,
        file_type: str
    ) -> dict:
        """
        문서 생성
        
        Returns:
            생성된 문서 정보
        """
        document = {
            "document_id": document_id,
            "filename": filename,
            "file_path": file_path,
            "file_size": file_size,
            "file_type": file_type,
            "status": "uploaded",
            "created_at": datetime.now(),
            "analysis_result": None,
            "extracted_text": None
        }
        
        self.documents[document_id] = document
        print(f"📝 Mock DB: 문서 생성 - {document_id}")
        
        return document
    
    def get_document(self, document_id: str) -> Optional[dict]:
        """
        문서 조회
        
        Returns:
            문서 정보 or None
        """
        return self.documents.get(document_id)
    
    def update_document(self, document_id: str, updates: dict) -> bool:
        """
        문서 업데이트
        
        Returns:
            업데이트 성공 여부
        """
        if document_id not in self.documents:
            return False
        
        self.documents[document_id].update(updates)
        print(f"📝 Mock DB: 문서 업데이트 - {document_id}")
        return True
    
    def delete_document(self, document_id: str) -> bool:
        """
        문서 삭제
        
        Returns:
            삭제 성공 여부
        """
        if document_id in self.documents:
            del self.documents[document_id]
            print(f"📝 Mock DB: 문서 삭제 - {document_id}")
            return True
        return False
    
    def list_documents(self) -> list:
        """
        모든 문서 조회
        
        Returns:
            문서 리스트
        """
        return list(self.documents.values())


# 싱글톤 인스턴스
mock_db = MockDatabase()