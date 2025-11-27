"""
LangChain Integration - Example Usage

This script demonstrates how to use the new LangChain-based components:
1. LangChain LLM (Ollama/Gemini) with conversation memory
2. LangChain Tools (web search, weather, notifications)
3. Combined usage examples

Run this to test the Phase 1 implementation.
"""

import sys
from pathlib import Path

# Add src-langchain to path
sys.path.insert(0, str(Path(__file__).parent))

from ai_brain.langchain_integration import (
    LangChainLLM,
    create_ollama_llm,
    create_gemini_llm
)
from tools.langchain_tools import (
    get_all_tools,
    print_tool_info,
    get_tool_names
)


def example_1_basic_ollama():
    """Example 1: Basic Ollama conversation"""
    print("\n" + "=" * 70)
    print("EXAMPLE 1: Basic Ollama Conversation")
    print("=" * 70)
    
    try:
        # Create Ollama LLM
        llm = create_ollama_llm(
            model="llama3.2:latest",
            system_prompt="You are Chika Fujiwara from 'Kaguya-sama: Love is War'. Respond in a cute, bubbly manner.",
            temperature=0.7
        )
        
        print("\n🦙 Ollama LLM created successfully")
        print(f"Provider: {llm.provider}")
        print(f"Model: {llm.model}")
        
        # Have a conversation
        print("\n💬 Starting conversation...")
        
        response1 = llm.chat("Hello! Who are you?")
        print(f"\n👤 User: Hello! Who are you?")
        print(f"🤖 Chika: {response1}")
        
        response2 = llm.chat("What's your favorite food?")
        print(f"\n👤 User: What's your favorite food?")
        print(f"🤖 Chika: {response2}")
        
        # Show conversation history
        print("\n📜 Conversation History:")
        for msg in llm.get_history():
            role_emoji = "👤" if msg['role'] == 'user' else "🤖"
            print(f"  {role_emoji} {msg['role']}: {msg['content'][:60]}...")
        
        return True
    
    except Exception as e:
        print(f"\n❌ Error: {e}")
        print("Make sure Ollama is running: ollama serve")
        return False


def example_2_gemini():
    """Example 2: Gemini conversation"""
    print("\n" + "=" * 70)
    print("EXAMPLE 2: Gemini Conversation")
    print("=" * 70)
    
    try:
        # Create Gemini LLM
        llm = create_gemini_llm(
            system_prompt="You are a helpful assistant that provides concise, accurate answers."
        )
        
        print("\n🌟 Gemini LLM created successfully")
        print(f"Provider: {llm.provider}")
        print(f"Model: {llm.model}")
        
        # Ask a question
        print("\n💬 Asking question...")
        response = llm.chat("What is the capital of Japan?")
        print(f"\n👤 User: What is the capital of Japan?")
        print(f"🤖 Gemini: {response}")
        
        return True
    
    except Exception as e:
        print(f"\n❌ Error: {e}")
        print("Make sure GEMINI_API_KEY is set in .env file")
        return False


def example_3_tools():
    """Example 3: Using LangChain tools"""
    print("\n" + "=" * 70)
    print("EXAMPLE 3: LangChain Tools")
    print("=" * 70)
    
    # Show available tools
    print_tool_info()
    
    # Get all tools
    tools = get_all_tools()
    
    if not tools:
        print("\n⚠️ No tools available. Check if src/tools modules are accessible.")
        return False
    
    print(f"\n✅ Loaded {len(tools)} tools: {get_tool_names()}")
    
    # Test web search tool
    print("\n" + "-" * 70)
    print("Testing Web Search Tool")
    print("-" * 70)
    
    web_search_tool = next((t for t in tools if t.name == "web_search"), None)
    if web_search_tool:
        print("\n🔍 Searching for: 'Python programming'")
        try:
            result = web_search_tool.run("Python programming")
            print(result[:300] + "..." if len(result) > 300 else result)
        except Exception as e:
            print(f"❌ Error: {e}")
    
    # Test weather tool
    print("\n" + "-" * 70)
    print("Testing Weather Tool")
    print("-" * 70)
    
    weather_tool = next((t for t in tools if t.name == "weather"), None)
    if weather_tool:
        print("\n🌤️ Getting weather for: Tokyo")
        try:
            result = weather_tool.run("Tokyo")
            print(result)
        except Exception as e:
            print(f"❌ Error: {e}")
    
    return True


def example_4_streaming():
    """Example 4: Streaming responses"""
    print("\n" + "=" * 70)
    print("EXAMPLE 4: Streaming Responses")
    print("=" * 70)
    
    try:
        # Create LLM with streaming enabled
        llm = create_ollama_llm(
            system_prompt="You are a helpful assistant.",
            streaming=True
        )
        
        print("\n🦙 Ollama LLM with streaming created")
        print("\n💬 Asking: 'Tell me a short joke'")
        print("🤖 Response: ", end="", flush=True)
        
        # Stream the response
        for chunk in llm.stream_response("Tell me a short joke"):
            print(chunk, end="", flush=True)
        
        print("\n")
        return True
    
    except Exception as e:
        print(f"\n❌ Error: {e}")
        return False


def example_5_memory_management():
    """Example 5: Memory management"""
    print("\n" + "=" * 70)
    print("EXAMPLE 5: Memory Management")
    print("=" * 70)
    
    try:
        llm = create_ollama_llm(system_prompt="You are a helpful assistant.")
        
        # Chat 1
        llm.chat("My name is Alice")
        print("✅ Told LLM: 'My name is Alice'")
        
        # Chat 2
        response = llm.chat("What is my name?")
        print(f"🤖 LLM remembers: {response}")
        
        # Show history
        print(f"\n📜 History has {len(llm.get_history())} messages")
        
        # Clear history
        llm.clear_history()
        print("\n🗑️ Cleared conversation history")
        
        # Try again
        response = llm.chat("What is my name?")
        print(f"🤖 After clearing: {response}")
        
        return True
    
    except Exception as e:
        print(f"\n❌ Error: {e}")
        return False


def main():
    """Run all examples"""
    print("=" * 70)
    print("LANGCHAIN INTEGRATION - PHASE 1 EXAMPLES")
    print("=" * 70)
    print("\nThis demonstrates the new LangChain-based components:")
    print("  ✓ Unified LLM interface (Ollama & Gemini)")
    print("  ✓ Conversation memory management")
    print("  ✓ LangChain tool wrappers")
    print("  ✓ Streaming support")
    
    # Run examples
    examples = [
        ("Basic Ollama Conversation", example_1_basic_ollama),
        ("Gemini Conversation", example_2_gemini),
        ("LangChain Tools", example_3_tools),
        ("Streaming Responses", example_4_streaming),
        ("Memory Management", example_5_memory_management),
    ]
    
    results = {}
    
    for name, func in examples:
        try:
            success = func()
            results[name] = "✅ PASSED" if success else "⚠️ FAILED"
        except KeyboardInterrupt:
            print("\n\n⚠️ Interrupted by user")
            break
        except Exception as e:
            print(f"\n❌ Unexpected error in {name}: {e}")
            results[name] = "❌ ERROR"
    
    # Summary
    print("\n" + "=" * 70)
    print("SUMMARY")
    print("=" * 70)
    for name, status in results.items():
        print(f"{status} {name}")
    
    print("\n✨ Phase 1 implementation complete!")
    print("\nNext steps:")
    print("  • Phase 2: Refactor RAG pipeline with LangChain")
    print("  • Phase 3: Build agent system for automatic tool selection")
    print("  • Phase 4: Update MCP server and UI to use new components")


if __name__ == "__main__":
    main()
