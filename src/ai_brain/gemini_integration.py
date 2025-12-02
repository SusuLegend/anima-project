"""
GeminiIntegration: Class for interacting with Google Gemini API
API key is loaded from .env
"""
import os
from dotenv import load_dotenv
import requests

class GeminiIntegration:
    def __init__(self, api_key: str = None, system_prompt: str = None):
        load_dotenv(os.path.join(os.path.dirname(__file__), '../../.env'))
        self.api_key = api_key or os.getenv('GEMINI_API_KEY')
        self.base_url = "https://generativelanguage.googleapis.com/v1beta/models/gemini-2.0-flash-lite"
        if not self.api_key:
            raise ValueError("GEMINI_API_KEY not found in .env or not provided.")
        self.headers = {
            "Content-Type": "application/json"
        }
        self.history = []  # List of dicts: {role: "user"|"model", text: str}
        self.system_prompt = system_prompt or "You are a helpful assistant."

    def get_response(self, prompt: str) -> str:
        # Build context from history
        contents = []
        if self.system_prompt:
            contents.append({"parts": [{"text": self.system_prompt}]})
        for msg in self.history:
            contents.append({"parts": [{"text": msg['text']}], "role": msg['role']})
        # Add current user prompt
        contents.append({"parts": [{"text": prompt}], "role": "user"})

        payload = {"contents": contents}
        params = {"key": self.api_key}
        response = requests.post(self.base_url, headers=self.headers, params=params, json=payload)
        if response.status_code == 200:
            data = response.json()
            try:
                reply = data["candidates"][0]["content"]["parts"][0]["text"]
                # Save user prompt and model reply to history
                self.history.append({"role": "user", "text": prompt})
                self.history.append({"role": "model", "text": reply})
                return reply
            except (KeyError, IndexError):
                return "[Gemini API: No response text found]"
        else:
            return f"[Gemini API Error {response.status_code}: {response.text}]"

    def reset_history(self):
        self.history = []
