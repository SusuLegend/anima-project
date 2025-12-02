"""
GroqIntegration: Class for interacting with Groq API
API key is loaded from .env
"""
import os
from dotenv import load_dotenv
import requests

class GroqIntegration:
    def __init__(self, api_key: str = None, system_prompt: str = None, model: str = "llama-3.1-8b-instant"):
        load_dotenv(os.path.join(os.path.dirname(__file__), '../../.env'))
        self.api_key = api_key or os.getenv('GROQ_API_KEY')
        self.base_url = "https://api.groq.com/openai/v1/chat/completions"
        self.model = model
        if not self.api_key:
            raise ValueError("GROQ_API_KEY not found in .env or not provided.")
        self.headers = {
            "Content-Type": "application/json",
            "Authorization": f"Bearer {self.api_key}"
        }
        self.history = []  # List of dicts: {role: "user"|"assistant", content: str}
        self.system_prompt = system_prompt or "You are a helpful assistant."

    def get_response(self, prompt: str) -> str:
        # Build messages from history
        messages = []
        if self.system_prompt:
            messages.append({"role": "system", "content": self.system_prompt})
        for msg in self.history:
            messages.append({"role": msg['role'], "content": msg['content']})
        # Add current user prompt
        messages.append({"role": "user", "content": prompt})

        payload = {
            "model": self.model,
            "messages": messages
        }
        
        response = requests.post(self.base_url, headers=self.headers, json=payload)
        if response.status_code == 200:
            data = response.json()
            try:
                reply = data["choices"][0]["message"]["content"]
                # Save user prompt and assistant reply to history
                self.history.append({"role": "user", "content": prompt})
                self.history.append({"role": "assistant", "content": reply})
                return reply
            except (KeyError, IndexError):
                return "[Groq API: No response text found]"
        else:
            return f"[Groq API Error {response.status_code}: {response.text}]"

    def reset_history(self):
        self.history = []
