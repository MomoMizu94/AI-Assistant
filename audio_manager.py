import os, time, queue, numpy, sounddevice, subprocess
from faster_whisper import WhisperModel
from scipy.io.wavfile import write as write_wav
from piper import PiperVoice, SynthesisConfig

class AudioManager:
    def __init__(self,whisper_model, piper_model, piper_config,
                mic_rate, tts_rate, channels, record_timeout):
        # Recording setup
        self.mic_rate = mic_rate
        self.channels = channels
        self.record_timeout = record_timeout
        self.audio_queue = queue.Queue()
        self.recording=False

        # Whisper setup
        print(">> Loading Whisper model...")
        self.whisper = WhisperModel(whisper_model, device="cpu", cpu_threads=16, compute_type="int8")

        # Piper tts setup
        if piper_model and piper_config:
            print(">> Loading Piper TTS voice...")
            self.voice = PiperVoice.load(piper_model, config_path=piper_config)
            self.tts_config = SynthesisConfig(length_scale=0.95, noise_scale=0.3, noise_w_scale=0.9)
            self.tts_rate = tts_rate
        else:
            self.voice = None

    # Audio input
    def _callback(self, indata, frames, time_info, status):
        if self.recording:
            self.audio_queue.put(indata.copy())

    # Recording
    def record_loop(self):
        # Listens to audio continiously and stores chunks into a queue
        with sounddevice.InputStream(samplerate=self.mic_rate, channels=self.channels, 
                                    callback=self._callback):
            while True:
                time.sleep(self.record_timeout)

    # Transcription
    def transcribe(self):
        # Create an empty list and append audio chunks to it
        frames = []
        while not self.audio_queue.empty():
            frames.append(self.audio_queue.get())

        # Checks for no recording
        if not frames:
            print(">> No audio captured.")
            return None
        
        # Joins all audio chunks into a temporary .wav file
        audio = numpy.concatenate(frames, axis=0)
        temp_path = "temp_audio.wav"
        write_wav(temp_path, self.mic_rate, audio)

        # Transcribe the audio
        segments, _ = self.whisper.transcribe(temp_path, language="en", task="transcribe")
        text = " ".join([seg.text for seg in segments])

        # Clean upfor temp files
        os.remove(temp_path)

        print(">> TRANSCRIPT:", text)
        return text.strip()

    # Text-To-Speech
    def speak(self, text):
        # Generate audio output from text
        if not text or not self.voice:
            return
        print(">> Generating speech...")

        # Generate audio chunks from provided response text
        audio_chunks = list(self.voice.synthesize(text, syn_config=self.tts_config))
        if not audio_chunks:
            print(">> Piper returned no audio.")
            return

        # Extract audio chunks into an array
        audio_arrays = []
        for chunk in audio_chunks:
            audio_arrays.append(chunk.audio_int16_array)
        audio = numpy.concatenate(audio_arrays)

        # Write the audio data to a wav file
        wav_path = "response.wav"
        write_wav(wav_path, self.tts_rate, audio)

        # Play generated audio file with ffplay
        subprocess.run(["ffplay", "-nodisp", "-autoexit", wav_path],
                        stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        
        # Cleanup for temp files
        os.remove(wav_path)