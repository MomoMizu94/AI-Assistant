### AI-Assistant ###

Use locally run AI model with locally run TTS models.

This script uses locally installed LLM model to query question you ask them about.
It takes your voice as an input, converts it to text format, gives to the LLM model, and speaks the answer for you outloud.

Requirements:
- Local LLM model
- Local Piper TTS model
- Ffmpeg for voice playback (uses ffplay)
- Python 3.10+

This runs inside a virtual environment with requirements.txt installed to your pip.
