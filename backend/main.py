from fastapi import FastAPI

app = FastAPI()


@app.get("/")
async def read_root():
    return {"message": "fast api working"}


@app.get("/ping")
async def get_ping():
    return {"message": "pong"}
