from fastapi import FastAPI

app = FastAPI()


@app.get("/")
async def read_root():
    message = 'hello world'
    result = message + undefined_variable
    return {'message': result}


@app.get("/ping")
async def get_ping():
    return {"message": "pong"}
