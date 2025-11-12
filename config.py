import os

### PATHS & MODEL SETTINGS ###
PIPE_PATH = "/tmp/ai-assistant.pipe"
MODEL_NAME = "Qwen3-32B-UD-Q6_K_XL.gguf"
SERVER_PORT = 8080
AUTO_SHUTDOWN = 600
CHAT_HISTORY_FILE = "/tmp/assistant_history.json"

### AUDIO SETTINGS ###
WHISPER_MODEL = "base.en"
SAMPLE_RATE = 48000
PIPER_SAMPLE_RATE = 22050
CHANNELS = 1
RECORD_TIMEOUT = 1.0

### TTS SETTIGNS ###
PIPER_MODEL = os.path.expanduser("~/Documents/GitHub/AI-Assistant/TTS/models/en_US-alexa-medium/alexa.onnx")
PIPER_CONFIG = os.path.expanduser("~/Documents/GitHub/AI-Assistant/TTS/models/en_US-alexa-medium/alexa.onnx.json")

### LLM SERVER SETTINGS ###
LLM_SERVER_BIN = os.path.expanduser("~/Documents/GitHub/llama.cpp/build/bin/llama-server")
LLM_MODEL_PATH = os.path.expanduser("~/Documents/GitHub/llama.cpp/models/Qwen3-32B-UD-Q6_K_XL.gguf")
LLM_PID_FILE = "/tmp/llm_server.pid"
