"""
LangChain LLM Integration

Unified interface for multiple LLM providers using LangChain.
Supports:
- Ollama (local models like llama3.2)
- Google Gemini (cloud-based)

Features:
- Automatic conversation memory management
- Easy switching between providers
- Streaming support
- Consistent API across providers
"""

import os
from typing import Optional, Literal, Dict, Any, List
from pathlib import Path

from langchain_core.messages import HumanMessage, AIMessage, SystemMessage
from langchain_core.prompts import ChatPromptTemplate, MessagesPlaceholder
from langchain.memory import ConversationBufferMemory
from langchain.chains import LLMChain

# LLM imports
try:
    from langchain_ollama import ChatOllama
    OLLAMA_AVAILABLE = True
except ImportError:
    OLLAMA_AVAILABLE = False
    print("Warning: langchain-ollama not installed. Install with: pip install langchain-ollama")

try:
    from langchain_google_genai import ChatGoogleGenerativeAI
    GEMINI_AVAILABLE = True
except ImportError:
    GEMINI_AVAILABLE = False
    print("Warning: langchain-google-genai not installed. Install with: pip install langchain-google-genai")


class LangChainLLM:
    """
    Unified LLM interface using LangChain.
    
    Supports multiple providers with consistent API and automatic memory management.
    """
    
    def __init__(
        self,
        provider: Literal["ollama", "gemini"] = "ollama",
        model: Optional[str] = None,
        system_prompt: Optional[str] = None,
        temperature: float = 0.7,
        api_key: Optional[str] = None,
        base_url: Optional[str] = None,
        streaming: bool = False
    ):
        """
        Initialize LangChain LLM.
        
        Args:
            provider: LLM provider ("ollama" or "gemini")
            model: Model name (e.g., "llama3.2:latest", "gemini-2.0-flash-exp")
            system_prompt: System instruction for the LLM
            temperature: Sampling temperature (0.0-1.0)
            api_key: API key for cloud providers (Gemini)
            base_url: Base URL for Ollama (default: http://localhost:11434)
            streaming: Enable streaming responses
        """
        self.provider = provider
        self.model = model
        self.system_prompt = system_prompt or "You are a helpful assistant."
        self.temperature = temperature
        self.streaming = streaming
        
        # Initialize the appropriate LLM
        if provider == "ollama":
            if not OLLAMA_AVAILABLE:
                raise ImportError("langchain-ollama not installed. Install with: pip install langchain-ollama")
            
            model_name = model or "llama3.2:latest"
            base_url = base_url or "http://localhost:11434"
            
            self.llm = ChatOllama(
                model=model_name,
                temperature=temperature,
                base_url=base_url,
                streaming=streaming
            )
            
        elif provider == "gemini":
            if not GEMINI_AVAILABLE:
                raise ImportError("langchain-google-genai not installed. Install with: pip install langchain-google-genai")
            
            # Load API key from environment or parameter
            if api_key is None:
                from dotenv import load_dotenv
                load_dotenv()
                api_key = os.getenv("GEMINI_API_KEY")
            
            if not api_key:
                raise ValueError("GEMINI_API_KEY not found. Set in .env or pass as parameter.")
            
            model_name = model or "gemini-2.0-flash-exp"
            
            self.llm = ChatGoogleGenerativeAI(
                model=model_name,
                temperature=temperature,
                google_api_key=api_key,
                streaming=streaming
            )
        
        else:
            raise ValueError(f"Unsupported provider: {provider}. Use 'ollama' or 'gemini'")
        
        # Initialize memory for conversation history
        self.memory = ConversationBufferMemory(
            memory_key="chat_history",
            return_messages=True
        )
        
        # Create prompt template with memory
        self.prompt = ChatPromptTemplate.from_messages([
            ("system", self.system_prompt),
            MessagesPlaceholder(variable_name="chat_history"),
            ("human", "{input}")
        ])
        
        # Create LLM chain
        self.chain = LLMChain(
            llm=self.llm,
            prompt=self.prompt,
            memory=self.memory,
            verbose=False
        )
    
    def get_response(self, message: str) -> str:
        """
        Get response from LLM with conversation memory.
        
        Args:
            message: User message/prompt
        
        Returns:
            LLM response text
        """
        try:
            response = self.chain.invoke({"input": message})
            return response["text"]
        except Exception as e:
            return f"[LLM Error: {e}]"
    
    def chat(self, message: str) -> str:
        """Alias for get_response()"""
        return self.get_response(message)
    
    def stream_response(self, message: str):
        """
        Stream response from LLM (generator).
        
        Args:
            message: User message/prompt
        
        Yields:
            Chunks of response text
        """
        if not self.streaming:
            # If streaming not enabled, return full response
            yield self.get_response(message)
            return
        
        try:
            # For streaming, we need to use the LLM directly
            messages = []
            
            # Add system message
            messages.append(SystemMessage(content=self.system_prompt))
            
            # Add conversation history
            history = self.memory.load_memory_variables({})
            if "chat_history" in history:
                messages.extend(history["chat_history"])
            
            # Add current message
            messages.append(HumanMessage(content=message))
            
            # Stream response
            full_response = ""
            for chunk in self.llm.stream(messages):
                if hasattr(chunk, 'content'):
                    content = chunk.content
                    full_response += content
                    yield content
            
            # Save to memory after streaming completes
            self.memory.save_context(
                {"input": message},
                {"output": full_response}
            )
        
        except Exception as e:
            yield f"[LLM Error: {e}]"
    
    def clear_history(self):
        """Clear conversation history"""
        self.memory.clear()
    
    def get_history(self) -> List[Dict[str, str]]:
        """
        Get conversation history.
        
        Returns:
            List of message dicts with 'role' and 'content' keys
        """
        history = self.memory.load_memory_variables({})
        messages = history.get("chat_history", [])
        
        formatted = []
        for msg in messages:
            if isinstance(msg, HumanMessage):
                formatted.append({"role": "user", "content": msg.content})
            elif isinstance(msg, AIMessage):
                formatted.append({"role": "assistant", "content": msg.content})
        
        return formatted
    
    def set_system_prompt(self, system_prompt: str):
        """Update system prompt"""
        self.system_prompt = system_prompt
        self.prompt = ChatPromptTemplate.from_messages([
            ("system", system_prompt),
            MessagesPlaceholder(variable_name="chat_history"),
            ("human", "{input}")
        ])
        self.chain = LLMChain(
            llm=self.llm,
            prompt=self.prompt,
            memory=self.memory,
            verbose=False
        )


# Convenience factory functions
def create_ollama_llm(
    model: str = "llama3.2:latest",
    system_prompt: Optional[str] = None,
    temperature: float = 0.7,
    streaming: bool = False
) -> LangChainLLM:
    """
    Create Ollama LLM instance.
    
    Args:
        model: Ollama model name
        system_prompt: System instruction
        temperature: Sampling temperature
        streaming: Enable streaming
    
    Returns:
        Configured LangChainLLM instance
    """
    return LangChainLLM(
        provider="ollama",
        model=model,
        system_prompt=system_prompt,
        temperature=temperature,
        streaming=streaming
    )


def create_gemini_llm(
    model: str = "gemini-2.0-flash-exp",
    system_prompt: Optional[str] = None,
    temperature: float = 0.7,
    api_key: Optional[str] = None,
    streaming: bool = False
) -> LangChainLLM:
    """
    Create Gemini LLM instance.
    
    Args:
        model: Gemini model name
        system_prompt: System instruction
        temperature: Sampling temperature
        api_key: Google API key (reads from .env if not provided)
        streaming: Enable streaming
    
    Returns:
        Configured LangChainLLM instance
    """
    return LangChainLLM(
        provider="gemini",
        model=model,
        system_prompt=system_prompt,
        temperature=temperature,
        api_key=api_key,
        streaming=streaming
    )


# Example usage
if __name__ == "__main__":
    print("=" * 60)
    print("LangChain LLM Integration - Test")
    print("=" * 60)
    
    # Test Ollama
    print("\n🦙 Testing Ollama...")
    try:
        ollama_llm = create_ollama_llm(
            system_prompt="You are Chika Fujiwara from 'Kaguya-sama: Love is War'. Always respond in a cute, bubbly manner."
        )
        
        response1 = ollama_llm.chat("Hello! Who are you?")
        print(f"Ollama: {response1}")
        
        response2 = ollama_llm.chat("What's your favorite food?")
        print(f"Ollama: {response2}")
        
        print("\n📜 Conversation History:")
        for msg in ollama_llm.get_history():
            print(f"  {msg['role']}: {msg['content'][:50]}...")
    
    except Exception as e:
        print(f"❌ Ollama test failed: {e}")
    
    # Test Gemini
    print("\n" + "=" * 60)
    print("🌟 Testing Gemini...")
    try:
        gemini_llm = create_gemini_llm(
            system_prompt="You are a helpful assistant."
        )
        
        response = gemini_llm.chat("What is the capital of France?")
        print(f"Gemini: {response}")
    
    except Exception as e:
        print(f"❌ Gemini test failed: {e}")
        print("Make sure GEMINI_API_KEY is set in .env file")
