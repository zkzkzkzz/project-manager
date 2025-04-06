from fastapi import FastAPI, APIRouter
from backend.routes import projects

app = FastAPI()

api_router = APIRouter()
api_router.include_router(projects.router, prefix="/projects")

app.include_router(api_router)


@app.get("/")
async def read_root():
    return {"message": "fast api working"}


@app.get("/ping")
async def get_ping():
    return {"message": "pong"}
