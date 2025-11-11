"""
LLM Integration for Floating Character

This module provides a function to query a local Ollama Llama 3.2:1b model via the Ollama REST API.

Requirements:
- Ollama running locally (default: http://localhost:11434)
- pip install requests
"""


import subprocess

OLLAMA_MODEL = "llama3.2:1b"

def get_llm_response(prompt: str, timeout: float = 30.0) -> str:
    """
    Sends a prompt to the local Ollama Llama 3.2:1b model using the ollama CLI and returns the response.
    Always instructs the LLM to respond as Chika Fujiwara from Kaguya-sama: Love is War.
    Returns a string with the LLM's reply, or an error message if failed.
    """
    system_prompt = (
        "You are Chika Fujiwara from the anime 'Kaguya-sama: Love is War'. "
        "Always answer in a cute, bubbly, and playful manner, as if you are Chika. "
        "If asked about yourself, respond as Chika would."
    )
    full_prompt = f"{system_prompt}\nUser: {prompt}\nChika:"
    try:
        result = subprocess.run([
            "ollama", "run", OLLAMA_MODEL, full_prompt
        ], capture_output=True, text=True, timeout=timeout)
        if result.returncode == 0:
            return result.stdout.strip()
        else:
            return f"[LLM Error: ollama CLI failed: {result.stderr.strip()}]"
    except Exception as e:
        return f"[LLM Error: {e}]"
print(get_llm_response("Hello, world!"))