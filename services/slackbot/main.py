import uvicorn
from fastapi import FastAPI
import time
from dotenv import load_dotenv

load_dotenv()

from webhook_handler import slack_webhook_router

app = FastAPI(title="Alpha Machine Slack Bot", version="1.0.0")

app.include_router(slack_webhook_router, prefix="/slack")

@app.get("/")
def read_root():
    return {"service": "Slack Bot", "status": "running", "version": "1.0.0"}

@app.get("/health")
def health_check():
    return {"status": "healthy", "timestamp": time.time()}

if __name__ == "__main__":
    uvicorn.run("main:app", host="0.0.0.0", port=8001, reload=True)