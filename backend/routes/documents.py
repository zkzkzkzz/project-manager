from fastapi import APIRouter, Depends, HTTPException, status, File, UploadFile
from fastapi.responses import RedirectResponse
from sqlalchemy.orm import Session


import backend.models.sql_models as db_models
from backend.db.apply_schema import get_db
from backend.core.security import get_current_user
from backend.core.s3_utils import s3_store
from backend.routes.projects import verify_project_access
from backend.models.models import DocumentOut

router = APIRouter(tags=["Documents"])


@router.get(
    "/documents/{document_id}/download",
    status_code=status.HTTP_307_TEMPORARY_REDIRECT,
    summary="Download a document via presigned URL",
)
def download_document(
    document_id: int,
    db: Session = Depends(get_db),
    current_user: db_models.User = Depends(get_current_user),
) -> RedirectResponse:

    doc = db.query(db_models.Document).filter_by(id=document_id).first()
    if not doc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Document not found"
        )

    verify_project_access(db, doc.project_id, current_user.id)

    url = s3_store.presign(doc.s3_key)

    if url is None:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Could not generate download URL",
        )

    return RedirectResponse(url=url, status_code=status.HTTP_307_TEMPORARY_REDIRECT)


@router.delete("/documents/{document_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_document(
    document_id: int,
    db: Session = Depends(get_db),
    current_user: db_models.User = Depends(get_current_user),
):

    doc = db.query(db_models.Document).filter_by(id=document_id).first()
    if not doc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Document not found"
        )

    is_project_owner = doc.project.owner_id == current_user.id
    is_project_uploader = doc.uploader_id == current_user.id

    if not (is_project_owner or is_project_uploader):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You do not have permission to delete this document.",
        )

    s3_key_to_delete = doc.s3_key

    key_deletion_successful = s3_store.delete(s3_key_to_delete)

    if not key_deletion_successful:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to delete file from storage. Document metadata not deleted.",
        )

    try:
        db.delete(doc)
        db.commit()

    except Exception as e:
        print(
            f"S3 key {s3_key_to_delete} was deleted, "
            f"but failed to delete database record for document ID {doc.id}. Error: {e}"
        )

        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="File successfully deleted from storage, but an error occurred removing its database record. Please contact support.",
        )


@router.put(
    "/documents/{document_id}",
    response_model=DocumentOut,
    status_code=status.HTTP_200_OK,
    summary="Replace an existing document",
)
def update_document(
    document_id: int,
    file: UploadFile = File(..., description="New file to replace existing"),
    db: Session = Depends(get_db),
    current_user: db_models.User = Depends(get_current_user),
) -> DocumentOut:
    doc = db.query(db_models.Document).filter_by(id=document_id).first()
    if not doc:
        raise HTTPException(status_code=404, detail="Document not found")

    old_s3_key = doc.s3_key

    verify_project_access(db, doc.project_id, current_user.id)

    new_filename = file.filename or "unnamed"

    try:
        new_key = s3_store.upload(file, doc.project_id)
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"S3 upload failed: {str(e)}",
        )

    s3_store.delete(old_s3_key)

    doc.file_name = new_filename
    doc.s3_key = new_key
    doc.file_type = file.content_type
    db.add(doc)
    db.commit()
    db.refresh(doc)

    response_data = DocumentOut.model_validate(doc)
    return response_data
