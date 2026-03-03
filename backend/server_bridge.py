from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
import threading

from config import *
from llm_client import LLMClient
from llm_server import LLMServerManager
from conversation_manager import ConversationManager


app = FastAPI(title="AI Assistant Bridge")

# Middleware config
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"]
)


# Request schema
class ChatRequest(BaseModel):
    prompt : str


### Shared backend objects ###
conversation = ConversationManager(CHAT_HISTORY_FILE)

server = LLMServerManager(
    bin_path = LLM_SERVER_BIN,
    model_path = LLM_MODEL_PATH,
    port = SERVER_PORT,
    pid_file = LLM_PID_FILE,
    auto_shutdown=AUTO_SHUTDOWN
)

llm_client = LLMClient(
    MODEL_NAME,
    server,
    conversation,
    TEMPERATURE
)

# Audio manager later


### Lock ###
busy_lock = threading.Lock()


### API endpoints ###

@app.get("/api/health")
def health():
    return {
        "status": "ok",
        "llm_server_running": server.is_running(),
        "history_count": len(conversation.get()),
        "busy": busy_lock.locked(),
    }

@app.get("/api/history")
def history():
    return {
        "messages": conversation.get()
    }

@app.post("/api/clear")
def clear():
    conversation.clear(keep_system=True)
    return {
        "ok": True
    }

@app.post("/api/chat")
def chat(req: ChatRequest):
    prompt = req.prompt.strip()
    if not prompt:
        raise HTTPExecption(status_code=400, detail="Prompt can't be empty.")
    if not busy_lock.acquire(blocking=False):
        raise HTTPExecption(status_code=409, detail="Assistant is currently busy.")

    try:
        response_text = llm_client.send_query(prompt)
        return {
            "response": response_text
        }
    finally:
        busy_lock.release()

@app.post("/api/server/start")
def start_server():
    if not server.is_running():
        server.start()
    return {"ok": True, "llm_server_running": server.is_running()}

@app.post("/api/server/stop")
def stop_server():
    server.stop(conversation)
    return {"ok": True, "message": "LLM server stopped running."}