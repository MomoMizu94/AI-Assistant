import time, os, subprocess, signal, requests

class LLMServerManager:
    def __init__(self, bin_path, model_path, port, pid_file, auto_shutdown):
        self.bin_path = bin_path
        self.model_path = model_path
        self.port = port
        self.pid_file = pid_file
        self.auto_shutdown = auto_shutdown
        self.last_query_time = time.time()


    ### SERVER LISTENER ###
    def is_running(self):
        if not os.path.exists(self.pid_file):
            return False

        # Checks if the server is still running on the background
        try:
            with open(self.pid_file) as f:
                pid = int(f.read().strip())
                os.kill(pid, 0)
                return True
        except:
            return False

    
    ### START THE SERVER ###
    def start(self):
        if self.is_running():
            print(">> LLM server is already running.")
            return

        # Start the LLM server as a bg process
        print(">> LLM server starting. Loading model to VRAM...")
        process = subprocess.Popen([
            self.bin_path,
            "-m", self.model_path,
            "-t", "16",
            "-ngl", "999",
            "--port", str(self.port)
        ])

        # Bookmarks the bg process
        with open(self.pid_file, "w") as f:
            f.write(str(process.pid))
        time.sleep(2)
        print(">> LLM server started with PID:", process.pid)

        # Wait for the model finish loading
        for _ in range(60):
            try:
                # Remove prints?
                r = requests.get(f"http://127.0.0.1:{self.port}/health", timeout=2)
                if r.status_code == 200:
                    print(">> LLM server ready to accept queries.")
                    break
            except Exception:
                pass
            time.sleep(1)
        else:
            print(">> LLM server did not respond within 60 seconds.")


    ### STOP THE SERVER ###
    def stop(self, conversation=None):
        # Stops LLM server and clears conversation history optionally
        if conversation:
            conversation.clear(keep_system=True)
            print(">> Conversation history cleared.")
        
        if not self.is_running():
            print(">> No LLM server running.")
            return

        try:
            with open(self.pid_file) as f:
                pid = int(f.read().strip())
            print(f">> Stopping LLM server with PID: {pid}")
            os.kill(pid, signal.SIGTERM)
            os.remove(self.pid_file)
            print(">> LLM server stopped. Reserved VRAM released.")
        
        except Exception as e:
            print(f">> Failed to stop LLM server: {e}")


    ### AUTO SHUTDOWN ###
    def auto_shutdown_monitor(self, conversation=None):
        # Monitors idle time and shuts down the server automatically
        while True:

            if self.is_running() and (time.time() - self.last_query_time > self.auto_shutdown):
                print(">> LLM has been idle for too long. Shutting down the server...")
                self.stop(conversation)
            time.sleep(60)