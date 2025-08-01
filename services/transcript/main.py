import uvicorn
from fastapi import FastAPI
from dotenv import load_dotenv

load_dotenv()

from services.transcript.webhook_handler import webhook_router
from services.transcript.processor import processor_router
from services.transcript.filter_service import filter_router

app = FastAPI()

app.include_router(webhook_router, prefix="/webhook")
app.include_router(processor_router, prefix="/processor")
app.include_router(filter_router, prefix="/filter")

@app.get("/")
def read_root():
    return {"Service": "Transcript"}

if __name__ == "__main__":
    uvicorn.run("services.transcript.main:app", host="0.0.0.0", port=8000, reload=True) 