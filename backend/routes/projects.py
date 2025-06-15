from fastapi import APIRouter, HTTPException, status, Depends, File, UploadFile
from backend.models.models import ProjectCreate, ProjectOut, DocumentOut, DocumentList
from sqlalchemy.orm import Session
import backend.models.sql_models as db_models
from backend.db.apply_schema import get_db
from sqlalchemy.sql import or_
import logging


from backend.core.security import get_current_user
from backend.core.s3_utils import s3_store
from typing import List


router = APIRouter()

logger = logging.getLogger(__name__)


def get_project_validation(db: Session, project_id: int):
    db_project = db.query(db_models.Project).filter_by(id=project_id).first()
    if db_project is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Project with that id not found",
        )
    return db_project


def verify_project_access(db: Session, project_id: int, user_id: int):
    db_project = get_project_validation(db, project_id)

    if db_project.owner_id == user_id:
        return db_project

    participant = (
        db.query(db_models.ProjectParticipant)
        .filter_by(project_id=project_id, user_id=user_id)
        .first()
    )
    if participant:
        return db_project

    raise HTTPException(
        status_code=status.HTTP_403_FORBIDDEN,
        detail="You dont have permission to access this project",
    )


@router.post(
    "",
    response_model=ProjectOut,
    status_code=status.HTTP_201_CREATED,
    tags=["Projects"],
)
async def create_project(
    project_in: ProjectCreate,
    db: Session = Depends(get_db),
    current_user: db_models.User = Depends(get_current_user),
) -> ProjectOut:

    db_project = db_models.Project(
        name=project_in.name,
        description=project_in.description,
        owner_id=current_user.id,
    )

    db.add(db_project)
    db.commit()
    db.refresh(db_project)

    return db_project


@router.get(
    "",
    response_model=list[ProjectOut],
    status_code=status.HTTP_200_OK,
    tags=["Projects"],
)
async def get_all_projects(
    db: Session = Depends(get_db),
    current_user: db_models.User = Depends(get_current_user),
) -> list[ProjectOut]:

    projects = (
        db.query(db_models.Project)
        .outerjoin(db_models.ProjectParticipant)
        .filter(
            or_(
                db_models.Project.owner_id == current_user.id,
                db_models.ProjectParticipant.user_id == current_user.id,
            )
        )
        .distinct()
        .all()
    )
    return [ProjectOut.model_validate(project) for project in projects]


@router.get(
    "/{project_id}",
    response_model=ProjectOut,
    status_code=status.HTTP_200_OK,
    tags=["Projects"],
)
async def get_project(
    project_id: int,
    db: Session = Depends(get_db),
    current_user: db_models.User = Depends(get_current_user),
):

    db_project = verify_project_access(db, project_id, current_user.id)

    return db_project


@router.put(
    "/{project_id}",
    response_model=ProjectOut,
    status_code=status.HTTP_200_OK,
    tags=["Projects"],
)
async def update_project(
    project_id: int,
    project_update_data: ProjectCreate,
    db: Session = Depends(get_db),
    current_user: db_models.User = Depends(get_current_user),
):

    db_project = verify_project_access(db, project_id, current_user.id)

    db_project.name = project_update_data.name
    db_project.description = project_update_data.description

    db.add(db_project)
    db.commit()
    db.refresh(db_project)

    return db_project


@router.delete("/{project_id}", status_code=status.HTTP_200_OK, tags=["Projects"])
async def delete_project(
    project_id: int,
    db: Session = Depends(get_db),
    current_user: db_models.User = Depends(get_current_user),
):
    db_project = get_project_validation(db, project_id)

    if current_user:
        print(f" current_user ID: {current_user.id}, Login: {current_user.login}")
    else:
        print("current_user is None! Auth failed silently?")

    # db_project = get_project_validation(db, project_id)

    if db_project.owner_id != current_user.id:

        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not enough permissions to delete this project",
        )

    logger.info(
        f"Permission GRANTED: Project Owner {db_project.owner_id} == Current User {current_user.id}"
    )

    db.delete(db_project)
    db.commit()

    return {"message": "Project deleted"}


@router.post("/{project_id}/invite")
async def invite_user_to_project(
    project_id: int,
    user: str,
    db: Session = Depends(get_db),
    current_user: db_models.User = Depends(get_current_user),
):
    db_project = get_project_validation(db, project_id)

    if db_project.owner_id != current_user.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only the owner can invite users",
        )

    invited_user = db.query(db_models.User).filter_by(login=user).first()

    if not invited_user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="User to invite not found"
        )

    if invited_user.id == db_project.owner_id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Owner cannot invite themselves",
        )

    existing_participant = (
        db.query(db_models.ProjectParticipant)
        .filter_by(project_id=project_id, user_id=invited_user.id)
        .first()
    )
    if existing_participant:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="User is already a participant",
        )

    new_participant = db_models.ProjectParticipant(
        project_id=project_id, user_id=invited_user.id
    )

    db.add(new_participant)
    db.commit()

    return {"message": f"User '{user}' successfully invited to project {project_id}"}


@router.post(
    "/{project_id}/documents",
    response_model=list[DocumentOut],
    status_code=status.HTTP_201_CREATED,
    tags=["Projects", "Documents"],
)
async def upload_documents(
    project_id: int,
    files: List[UploadFile] = File(..., description="One or more files to upload"),
    db: Session = Depends(get_db),
    current_user: db_models.User = Depends(get_current_user),
) -> list[DocumentOut]:

    project = verify_project_access(db, project_id, current_user.id)

    if not files:
        raise HTTPException(status_code=400, detail="No files provided for upload.")

    created_docs: list[DocumentOut] = []
    s3_keys: list[str] = []

    for upload in files:
        filename = upload.filename or "unnamed"
        s3_key = s3_store.upload(upload, project.id)
        s3_keys.append(s3_key)

        doc = db_models.Document(
            project_id=project.id,
            file_name=filename,
            s3_key=s3_key,
            file_type=upload.content_type,
            uploader_id=current_user.id,
        )
        created_docs.append(doc)

        logger.info(
            f"Successfully committed DB record for {upload.filename}, S3 key: {s3_key}, DB ID: {doc.id}"
        )

    if len(created_docs) != len(s3_keys):
        for key in s3_keys:
            s3_store.delete(key)

        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="One or more files failed to upload.",
        )

    try:
        db.add_all(created_docs)
        db.commit()
        for doc in created_docs:
            db.refresh(doc)

    except Exception:
        for key in s3_keys:
            s3_store.delete(key)
        raise HTTPException(500, "Could not save file metadata. Rolled back.")

    return created_docs


@router.get(
    "/{project_id}/documents",
    response_model=List[DocumentList],
    tags=["Projects", "Documents"],
    summary="List documents for a project",
)
def list_project_documents(
    project_id: int,
    db: Session = Depends(get_db),
    current_user: db_models.User = Depends(get_current_user),
) -> list[DocumentList]:

    verify_project_access(db, project_id, current_user.id)

    docs = (
        db.query(db_models.Document)
        .filter_by(project_id=project_id)
        .order_by(db_models.Document.created_at.desc())
        .all()
    )

    documents_list: List[DocumentList] = []

    # d is a sqlalchemy object
    for d in docs:
        url = s3_store.presign(d.s3_key)

        if url is None:
            raise HTTPException(
                500, f"Could not generate download URL for document {d.id}"
            )
        # here we create a documents pydantic item
        documents_list.append(
            DocumentList(
                id=d.id,
                file_name=d.file_name,
                file_type=d.file_type,
                created_at=d.created_at,
                download_url=url,
            )
        )

    return documents_list
