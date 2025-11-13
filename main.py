import os, threading, time
from config import *
from conversation_manager import ConversationManager
from llm_server import LLMServerManager
from llm_client import LLMClient
from pipe_listener import PipeListener
from audio_manager import AudioManager


### INITIALIZATION ###
conversation = ConversationManager(CHAT_HISTORY_FILE)

server = LLMServerManager(
    bin_path = LLM_SERVER_BIN,
    model_path = LLM_MODEL_PATH,
    port = SERVER_PORT,
    pid_file = LLM_PID_FILE,
    auto_shutdown=AUTO_SHUTDOWN
)

llm_client = LLMClient(MODEL_NAME, server, conversation, TEMPERATURE)

audio_manager = AudioManager(
    whisper_model = WHISPER_MODEL,
    piper_model = PIPER_MODEL,
    piper_config = PIPER_CONFIG,
    mic_rate = SAMPLE_RATE,
    tts_rate = PIPER_SAMPLE_RATE,
    channels = CHANNELS,
    record_timeout = RECORD_TIMEOUT
)
    

### PIPE EVENT HANDLERS ###
def handle_toggle():
    # Toggles recording on/off
    audio_manager.recording = not audio_manager.recording
    print(f">> Recording state changed: {audio_manager.recording}")
    if not audio_manager.recording:
        print(">> Processing audio input...")
        text = audio_manager.transcribe()
        if text:
            response = llm_client.send_query(text)
            print(">> RESPONSE:", response)
            audio_manager.speak(response)

def handle_stop():
    # Stops LLM server manually
    print(">> Manual stop command received from pipe.")
    server.stop(conversation)
    print(">> LLM server stopped via pipe command.")


### MAIN ###
if __name__ == "__main__":
    print(">> AI Assistant starting up...")

    # Pipe listener (for cli control)
    pipe_listener = PipeListener(pipe_path=PIPE_PATH, on_toggle=handle_toggle, on_stop=handle_stop)

    # Background threads
    threading.Thread(target=server.auto_shutdown_monitor, args=(conversation,), daemon=True).start()
    threading.Thread(target=audio_manager.record_loop, daemon=True).start()
    threading.Thread(target=pipe_listener.listen, daemon=True).start()

    # Main thread kept alive
    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        print("\n>> Shutting down...")