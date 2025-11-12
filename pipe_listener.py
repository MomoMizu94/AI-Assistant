import os, time

class PipeListener:
    def __init__(self, pipe_path="/tmp/ai-assistant.pipe", on_toggle=None, on_stop=None):
        self.pipe_path = pipe_path
        self.on_toggle = on_toggle
        self.on_stop = on_stop

        # Ensure clean state for the pipe
        if os.path.exists(pipe_path):
            os.remove(pipe_path)
        os.mkfifo(pipe_path)

    
    def listen(self):
        # Listens for pipe toggles
        print(f"Listening for dwm triggers on {self.pipe_path}...")
        while True:
            try:
                with open(self.pipe_path, 'r') as pipe:
                    print("Pipe opened for reading...")
                    for line in pipe:
                        cmd = line.strip()
                        if not cmd:
                            continue

                        print(f"Received command from pipe: '{cmd}'")
                        if cmd == "toggle" and self.on_toggle:
                            self.on_toggle()
                        elif cmd == "stop" and self.on_stop:
                            self.on_stop()
                        else:
                            print(f"Unknown command: {cmd}")
            except Exception as e:
                print(f"Pipe error: {e}")
                time.sleep(0.5)