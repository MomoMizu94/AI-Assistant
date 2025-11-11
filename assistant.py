import os, threading, time, queue, numpy, sounddevice, requests, subprocess, json
from faster_whisper import WhisperModel
from scipy.io.wavfile import write as write_wav
from piper import PiperVoice, SynthesisConfig
from conversation_manager import ConversationManager
from llm_server import LLMServerManager


### CONFIGURATIONS ###
PIPE_PATH = "/tmp/ai-assistant.pipe"
MODEL_NAME = "Qwen3-32B-UD-Q6_K_XL.gguf"
SERVER_PORT = 8080
AUTO_SHUTDOWN = 600
CHAT_HISTORY_FILE = "/tmp/assistant_history.json"

# Audio tuning
SAMPLE_RATE = 48000
PIPER_SAMPLE_RATE = 22050
CHANNELS = 1
RECORD_TIMEOUT = 1.0

# TTS
PIPER_MODEL = os.path.expanduser("~/Documents/GitHub/AI-Assistant/TTS/models/en_US-alexa-medium/alexa.onnx")
PIPER_CONFIG = os.path.expanduser("~/Documents/GitHub/AI-Assistant/TTS/models/en_US-alexa-medium/alexa.onnx.json")
PIPER_VOICE = PiperVoice.load(PIPER_MODEL, config_path=PIPER_CONFIG)
SYNTH_CONFIG = SynthesisConfig(length_scale=0.95, noise_scale=0.3, noise_w_scale=0.9)


### INITIALIZATION ###
# Ensure clean state for the pipe
if os.path.exists(PIPE_PATH):
    os.remove(PIPE_PATH)
os.mkfifo(PIPE_PATH)

###
conversation = ConversationManager(CHAT_HISTORY_FILE)
server = LLMServerManager(
    bin_path = os.path.expanduser("~/Documents/GitHub/llama.cpp/build/bin/llama-server"),
    model_path = os.path.expanduser("~/Documents/GitHub/llama.cpp/models/Qwen3-32B-UD-Q6_K_XL.gguf"),
    port = 8080,
    pid_file = "/tmp/llm_server.pid",
    auto_shutdown=AUTO_SHUTDOWN
)

# Recording state
record = False
# Holds recorded audio chunks
audio_queue = queue.Queue()

# Speech recognition model
model = WhisperModel("base.en", device="cpu", compute_type="int8")


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
    # Start the server if it's not running
    if not server.is_running():
        server.start()
    
    server.last_query_time = time.time()

    # Add message to memory
    conversation.append("user", prompt)

    # Dictionary layout for data
    payload = {
        "model": MODEL_NAME,
        "messages": conversation.get(),
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
        conversation.append("assistant", content)
        print(content)
        print(content.strip())
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
                        server.stop(conversation)

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
    threading.Thread(target=server.auto_shutdown_monitor, args=(conversation,), daemon=True).start()


    # Background threads for pipe and audio recording
    threading.Thread(target=pipe_listener, daemon=True).start()
    threading.Thread(target=record_audio, daemon=True).start()

    # Main thread kept alive
    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        print("\nShutting down...")