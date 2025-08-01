import uvicorn
from fastapi import FastAPI
from dotenv import load_dotenv

load_dotenv()

from services.slackbot.command_handler import command_router
from services.slackbot.event_handler import event_router
from services.slackbot.webhook_handler import webhook_router

app = FastAPI()

app.include_router(command_router, prefix="/commands")
app.include_router(event_router, prefix="/events")
app.include_router(webhook_router, prefix="/webhooks")

@app.get("/")
def read_root():
    return {"Service": "Slackbot"}

if __name__ == "__main__":
    uvicorn.run("services.slackbot.main:app", host="0.0.0.0", port=8001, reload=True)