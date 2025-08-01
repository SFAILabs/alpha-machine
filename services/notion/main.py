import uvicorn
from fastapi import FastAPI
from dotenv import load_dotenv

load_dotenv()

from services.notion.processor import notion_router

app = FastAPI()

app.include_router(notion_router)

@app.get("/")
def read_root():
    return {"Service": "Notion"}

if __name__ == "__main__":
    uvicorn.run("services.notion.main:app", host="0.0.0.0", port=8003, reload=True) 