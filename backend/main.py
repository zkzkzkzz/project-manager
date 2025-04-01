from fastapi import FastAPI

app = FastAPI()


@app.get("/")
async def read_root():
    long_text = "This is an intentionally very very very very very very very very very very very very very very very very long line of text to trigger a flake8 E501 error."
    return {"message": "Hello World from Project Manager API!" + long_text}


@app.get("/ping")
async def get_ping():
    return {"message": "pong"}
