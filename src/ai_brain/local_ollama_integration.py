"""
LLM Integration for Floating Character

This module provides a function to query a local Ollama Llama 3.2:1b model via the Ollama REST API.

Requirements:
- Ollama running locally (default: http://localhost:11434)
- pip install requests
"""



# Use the ollama Python library
import ollama

OLLAMA_MODEL = "llama3.2:latest"


class OllamaConversation:
    """
    Maintains conversation history for logic flow and memory with Ollama LLM.
    """
    def __init__(self, model: str = OLLAMA_MODEL):
        self.model = model
        self.system_prompt = (
            "You are Chika Fujiwara from the anime 'Kaguya-sama: Love is War'. "
            "Always answer in a cute, bubbly, and playful manner, as if you are Chika. "
            "If asked about yourself, respond as Chika would."
        )
        self.messages = [
            {"role": "system", "content": self.system_prompt}
        ]

    def add_user_message(self, prompt: str):
        self.messages.append({"role": "user", "content": prompt})

    def add_assistant_message(self, response: str):
        self.messages.append({"role": "assistant", "content": response})

    def get_response(self, prompt: str, timeout: float = 30.0) -> str:
        self.add_user_message(prompt)
        try:
            response = ollama.chat(model=self.model, messages=self.messages)
            reply = response['message']['content'].strip()
            self.add_assistant_message(reply)
            return reply
        except Exception as e:
            return f"[LLM Error: {e}]"

# Example usage
if __name__ == "__main__":
    convo = OllamaConversation()
    print(convo.get_response("Hello, world!"))
    print(convo.get_response("What is your favorite food?"))

