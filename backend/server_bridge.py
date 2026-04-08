from fastapi import FastAPI, HTTPException, Body
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import Any, Dict
import threading, time

import config
from llm_server import LLMServerManager
from chat_manager import ChatManager
from settings_manager import SettingsManager


app = FastAPI(title="AI Assistant Bridge")


# Middleware config
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"]
)


### JSON Schemas for frontend ###
class ChatRequest(BaseModel):
    prompt : str

class CreateChatRequest(BaseModel):
    title: str | None = None

class RenameChatRequest(BaseModel):
    title: str


### Shared backend objects ###
server = LLMServerManager(
    bin_path = config.LLM_SERVER_BIN,
    model_path = config.LLM_MODEL_PATH,
    port = config.SERVER_PORT,
    pid_file = config.LLM_PID_FILE,
    auto_shutdown = config.AUTO_SHUTDOWN
)

chat_manager = ChatManager(
    config.CHATS_DIR,
    system_prompt = config.SYSTEM_PROMPT
)

# Use blocklist to block some settings from config.py to be showed
settings_blocklist = {"LLM_PID_FILE", "PIPE_PATH", "CHANNELS"}
settings_restart_required = {"LLM_MODEL_PATH", "SERVER_PORT", "LLM_SERVER_BIN", "MODEL_NAME"}

# Helper function to build default settings
def build_settings_defaults():
    settings_defaults = {}
    for key, value in vars(config).items():
        if not key.isupper() or key.startswith("_"):
            continue
        if key in settings_blocklist:
            continue
        settings_defaults[key] = value
    return settings_defaults

SETTINGS_DEFAULTS = build_settings_defaults()
settings_manager = SettingsManager(config.SETTINGS_FILE_PATH, SETTINGS_DEFAULTS)

# Audio manager later?


### Lock ###
busy_lock = threading.Lock()


### API endpoints ###
@app.get("/api/health")
def health():
    # Fetches server health status
    return {
        "status": "ok",
        "llm_server_running": server.is_running(),
        "busy": busy_lock.locked(),
    }

@app.get("/api/chats")
def list_chats():
    # Lists chats for sidebar
    return {
        "chats": chat_manager.list_chats()
    }

@app.post("/api/chats")
def create_chat(req: CreateChatRequest):
    # Creates a chat with just system prompt
    title = (req.title or "New chat").strip()
    meta = chat_manager.create_chat(title=title)
    return {
        "chat": meta
    }

@app.get("/api/chats/{chat_id}")
def get_chat(chat_id: str):
    # Loads chat messages from disk to UI
    messages = chat_manager.get_messages(chat_id)
    return {
        "id": chat_id,
        "messages": messages
    }

@app.post("/api/chats/{chat_id}/clear")
def clear_chat(chat_id: str):
    # Clean the selected chat
    chat_manager.clear_chat(chat_id)
    return {
        "ok": True
    }

@app.post("/api/chats/{chat_id}/rename")
def rename_chat(chat_id: str, req: RenameChatRequest):
    # Rename a chat
    meta = chat_manager.rename_chat(chat_id, req.title)
    return {
        "chat": meta
    }

@app.delete("/api/chats/{chat_id}")
def delete_chat(chat_id: str):
    # Delets a chat
    chat_manager.delete_chat(chat_id)
    return {
        "ok": True
    }

@app.post("/api/chats/{chat_id}/chat")
def chat(chat_id: str, req: ChatRequest):
    # Loads messages for a specific chat, appends new messages, and saves them to disk
    # Prompt and error handling
    prompt = req.prompt.strip()
    if not prompt:
        raise HTTPException(status_code=400, detail="Prompt can't be empty.")
    if not busy_lock.acquire(blocking=False):
        raise HTTPException(status_code=409, detail="Assistant is currently busy.")

    try:
        # Fetches chats
        messages = chat_manager.get_messages(chat_id)
        messages.append({
            "role": "user",
            "content": prompt
        })

        # Error handling
        if not server.is_running():
            server.start()
        server.last_query_time = time.time()

        # Send a message to server
        import requests
        effective = settings_manager.get_merged_settings()
        payload = {
            "model": effective["MODEL_NAME"],
            "messages": messages,
            "temperature": float(effective["TEMPERATURE"]),
        }

        r = requests.post(
            f"http://127.0.0.1:{server.port}/v1/chat/completions",
            json=payload,
            timeout=300
        )
        r.raise_for_status()
        data = r.json()

        # Reply extraction
        raw = data["choices"][0]["message"]["content"]
        content = raw

        # Cleaning the response
        if "<think>" in content and "</think>" in content:
            content = content.split("</think>", 1)[-1].strip()
        content = content.replace("*", "").replace("###", "").replace("---", "").strip()

        # Append to messages
        messages.append({
            "role": "assistant",
            "content": content
        })
        # Save
        chat_manager.save_messages(chat_id, messages)

        return {
            "response": content
        }

    finally:
        # Release the lock
        busy_lock.release()
            
@app.post("/api/server/start")
def start_server():
    # Starts the LLM server
    if not server.is_running():
        server.start()
    return {"ok": True, "llm_server_running": server.is_running()}

@app.post("/api/server/stop")
def stop_server():
    # Stops the LLM server
    server.stop()
    return {"ok": True, "llm_server_running": server.is_running()}

@app.get("/api/settings")
def get_settings():
    return {"settings": settings_manager.get_merged_settings()}

@app.post("/api/settings")
def update_settings(updates: Dict[str, Any] = Body(...)):
    """Updates all settings of the json"""
    # Filter allowed parameters (config - blocklist)
    allowed_params = set(SETTINGS_DEFAULTS.keys())
    # Incoming parameters from UI
    incoming_params = {key: value for key, value in updates.items() if key not in allowed_params}

    # "Safety check"
    if not incoming_params:
        return {
            "ok": True,
            "settings": settings_manager.get_merged_settings(),
            "restart_required": False,
            "ignored_keys": [key for key in updates.keys() if key not in allowed_params],
        }
    
    # Use defaults as source of truth
    for key, value in list(incoming_params.items()):
        default_value = SETTINGS_DEFAULTS[key]

        # For converting / handling value types
        try:
            if isinstance(default_value, bool):
                if isinstance(value, str):
                    incoming_params[key] = value.strip().lower() in ("1", "true", "yes", "on")
                else:
                    incoming_params[key] = bool(value)
            
            elif isinstance(default_value, int) and not isinstance(default_value, bool):
                if isinstance(value, str):
                    incoming_params[key] = int(value.strip())
                else:
                    incoming_params[key] = int(value)

            elif isinstance(default_value, float):
                if isinstance(value, str):
                    incoming_params[key] = float(value.strip())
                else:
                    incoming_params[key] = float(value)

            elif isinstance(default_value, str):
                incoming_params[key] = str(value)

        except Exception:
            raise HTTPException(status_code=400, detail=f"Invalid value for {key}")
        
    # Constraints for some config values
    if "TEMPERATURE" in incoming_params:
        t = float(incoming_params["TEMPERATURE"])
        if t < 0 or t > 2:
            raise HTTPException(status_code=400, detail="TEMPERATURE must be between 0 and 2")
        
    if "AUTO_SHUTDOWN" in incoming_params:
        s = int(incoming_params["AUTO_SHUTDOWN"])
        if s < 0:
            raise HTTPException(status_code=400, detail="AUTO_SHUTDOWN must be a positive number")

    if "SERVER_PORT" in incoming_params:
        p = int(incoming_params["SERVER_PORT"])
        if p < 1 or p > 65535:
            raise HTTPException(status_code=400, detail="SERVER_PORT must be between 1 and 65535")
        
    # Load overrides from settings.json
    overrides = settings_manager.load_overrides()
    overrides.update(incoming_params)
    settings_manager.save_overrides(overrides)

    # Build settings (from overrides & defaults)
    effective_settings = settings_manager.get_merged_settings()

    # Apply effective settings if safe
    if "AUTO_SHUTDOWN" in incoming_params:
        server.auto_shutdown = int(effective_settings["AUTO_SHUTDOWN"])

    # Determine whether restart is required for changes to apply
    restart_required = any(key in incoming_params for key in settings_restart_required)

    return {
        "ok": True,
        "settings": effective_settings,
        "restart_required": restart_required,
        "updated_keys": sorted(list(incoming_params.keys())),
        "ignored_keys": [key for key in updates.keys() if key not in allowed_params],
    }