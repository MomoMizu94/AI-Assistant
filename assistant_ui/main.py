import sys, os
from PySide6.QtWidgets import QApplication
from PySide6.QtQml import QQmlApplicationEngine

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
sys.path.append(ROOT)


from bridge.backend_bridge import BackendBridge
from audio_manager import AudioManager
from llm_client import LLMClient
from conversation_manager import ConversationManager
from llm_server import LLMServerManager
import config


def main():
    app = QApplication(sys.argv)

    audio = AudioManager(
        whisper_model=config.WHISPER_MODEL,
        piper_model=config.PIPER_MODEL,
        piper_config=config.PIPER_CONFIG,
        mic_rate=config.SAMPLE_RATE,
        tts_rate=config.PIPER_SAMPLE_RATE,
        channels=config.CHANNELS,
        record_timeout=config.RECORD_TIMEOUT
    )

    conversation = ConversationManager(config.CHAT_HISTORY_FILE)

    server = LLMServerManager(
        bin_path=config.LLM_SERVER_BIN,
        model_path=config.LLM_MODEL_PATH,
        port=config.SERVER_PORT,
        pid_file=config.LLM_PID_FILE,
        auto_shutdown=config.AUTO_SHUTDOWN
    )

    llm = LLMClient(
        model_name=config.MODEL_NAME,
        server=server,
        conversation=conversation,
        temperature=config.TEMPERATURE
    )

    backend = BackendBridge(audio, llm, conversation, server)

    engine = QQmlApplicationEngine()
    engine.rootContext().setContextProperty("backend", backend)
    engine.addImportPath(os.path.join(os.path.dirname(__file__), "ui"))

    qml_path = os.path.join(os.path.dirname(__file__), "ui/MainWindow.qml")
    engine.load(qml_path)

    if not engine.rootObjects():
        print(">> Failed to load QML UI!")
        sys.exit(-1)

    sys.exit(app.exec())

if __name__ == "__main__":
    main()
