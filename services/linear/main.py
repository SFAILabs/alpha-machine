import uvicorn
from fastapi import FastAPI
from dotenv import load_dotenv

load_dotenv()

from orchestrator import linear_router

app = FastAPI()

app.include_router(linear_router)

@app.get("/")
def read_root():
    return {"Service": "Linear"}

if __name__ == "__main__":
    uvicorn.run("linear.main:app", host="0.0.0.0", port=8002, reload=True) 