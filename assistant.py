import evdev
import sounddevice
import numpy
import wave
import subprocess
import pyttsx3
from faster_whisper import WhisperModel

# Configurations
DEVICE_PATH = "/dev/input/by-id/usb-UBEST_zoom75_wireless_067E0F9F3C18-event-kbd"
