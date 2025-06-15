from fastapi import FastAPI, APIRouter
from backend.routes import projects
from backend.routes import auth
from backend.routes import users
from backend.routes import documents

app = FastAPI()

api_router = APIRouter()
api_router.include_router(projects.router, prefix="/projects", tags=["Projects"])

api_router.include_router(auth.router, tags=["Authentication"])

api_router.include_router(users.router, prefix="/users", tags=["Oauth2scheme"])

api_router.include_router(documents.router, tags=["Documents"])

app.include_router(api_router)


@app.get("/")
async def read_root():
    return {"message": "fast api working"}


@app.get("/ping")
async def get_ping():
    return {"message": "pong"}
