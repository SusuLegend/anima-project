from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi_mcp import FastApiMCP 
from src.database.rag_pipeline import RAGPipeline
from src.ai_brain.gemini_integration import GeminiIntegration
import os
from dotenv import load_dotenv


api = FastAPI()

# Import tools_app FastAPI app
import sys
import os
from src.tools.tools_app import app as tools_app

# Mount tools_app under /tools
api.mount("/tools", tools_app)

api.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

#####################
### PINECONE INIT ###
#####################

load_dotenv(os.path.join(os.path.dirname(__file__), '../.env'))
pinecone_api_key = os.getenv('PINECONE_API_KEY')
pinecone_index_name = os.getenv('PINECONE_INDEX_NAME', 'rag-documents')
pinecone_embedding_model = os.getenv('PINECONE_EMBEDDING_MODEL', 'all-MiniLM-L6-v2')
rag_pipeline = RAGPipeline(
    pinecone_api_key=pinecone_api_key,
    index_name=pinecone_index_name,
    embedding_model=pinecone_embedding_model
)

gemini_api_key = os.getenv('GEMINI_API_KEY')
gemini_system_prompt = os.getenv('GEMINI_SYSTEM_PROMPT', 'You are a helpful assistant.')
gemini_ai = GeminiIntegration(api_key=gemini_api_key, system_prompt=gemini_system_prompt)

mcp = FastApiMCP(api)
# RAG Pipeline MCP Tool
@mcp.tools()
def gemini_chat(prompt: str):
    """Get a response from Gemini AI."""
    reply = gemini_ai.get_response(prompt)
    return {"reply": reply}

# RAG Pipeline MCP Tool
@mcp.tools()
def rag_search(query: str, top_k: int = 3):
    """Semantic search using RAG pipeline."""
    results = rag_pipeline.search(query, top_k=top_k, return_text_only=True)
    return {"results": results}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(api, host="0.0.0.0", port=8000)
