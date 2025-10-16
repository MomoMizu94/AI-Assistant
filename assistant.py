import os, threading, time, queue, numpy, sounddevice, requests, signal, subprocess, json
from faster_whisper import WhisperModel
from scipy.io.wavfile import write as write_wav
from piper import PiperVoice, SynthesisConfig


### CONFIGURATIONS ###
PIPE_PATH = "/tmp/ai-assistant.pipe"
MODEL_NAME = "Qwen3-32B-UD-Q6_K_XL.gguf"
LLM_SERVER_BIN = os.path.expanduser("~/Documents/GitHub/llama.cpp/build/bin/llama-server")
LLM_MODEL_PATH = os.path.expanduser("~/Documents/GitHub/llama.cpp/models/Qwen3-32B-UD-Q6_K_XL.gguf")
SERVER_PORT = 8080
SERVER_PID_FILE = "/tmp/llm_server.pid"
AUTO_SHUTDOWN = 600
CHAT_HISTORY_FILE = "/tmp/assistant_history.json"
last_query_time = time.time()

# Audio tuning
SAMPLE_RATE = 48000
PIPER_SAMPLE_RATE = 22050
CHANNELS = 1
RECORD_TIMEOUT = 1.0

# TTS
PIPER_MODEL = os.path.expanduser("~/Documents/GitHub/AI-Assistant/TTS/models/en_US-sam-medium.onnx")
PIPER_CONFIG = os.path.expanduser("~/Documents/GitHub/AI-Assistant/TTS/models/en_US-sam-medium.onnx.json")
PIPER_VOICE = PiperVoice.load(PIPER_MODEL, config_path=PIPER_CONFIG)
SYNTH_CONFIG = SynthesisConfig(length_scale=0.80)


### INITIALIZATION ###
# Ensure clean state for the pipe
if os.path.exists(PIPE_PATH):
    os.remove(PIPE_PATH)
os.mkfifo(PIPE_PATH)

# Recording state
record = False
# Holds recorded audio chunks
audio_queue = queue.Queue()
# Load conversation history from the file
if os.path.exists(CHAT_HISTORY_FILE):
    with open(CHAT_HISTORY_FILE) as f:
        conversation_history = json.load(f)
else:
    conversation_history = [
        {"role": "system", "content": "You are a concise and friendly AI assistant that gives short, accurate answers without emojis."}
    ]
# Speech recognition model
model = WhisperModel("base.en", device="cpu", compute_type="int8")

### SERVER LISTENER ###
def server_listener():
    if not os.path.exists(SERVER_PID_FILE):
        return False
    # Checks if the server is still running on the background
    try:
        with open(SERVER_PID_FILE) as f:
            pid = int(f.read().strip())
            os.kill(pid, 0)
            return True
    except:
        return False


### START THE SERVER ###
def start_server():
    if server_listener():
        return

    # Start the LLM server as a bg process
    print(">> LLM server starting. Loading model to VRAM...")
    process = subprocess.Popen([
        LLM_SERVER_BIN,
        "-m", LLM_MODEL_PATH,
        "-t", "16",
        "-ngl", "999",
        "--port", str(SERVER_PORT)
    ])

    # Bookmarks the bg process
    with open(SERVER_PID_FILE, "w") as f:
        f.write(str(process.pid))
    time.sleep(2)
    print(">> LLM server started with PID:", process.pid)

    # Wait for the model to load
    for _ in range(60):
        try:
            r = requests.get(f"http://127.0.0.1:{SERVER_PORT}/health", timeout=2)
            if r.status_code == 200:
                print(">> LLM server ready to accept queries.")
                break
        except Exception:
            pass
        time.sleep(1)
    else:
        print(">> LLM server did not respond within 60 seconds.")


### STOP THE SERVER ###
def stop_server():
    global conversation_history
    # Clear conversation history only is server is manually stopped
    conversation_history = conversation_history[:1]
    with open(CHAT_HISTORY_FILE, "w") as f:
        json.dump(conversation_history, f)
    print(">> Conversation history cleared.")
    
    if not server_listener():
        print(">> No LLM server running.")
        return
    try:
        with open(SERVER_PID_FILE) as f:
            pid = int(f.read().strip())
        print(f">> Stopping LLM server with PID: {pid}")
        os.kill(pid, signal.SIGTERM)
        os.remove(SERVER_PID_FILE)
        print(">> LLM server stopped. Reserved VRAM released.")
        # Potential clear conversation memory here?
    
    except Exception as e:
        print(f">> Failed to stop LLM server: {e}")


### AUTO SHUTDOWN ###
def auto_shutdown_monitor():
    global last_query_time
    while True:
        if server_listener() and (time.time() - last_query_time > AUTO_SHUTDOWN):
            print(">> LLM has been idle for 10 minutes. Shutting down the server...")
            stop_server()
        time.sleep(60)


### AUDIO CALLBACK ###
def audio_callback(indata, frames, time_info, status):
    # Places audio chunks into a queue while recording
    if record:
        audio_queue.put(indata.copy())


### AUDIO RECORD LOOP ###
def record_audio():
    # Opens audio stream and starts calling for audio_callback in another thread
    with sounddevice.InputStream(samplerate=SAMPLE_RATE, channels=CHANNELS, callback=audio_callback):
        while True:
            time.sleep(RECORD_TIMEOUT)


### TTS FUNCTION ###
def text_to_speech(text):
    print(">> Generating speech...")

    # Generate audio chunks from provided response text
    audio_chunks = list(PIPER_VOICE.synthesize(text, syn_config=SYNTH_CONFIG))
    # Extract audio arrays
    audio_array = [chunk.audio_int16_array for chunk in audio_chunks]
    # Form one numpy array
    audio = numpy.concatenate(audio_array)
    
    # Write the audio data to a wav file with sample rate from Piper model settings
    wav_path = "response.wav"
    write_wav(wav_path, PIPER_SAMPLE_RATE, audio)

    # Play generated audio file with ffplay
    subprocess.run(["ffplay", "-nodisp", "-autoexit", wav_path], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)

    # Clean upfor temp files
    if os.path.exists(wav_path):
        os.remove(wav_path)


### QUERY LLM VIA HTTP ###
def llm_query(prompt):
    global last_query_time, conversation_history

    # Start the server if it's not running
    if not server_listener():
        start_server()
    
    last_query_time = time.time()

    # Add message to memory
    conversation_history.append({"role": "user", "content": prompt.strip()})

    # Dictionary layout for data
    payload = {
        "model": MODEL_NAME,
        "messages": conversation_history,
        # Randomness control (deterministic --- creative)
        "temperature": 0.7
    }

    try:
        
        print(">> Sending a query to LLM server...")
        # Request sending
        response = requests.post(f"http://127.0.0.1:{SERVER_PORT}/v1/chat/completions", json=payload, timeout=120)
        # Checks for http errors
        response.raise_for_status()
        # Parses response JSON to python dictionary
        data = response.json()
        # Extracts generated text from JSON structure
        content = data["choices"][0]["message"]["content"]
        # Add to history
        conversation_history.append({"role": "assistant", "content": content.strip()})
        with open(CHAT_HISTORY_FILE, "w") as f:
            json.dump(conversation_history, f)
        # Returns the response text further
        return content.strip()
    except Exception as e:
        print(f">> LLM request failed due to: {e}")
        return "Error encountered while processing request."


### AUDIO PROCESSING ###
def process_audio():
    # Processes recorded audio by transcribing it, sending it to LLM, and speaking out the response
    print(">> Starting audio processing...")

    # Create an empty list and append audio chunks to it
    frames = []
    while not audio_queue.empty():
        frames.append(audio_queue.get())

    # Checks for no recording
    if not frames:
        print("No audio captured.")
        return

    # Joins all audio chunks into a temporary .wav file
    audio = numpy.concatenate(frames, axis=0)
    audio_path = "temp_audio.wav"
    write_wav(audio_path, SAMPLE_RATE, audio)

    # Transcribe the audio
    segments, _ = model.transcribe(audio_path)
    text = " ".join([seg.text for seg in segments])
    print(">> TRANSCRIPT:", text)

    # Clean upfor temp files
    if os.path.exists(audio_path):
        os.remove(audio_path)
    
    # Send the question to LLM and get its reply
    response = llm_query(text).strip()

    # Split the response after first </think> block & remove asterisks
    if "<think>" in response and "</think>" in response:
        response = response.split("</think>", 1)[-1].strip()
    response = response.replace("*", "").strip()

    print(">> RESPONSE:", response)

    # Feeds the response to TTS
    text_to_speech(response)


### PIPE LISTENER ### 
def pipe_listener():
    # Listens for 'toggle' command on the pipe and updates recording state accordingly
    global record
    print(f"Listening for dwm triggers on {PIPE_PATH}...")

    while True:
        try:
            with open(PIPE_PATH, 'r') as pipe:
                print("Pipe opened for reading...")
                for line in pipe:
                    print(f"RAW PIPE INPUT: {repr(line)}")
                    cmd = line.strip()
                    if not cmd:
                        continue

                    print(f"Received command from pipe: '{cmd}'")
                    if cmd == "toggle":
                        print(f"TOGGLE received. Previous state: {record}")
                        record = not record
                        print(f"New recording state: {record}")
                        if record:
                            print("Recording started...")
                        else:
                            print("Recording stopped...")
                            process_audio()

                    elif cmd == "stop":
                        print("Received STOP command. Shutting down the LLM server manually...")
                        stop_server()

                    else:
                        print(f"Unknown command: {cmd}")

        except Exception as e:
            print(f"Pipe error: {e}")
            time.sleep(0.5)


### MAIN ###
if __name__ == "__main__":
    # For debugging
    print(f"Startup: record state = {record}")

    # Background thread for automatic shutdown
    threading.Thread(target=auto_shutdown_monitor, daemon=True).start()


    # Background threads for pipe and audio recording
    threading.Thread(target=pipe_listener, daemon=True).start()
    threading.Thread(target=record_audio, daemon=True).start()

    # Main thread kept alive
    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        print("\nShutting down...")