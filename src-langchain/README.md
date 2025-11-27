# LangChain Integration - Phase 1

This directory contains the LangChain-based implementation of the AI assistant components.

## 📁 Structure

```
src-langchain/
├── ai_brain/
│   ├── langchain_integration.py  # Unified LLM interface (Ollama + Gemini)
│   └── __init__.py
├── tools/
│   ├── langchain_tools.py        # Tool wrappers for LangChain
│   └── __init__.py
├── database/                      # (Phase 2 - RAG pipeline)
├── ui/                           # (Phase 4 - UI integration)
├── example_usage.py              # Demonstration script
└── README.md                     # This file
```

## 🚀 Phase 1 Complete

### Components Implemented:

#### 1. **langchain_integration.py** - Unified LLM Interface
- ✅ Support for both Ollama and Gemini
- ✅ Automatic conversation memory with `ConversationBufferMemory`
- ✅ Streaming support
- ✅ Easy provider switching
- ✅ Consistent API across providers

**Features:**
```python
from ai_brain.langchain_integration import create_ollama_llm, create_gemini_llm

# Ollama
llm = create_ollama_llm(
    model="llama3.2:latest",
    system_prompt="You are a helpful assistant."
)

# Gemini
llm = create_gemini_llm(
    system_prompt="You are a helpful assistant."
)

# Use them identically
response = llm.chat("Hello!")
```

#### 2. **langchain_tools.py** - Tool Wrappers
- ✅ Web search tool (DuckDuckGo)
- ✅ Weather information tool (OpenMeteo)
- ✅ Notifications tool (Gmail + System)
- ✅ Proper LangChain Tool format
- ✅ Structured tools with input schemas

**Features:**
```python
from tools.langchain_tools import get_all_tools

tools = get_all_tools()
# Returns list of LangChain Tool objects ready for agent use
```

## 📦 Dependencies Added

```
langchain>=0.1.0
langchain-community>=0.0.20
langchain-google-genai>=0.0.6
langchain-pinecone>=0.0.1
langchain-ollama>=0.1.0
```

## 🧪 Testing

Run the example script to test all components:

```bash
cd src-langchain
python example_usage.py
```

This will test:
1. Ollama conversation with memory
2. Gemini conversation
3. Tool execution (web search, weather, notifications)
4. Streaming responses
5. Memory management

## 📊 Comparison: Old vs New

### LLM Integration

**Before (src/ai_brain/):**
- 2 separate files (local_ollama_integration.py, gemini_integration.py)
- Manual conversation history tracking
- Inconsistent APIs
- No streaming support
- ~100 lines per provider

**After (src-langchain/ai_brain/):**
- 1 unified interface
- Automatic memory management via LangChain
- Consistent API regardless of provider
- Built-in streaming support
- ~300 lines total (supports both providers)

### Tools

**Before:**
- Raw Python functions
- Manual execution
- No standardization

**After:**
- LangChain Tool objects
- Standardized interface
- Ready for agent integration
- Input validation with Pydantic schemas

## 🎯 Benefits

### 1. **Code Reduction**
- Unified LLM interface eliminates duplicate code
- Standard tool format reduces boilerplate

### 2. **Consistency**
- Same API for Ollama and Gemini
- Easy to switch providers with one parameter

### 3. **Memory Management**
- Automatic conversation history
- Built-in context window handling

### 4. **Future-Ready**
- Tools ready for agent integration (Phase 3)
- Compatible with LangChain ecosystem
- Easy to add new providers/tools

## 🔄 Next Phases

### Phase 2: RAG Pipeline Refactor
- Replace custom Pinecone code with langchain-pinecone
- Use HuggingFaceEmbeddings instead of SentenceTransformer
- Implement ConversationalRetrievalChain
- **Expected: ~500 lines → ~100 lines**

### Phase 3: Agent System
- Create AgentExecutor with tools
- Automatic tool selection by LLM
- Multi-step reasoning capabilities

### Phase 4: Integration
- Update character_UI.py to use new LLM
- Update MCP server with agent endpoint
- Add streaming UI feedback

## ⚠️ Important Notes

1. **Original Code Untouched**: All original code in `src/` remains unchanged
2. **Side-by-side**: New implementation lives in `src-langchain/`
3. **Testing**: Test new components before migrating UI
4. **Gradual Migration**: Move components one at a time

## 🔧 Configuration

### Ollama
- Make sure Ollama is running: `ollama serve`
- Model will auto-download if not present

### Gemini
- Set `GEMINI_API_KEY` in `.env` file
- Get API key from: https://makersuite.google.com/app/apikey

## 📝 Usage Examples

### Example 1: Simple Chat
```python
from ai_brain.langchain_integration import create_ollama_llm

llm = create_ollama_llm()
response = llm.chat("What is Python?")
print(response)
```

### Example 2: Streaming
```python
llm = create_ollama_llm(streaming=True)
for chunk in llm.stream_response("Tell me a story"):
    print(chunk, end="", flush=True)
```

### Example 3: Using Tools
```python
from tools.langchain_tools import get_all_tools

tools = get_all_tools()
weather_tool = [t for t in tools if t.name == "weather"][0]
result = weather_tool.run("Tokyo")
print(result)
```

### Example 4: Conversation Memory
```python
llm = create_ollama_llm()
llm.chat("My favorite color is blue")
response = llm.chat("What's my favorite color?")
# LLM remembers: "Your favorite color is blue"
```

## ✅ Phase 1 Checklist

- [x] Add LangChain dependencies to requirements.txt
- [x] Create src-langchain directory structure
- [x] Implement unified LLM interface
- [x] Add conversation memory support
- [x] Support Ollama and Gemini
- [x] Add streaming capability
- [x] Wrap web search tool
- [x] Wrap weather tool
- [x] Wrap notifications tool
- [x] Create example usage script
- [x] Document implementation

## 🎉 Success Criteria Met

✅ Both LLM providers working with same interface  
✅ Conversation memory automatically managed  
✅ All 3 tools wrapped and functional  
✅ Streaming responses working  
✅ Clean separation from original code  
✅ Comprehensive examples and documentation

---

**Phase 1 Status: ✅ COMPLETE**

Ready to proceed with Phase 2 (RAG Pipeline Refactor) when you're ready!
