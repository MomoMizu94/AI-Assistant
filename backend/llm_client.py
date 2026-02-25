import time, requests

class LLMClient():
    def __init__(self, model_name, server, conversation, temperature):
        ''' Handles communication with the local LLM

        Args: model_name (str): model name used by llama.cpp
        server: reference to local LLM server controller
        conversation: manages conversation history
        temperature: randomness / creativity factor for the model '''
        self.model_name = model_name
        self.server = server
        self.conversation = conversation
        self.temperature = temperature

    
    ### LLM QUERY FUNCTION ###
    def send_query(self, prompt):
        # Start the server if it's not running
        if not self.server.is_running():
            self.server.start()  
        
        # Update last query time
        self.server.last_query_time = time.time()

        # Add user's message to conversation
        self.conversation.append("user", prompt)

        payload = {
            "model": self.model_name,
            "messages": self.conversation.get(),
            "temperature": self.temperature
        }

        try:
            print(">> Sending a query to LLM server...")
            # Request sending
            response = requests.post(
                f"http://127.0.0.1:{self.server.port}/v1/chat/completions",
                json=payload,
                timeout=120)
            # Checks for http errors
            response.raise_for_status()
            # Exctracts the response
            data = response.json()
            raw_content = data["choices"][0]["message"]["content"]
            # Cleanup before saving
            content = self._clean_response(raw_content)
            # Add clean response to conversation history
            self.conversation.append("assistant", content)
            print(">> LLM response received.")

            return content

        except Exception as e:
            print(f">> LLM request failed due to: {e}")
            return "Error encountered while processing request."


    ### RESPONSE CLEANING ###
    def _clean_response(self, text):
        ''' Removes <think> tags and unnecessary symbols for TTS output '''
        if not text:
            return ""

        # Remove model's internal reasoning
        if "<think>" in text and "</think>" in text:
            text = text.split("</think>", 1)[-1].strip()

        # Clean asterisks
        text = text.replace("*", "").strip()
        # Clean hashtags
        text = text.replace("###", "").strip()
        # Remove horizontal dash lines
        text = text.replace("---", "").strip()

        return text