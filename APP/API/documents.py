"""
문서 업로드/조회/삭제 API
⭐ 수정: 중복 방지 + 전체 삭제(초기화) 기능 추가
"""
from fastapi import APIRouter, UploadFile, File, HTTPException
from typing import List
import logging

from APP.schemas.document import DocumentUploadResponse, DocumentResponse
from APP.utils.file_handler import file_handler
from APP.db.mock_db import mock_db

logger = logging.getLogger(__name__)

router = APIRouter()

# ---------------------------------------------------------
# 1. 파일 업로드 (중복 방지 적용)
# ---------------------------------------------------------
@router.post("/upload", response_model=DocumentUploadResponse)
async def upload_document(
    file: UploadFile = File(..., description="업로드할 문서 파일")
):
    try:
        # [중복 체크] 이미 같은 이름의 파일이 있는지 확인
        existing_docs = mock_db.list_documents()
        for doc in existing_docs:
            if doc["filename"] == file.filename:
                logger.info(f"♻️ 중복 파일 감지됨: {file.filename} (기존 ID 반환)")
                # 새로 저장 안 하고 기존 정보 리턴
                return DocumentUploadResponse(
                    document_id=doc["document_id"],
                    filename=doc["filename"],
                    file_size=doc["file_size"],
                    file_type=doc["file_type"],
                    status=doc["status"],
                    created_at=doc["created_at"],
                    parsed_result=None
                )

        # 파일 저장
        logger.info(f"📤 파일 업로드 시작: {file.filename}")
        document_id, file_path, file_size = await file_handler.save_file(file)
        
        file_type = "." + file.filename.split(".")[-1].lower() if "." in file.filename else ""
        
        # DB 저장
        document = mock_db.create_document(
            document_id=document_id,
            filename=file.filename,
            file_path=file_path,
            file_size=file_size,
            file_type=file_type
        )
        
        return DocumentUploadResponse(
            document_id=document["document_id"],
            filename=document["filename"],
            file_size=document["file_size"],
            file_type=document["file_type"],
            status="uploaded",
            created_at=document["created_at"],
            parsed_result=None
        )
        
    except Exception as e:
        logger.error(f"❌ 업로드 오류: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


# ---------------------------------------------------------
# 2. 문서 목록 조회
# ---------------------------------------------------------
@router.get("/", response_model=dict)
async def list_documents():
    documents = mock_db.list_documents()
    return {
        "total": len(documents),
        "documents": [
            {
                "document_id": doc["document_id"],
                "filename": doc["filename"],
                "status": doc["status"],
                "file_size": doc.get("file_size"),
                "page_count": doc.get("page_count"),
                "created_at": doc["created_at"]
            }
            for doc in documents
        ]
    }


# ---------------------------------------------------------
# 3. 문서 상세 조회
# ---------------------------------------------------------
@router.get("/{document_id}", response_model=DocumentResponse)
async def get_document(document_id: str):
    document = mock_db.get_document(document_id)
    if not document:
        raise HTTPException(status_code=404, detail="문서를 찾을 수 없습니다.")
    
    return DocumentResponse(
        document_id=document["document_id"],
        filename=document["filename"],
        file_size=document["file_size"],
        file_type=document["file_type"],
        status=document["status"],
        created_at=document["created_at"],
        extracted_text=document.get("extracted_text"),
        page_count=document.get("page_count"), 
        analysis_result=document.get("analysis_result")
    )


# ---------------------------------------------------------
# 4. 문서 삭제
# ---------------------------------------------------------
@router.delete("/{document_id}")
async def delete_document(document_id: str):
    document = mock_db.get_document(document_id)
    if not document:
        raise HTTPException(status_code=404, detail="문서 없음")
    
    file_handler.delete_file(document_id, document["file_type"])
    mock_db.delete_document(document_id)
    
    return {"message": "삭제되었습니다.", "document_id": document_id}


# ---------------------------------------------------------
# 5. [긴급] 데이터 전체 초기화 (개발용)
# ---------------------------------------------------------
@router.delete("/debug/clear_all")
async def clear_all_documents():
    """
    모든 문서와 DB 데이터를 강제로 삭제합니다.
    """
    documents = mock_db.list_documents()
    count = 0
    for doc in documents:
        # 파일 삭제
        try:
            file_handler.delete_file(doc["document_id"], doc["file_type"])
        except:
            pass
        # DB 삭제
        mock_db.delete_document(doc["document_id"])
        count += 1
        
    logger.info(f"🧹 전체 초기화 완료: {count}개 삭제됨")
    return {"message": f"전체 초기화 완료. {count}개의 문서가 삭제되었습니다."}