import os
import json
import time
import uuid
from typing import List, Dict


# Helper function to fetch time
def _time_now() -> str:
    return time.strftime("%Y-%m-%dT%H:%M:%S", time.localtime())


### Manages chats ###
class ChatManager:
    def __init__(self, base_dir: str, system_prompt: str):
        # Creates base directory for chat storage & sets default prompt
        self.base_dir = base_dir
        self.system_prompt = system_prompt
        os.makedirs(self.base_dir, exist_ok=True)


    ### Patch builders ###
    def _chat_dir(self, chat_id: str) -> str:
        return os.path.join(self.base_dir, chat_id)


    def _meta_path(self, chat_id: str) -> str:
        return os.path.join(self._chat_dir(chat_id), "meta.json")


    def _messages_path(self, chat_id: str) -> str:
        return os.path.join(self._chat_dir(chat_id), "messages.json")


    def list_chats(self) -> List[Dict]:
        # Function that lists chats for sidebar
        chats = []
        if not os.path.exists(self.base_dir):
            return chats

        # Loops through everything inside base directory & add to list
        for chat_id in os.listdir(self.base_dir):
            cdir = self._chat_dir(chat_id)
            if not os.path.isdir(cdir):
                continue
            meta = self._read_json(self._meta_path(chat_id), default=None)
            if not meta:
                continue
            chats.append(meta)

        # Sorting for better UX
        chats.sort(key=lambda m: m.get("updated_at", ""), reverse=True)
        return chats


    def create_chat(self, title: str = "New chat") -> Dict:
        # Creates folder for a chat, assigns a uuid for it, creates metadata and initializes the chat
        chat_id = uuid.uuid4().hex[:12]
        os.makedirs(self._chat_dir(chat_id), exist_ok=True)

        meta = {
            "id": chat_id,
            "title": title,
            "created_at": _time_now(),
            "updated_at": _time_now()
        }
        messages = [{
            "role": "system",
            "content": self.system_prompt
        }]

        self._write_json(self._messages_path(chat_id), messages)
        self._write_json(self._meta_path(chat_id), meta)
        return meta


    def ensure_default_chat(self) -> Dict:
        # Ensures most recently updated chat launches first
        # If no chats -> creates new
        chats = self.list_chats()
        if chats:
            return chats[0]
        return self.create_chat("New chat")


    def get_messages(self, chat_id: str) -> List[Dict]:
        # Loads chat messages for a specific chat
        messages = self._read_json(self._messages_path(chat_id), default=None)
        if messages is None:
            raise FileNotFoundError(f"Chat not found: {chat_id}")
        return messages


    def save_messages(self, chat_id: str, messages: List[Dict]) -> None:
        # Saves new messages to a json file
        if not os.path.isdir(self._chat_dir(chat_id)):
            raise FileNotFoundError(f"Chat not found: {chat_id}")

        self._write_json(self._messages_path(chat_id), messages)
        meta = self._read_json(self._meta_path(chat_id), default=None)

        if not meta:
            meta = {
                "id": chat_id,
                "title": "Chat",
                "created_at": _time_now()
            }

        meta["updated_at"] = _time_now()
        self._write_json(self._meta_path(chat_id), meta)


    def clear_chat(self, chat_id: str) -> None:
        # Resets messages.json to initial system prompt & updates meta
        if not os.path.isdir(self._chat_dir(chat_id)):
            raise FileNotFoundError(f"Chat not found: {chat_id}")

        messages = [{
            "role": "system",
            "content": self.system_prompt
            }]
        self._write_json(self._messages_path(chat_id), messages)
        meta = self._read_json(self._meta_path(chat_id), default=None)

        if meta:
            meta["updated_at"] = _time_now()
            self._write_json(self._meta_path(chat_id), meta)


    def rename_chat(self, chat_id: str, title: str) -> Dict:
        # Loads metadata for a chat and tries to set empty title
        meta = self._read_json(self._meta_path(chat_id), default=None)

        if meta is None:
            raise FileNotFoundError(f"Chat not found: {chat_id}")
        
        meta["title"] = title.strip() or meta.get("title", "Chat")
        meta["updated_at"] = _time_now()
        self._write_json(self._meta_path(chat_id), meta)
        return meta

    def delete_chat(self, chat_id: str) -> None:
        # Recursively deletes files, directories & chat folder
        cdir = self._chat_dir(chat_id)
        if not os.path.isdir(cdir):
            raise FileNotFoundError(f"Chat not found: {chat_id}")

        for root, dirs, files in os.walk(cdir, topdown=False):
            for f in files:
                os.remove(os.path.join(root, f))
            for d in dirs:
                os.rmdir(os.path.join(root, d))
        
        os.rmdir(cdir)
        
    def _read_json(self, path: str, default):
        # Helper function to read json files
        try:
            if not os.path.exists(path):
                return default
            with open(path, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception:
            return default

    def _write_json(self, path: str, data) -> None:
        # Helper function to write json data
        os.makedirs(os.path.dirname(path), exist_ok=True)
        with open(path, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)