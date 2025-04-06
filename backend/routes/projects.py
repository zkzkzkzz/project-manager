from fastapi import APIRouter, HTTPException, status
from backend.models.models import ProjectCreate,ProjectOut

router=APIRouter()

projects_db = {}
next_project_id=1

@router.post('/projects', response_model=ProjectOut, status_code=status.HTTP_201_CREATED)
async def create_project(project: ProjectCreate) -> ProjectOut:
    global next_project_id
    project_id=next_project_id
    next_project_id += 1
    project_dict=project.model_dump()
    created_project=ProjectOut(id=project_id, **project_dict)
    projects_db[project_id] = created_project
    return created_project

@router.get('/projects', response_model=list[ProjectOut], status_code=status.HTTP_200_OK)
async def get_all_projects():
    return list(projects_db.values())

@router.get('/projects/{project_id}', response_model=ProjectOut, status_code=status.HTTP_200_OK)
async def get_project(project_id: int):
    if project_id not in projects_db:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail='Project with that id not found')
    return projects_db[project_id]

@router.put('/projects/{project_id}',response_model=ProjectOut, status_code=status.HTTP_200_OK)
async def update_project(project_id: int, updated_project: ProjectCreate):
    if project_id not in projects_db:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail='Project with that id not found')

    existing_project = projects_db[project_id]
    updated_dict = updated_project.model_dump()

    updated_project_object = ProjectOut(
        id=existing_project.id,
        name=updated_dict['name'],
        description=updated_dict['description']
    )

    projects_db[project_id]=updated_project_object

    return updated_project_object

@router.delete('/projects/{project_id}', status_code=status.HTTP_200_OK)
async def delete_project(project_id:int):
    if project_id not in projects_db:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail='Project with this id not found')
    del projects_db[project_id]
    return {'message':'Project deleted'}

