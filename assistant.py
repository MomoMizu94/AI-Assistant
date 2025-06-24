import os
import threading
import time
import queue
import sounddevice
import numpy
from subprocess import run
from faster_whisper import WhisperModel
from scipy.io.wavfile import write as write_wav

# Configurations
PIPE_PATH = "/tmp/ai-assistant.pipe"
SAMPLE_RATE = 48000
CHANNELS = 1
RECORD_TIMEOUT = 0.5
LLM_COMMAND = "/home/momo/Documents/GitHub/llama.cpp/build/bin/llama-cli -m /home/momo/Documents/GitHub/llama.cpp/models/DeepSeek-Coder-V2-Lite-Instruct-Q6_K.gguf -t 6 -ngl 999 -p"
TTS_COMMAND = ["festival", "--tts"]

# Setup
if not os.path.exists(PIPE_PATH):
    os.mkfifo(PIPE_PATH)

record = False
audio_queue = queue.Queue()
model = WhisperModel("base.en", compute_type="float32")


# Callback function for audio chunks
def audio_callback(indata, frames, time_info, status):
    if record:
        audio_queue.put(indata.copy())


# Sets up audio recording
def record_audio():
    with sounddevice.InputStream(samplerate=SAMPLE_RATE, channels=CHANNELS, callback=audio_callback):
        while True:
            time.sleep(RECORD_TIMEOUT)


def process_audio():
    # Global variable, audio chunk list
    global record
    frames = []

    # Empty the queue and collection of audio chunks
    while not audio_queue.empty():
        frames.append(audio_queue.get())

    # Check for no recording
    if not frames:
        print("No audio captured.")
        return

    # Joins all audio chunks into a one file
    audio = numpy.concatenate(frames, axis=0)
    audio_path = "temp_audio.wav"
    write_wav(audio_path, SAMPLE_RATE, audio)

    # Transcribing using Faster-Whisper
    segments, _ = model.transcribe(audio_path)
    text = " ".join([seg.text for seg in segments])
    print(">> TRANSCRIPT:", text)

    # Sends the question to local LLM and captures the output
    print(">> Querying local LLM...")
    prompt = f"<|im_start|>user\n{text}<|im_end|>\n<|im_start|>assistant"
    result = run(f'{LLM_COMMAND} "{prompt}"', shell=True, capture_output = True, text = True, timeout = 20)
    print(">> RAW OUTPUT:\n", result.stdout)


    # Defensive fallback
    if result.returncode != 0:
        print("LLM command failed:", result.stderr)
        return

    # Print raw output for debugging
    print(">> Raw LLM output:")
    print(result.stdout)


    # Strip out empty lines and extract the last meaningful one
    lines = [line.strip() for line in result.stdout.strip().split("\n") if line.strip()]
    response = lines[-1] if lines else "[No meaningful output]"

    print(">> RESPONSE:", response)

    # Feeds the response to TTS
    run(TTS_COMMAND + [response])


# Waits for a command and toggles the record state. Sends the recorded audio further.
def pipe_listener():
    global record

    print(f"Listening for dwm triggers on {PIPE_PATH}...")
    while True:
        with open(PIPE_PATH, 'r') as pipe:
            for line in pipe:
                cmd = line.strip()
                if cmd == "toggle":
                    record = not record
                    if record:
                        print("Recording started...")
                    else:
                        print("Recording stopped...")
                        process_audio()


# Listens for a keybind and continuously records mic audio
if __name__ == "__main__":
    threading.Thread(target=pipe_listener, daemon=True).start()
    threading.Thread(target=record_audio, daemon=True).start()

    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        print("Shutting down...")