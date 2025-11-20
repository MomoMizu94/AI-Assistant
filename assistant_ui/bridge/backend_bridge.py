from PySide6.QtCore import QObject, Signal, Slot, Property
import threading, subprocess


class BackendBridge(QObject):

    newMessage = Signal(str, str)      # role, message
    recordingChanged = Signal()
    mutedChanged = Signal()
    statusChanged = Signal()

    def __init__(self, audio_manager, llm_client, conversation, server):
        super().__init__()
        self.audio = audio_manager
        self.llm = llm_client
        self.conversation = conversation
        self.server = server

        self._recording = False
        self._muted = False
        self._status = "idle"


    # ------------------------------------------------------
    # PROPERTIES
    # ------------------------------------------------------
    @Property(bool, notify=recordingChanged)
    def isRecording(self):
        return self._recording

    @Property(bool, notify=mutedChanged)
    def isMuted(self):
        return self._muted

    @Property(str, notify=statusChanged)
    def status(self):
        return self._status

    def _setStatus(self, value):
        if self._status != value:
            self._status = value
            self.statusChanged.emit()

    # ------------------------------------------------------
    # MIC CONTROL
    # ------------------------------------------------------
    @Slot()
    def toggleMic(self):
        print("toggleMic() called (pipe-triggered)")

        # flip UI state
        self._recording = not self._recording
        self.recordingChanged.emit()

        # Send toggle to audio pipe
        try:
            subprocess.Popen(["bash", "-c", "echo toggle > /tmp/ai-assistant.pipe"])
        except Exception as e:
            print("ERROR sending toggle to pipe:", e)

    # ------------------------------------------------------
    # MUTE CONTROL
    # ------------------------------------------------------
    @Slot()
    def toggleMute(self):
        self._muted = not self._muted
        self.mutedChanged.emit()
        print("toggleMute() called →", self._muted)

    # ------------------------------------------------------
    # MESSAGE HANDLING
    # ------------------------------------------------------
    @Slot(str)
    def sendMessage(self, text):
        """Called from QML when user sends a message."""
        print("sendMessage() called with:", text)

        # Show user's message in UI immediately
        self.newMessage.emit("user", text)
        self.conversation.append("user", text)

        # Set state
        self._setStatus("thinking")

        # Run AI in background
        threading.Thread(
            target=self._run_llm_query,
            args=(text,),
            daemon=True
        ).start()

    def _run_llm_query(self, text):
        """Runs in background thread."""
        print(">>> Running LLM thread...")

        response = self.llm.send_query(text)

        # Append assistant message to history
        self.conversation.append("assistant", response)

        # Emit assistant message to UI
        self.newMessage.emit("assistant", response)

        # Play TTS if not muted
        if not self._muted:
            self._setStatus("speaking")
            self.audio.speak(response)

        # Finished
        self._setStatus("idle")