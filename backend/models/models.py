from pydantic import BaseModel

class ProjectCreate(BaseModel):
    name: str
    description: str | None=None

class ProjectOut(ProjectCreate):
    id: int


