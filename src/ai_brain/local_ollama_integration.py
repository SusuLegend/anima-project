"""Local Ollama integration compatible with the chat pipeline."""

from typing import Any
import ollama


class LocalOllamaIntegration:
    def __init__(self, model: str = "llama3.2:latest", system_prompt: str | None = None):
        self.model = model
        self.system_prompt = system_prompt or "You are a helpful assistant."
        self.history: list[dict[str, Any]] = []

    def get_response(self, prompt: str) -> str:
        messages: list[dict[str, str]] = []
        if self.system_prompt:
            messages.append({"role": "system", "content": self.system_prompt})
        for msg in self.history:
            messages.append({"role": msg["role"], "content": msg["content"]})
        messages.append({"role": "user", "content": prompt})

        try:
            response = ollama.chat(model=self.model, messages=messages)
            reply = (response.get("message", {}).get("content") or "").strip()
            if not reply:
                return "[Ollama: No response text found]"
            self.history.append({"role": "user", "content": prompt})
            self.history.append({"role": "assistant", "content": reply})
            return reply
        except Exception as e:
            return f"[Ollama Error: {e}]"

    def reset_history(self):
        self.history = []

