import os, threading, time, queue, numpy, sounddevice, requests
from subprocess import run, DEVNULL
from faster_whisper import WhisperModel
from scipy.io.wavfile import write as write_wav
from piper import PiperVoice, SynthesisConfig


### CONFIGURATIONS ###
PIPE_PATH = "/tmp/ai-assistant.pipe"
SERVER_URL = "http://127.0.0.1:8080/v1/chat/completions"
MODEL_NAME = "Qwen3-32B-UD-Q6_K_XL.gguf"

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
    run(["ffplay", "-nodisp", "-autoexit", wav_path], stdout=DEVNULL, stderr=DEVNULL)

    # Clean upfor temp files
    if os.path.exists(wav_path):
        os.remove(wav_path)


### QUERY LLM VIA HTTP ###
def llm_query(prompt):
    try:
        # Dictionary layout for data
        payload = {
            "model": MODEL_NAME,
            "messages": [
                {"role": "system", "content": "You are a concise and friendly AI assistant that gives short, accurate answers."},
                {"role": "user", "content": prompt.strip()}
            ],
            # Randomness control (deterministic --- creative)
            "temperature": 0.7
        }
        print(">> Sending a query to LLM server...")
        # Request sending
        response = requests.post(SERVER_URL, json=payload, timeout=120)
        # Checks for http errors
        response.raise_for_status()
        # Parses response JSON to python dictionary
        data = response.json()
        # Extracts generated text from JSON structure
        content = data["choices"][0]["message"]["content"]
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


### MAIN ###
if __name__ == "__main__":
    # For debugging
    print(f"Startup: record state = {record}")

    # Background threads for pipe and audio recording
    threading.Thread(target=pipe_listener, daemon=True).start()
    threading.Thread(target=record_audio, daemon=True).start()

    # Main thread kept alive
    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        print("\nShutting down...")