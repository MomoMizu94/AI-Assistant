import os
import threading
import time
import queue
import sounddevice
import numpy
from subprocess import run
from faster_whisper import WhisperModel
from scipy.io.wavfile import write as write_wav

### Configurations ###
# Pipe triggers the script via dwm keybind
PIPE_PATH = "/tmp/ai-assistant.pipe"

# Audio tuning
SAMPLE_RATE = 48000
CHANNELS = 1
RECORD_TIMEOUT = 1.0

# Commands for locally run LLM and TTS
LLM_COMMAND = "/home/momo/Documents/GitHub/llama.cpp/build/bin/llama-cli -m /home/momo/Documents/GitHub/llama.cpp/models/DeepSeek-Coder-V2-Lite-Instruct-Q6_K.gguf -t 6 -ngl 999 --single-turn -p"
TTS_COMMAND = ["festival", "--tts"]

### Initialization ###
# Ensure clean state for the pipe
if os.path.exists(PIPE_PATH):
    os.remove(PIPE_PATH)
os.mkfifo(PIPE_PATH)

# Recording state
record = False
# Holds recorded audio chunks
audio_queue = queue.Queue()
# Speech recognition model
model = WhisperModel("base.en", compute_type="float32")


### Audio callback ###
def audio_callback(indata, frames, time_info, status):
    # Places audio chunks into a queue while recording
    if record:
        audio_queue.put(indata.copy())


### Audio record loop ###
def record_audio():
    # Opens audio stream and starts calling for audio_callback in another thread
    with sounddevice.InputStream(samplerate=SAMPLE_RATE, channels=CHANNELS, callback=audio_callback):
        while True:
            time.sleep(RECORD_TIMEOUT)


### TTS function ###
def text_to_speech(text):
    # Sends the response to TTS of choice (Festival)
    run(TTS_COMMAND, input=text, text=True)


### Audio processing function ###
def process_audio():
    # Processes recorded audio by transcribing it, sending it to LLM, and speaking out the response
    global record
    print(">> Starting audio processing...")

    # Create an empty list and append audio chunks to it
    frames = []
    while not audio_queue.empty():
        frames.append(audio_queue.get())

    # Checks for no recording
    if not frames:
        print("No audio captured.")
        return

    # Joins all audio chunks into a .wav file
    audio = numpy.concatenate(frames, axis=0)
    audio_path = "temp_audio.wav"
    write_wav(audio_path, SAMPLE_RATE, audio)

    # Transcribe the audio
    segments, _ = model.transcribe(audio_path)
    text = " ".join([seg.text for seg in segments])
    print(">> TRANSCRIPT:", text)

    # Sends the question to LLM and captures the output
    print(">> Querying local LLM...")
    prompt = f"<|im_start|>user\n{text}<|im_end|>\n<|im_start|>assistant"
    result = run(f'{LLM_COMMAND} "{prompt}"', shell=True, capture_output = True, text = True, timeout = 30)

    # Defensive fallback
    if result.returncode != 0:
        print("LLM command failed:", result.stderr)
        return

    # Extract the response
    start_marker = "<|im_start|>assistant"
    response = result.stdout.split(start_marker, 1)[-1].strip()
    response = response.removesuffix("[end of text]").strip()

    if response.lower().startswith("assistant:"):
        response = response[len("assistant:"):].strip()

    response = response.replace("*", "")
    print(">> RESPONSE:", response)

    # Feeds the response to TTS
    text_to_speech(response)


### Pipe listener ###
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
                    print(f"TOGGLE received. Previous state: {record}")
                    record = not record
                    print(f"New recording state: {record}")
                    if record:
                        print("Recording started...")
                    else:
                        print("Recording stopped...")
                        process_audio()
        except Exception as e:
            print(f"Pipe error: {e}")
            time.sleep(0.5)


### Main ###
if __name__ == "__main__":
    # Prints initial record state, for debugging
    print(f"Startup: record state = {record}")
    # Background threads
    threading.Thread(target=pipe_listener, daemon=True).start()
    threading.Thread(target=record_audio, daemon=True).start()

    # Main thread kept alive
    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        print("Shutting down...")