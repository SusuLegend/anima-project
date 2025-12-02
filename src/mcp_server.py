from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse
from fastapi.middleware.cors import CORSMiddleware
from fastapi_mcp import FastApiMCP 
from src.database.rag_pipeline import RAGPipeline
from src.ai_brain.gemini_integration import GeminiIntegration
from src.ai_brain.function_calling import llm_tools
from fastapi import Request
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


def get_intent_function_name(prompt: str, gemini_ai: GeminiIntegration) -> str:
    # Compose a prompt for Gemini to select the function
    tool_list = "\n".join([f"{tool['name']}: {tool['description']}" for tool in llm_tools.get_schema()])
    selection_prompt = (
        f"Given the following user request:\n{prompt}\n\n"
        f"Available functions:\n{tool_list}\n\n"
        "Which function name best matches the user's intent? Only return the function name."
    )
    function_name = gemini_ai.get_response(selection_prompt).strip()
    return function_name


@api.post("/gemini_chat")
async def gemini_chat(request: Request):
    """Get a response from Gemini AI, using intent-based tool calling."""
    data = await request.json()
    prompt = data.get("prompt", "")
    system_prompt = data.get("system_prompt", None)

    gemini_ai = GeminiIntegration(api_key=gemini_api_key, system_prompt=system_prompt)
    tool_name = get_intent_function_name(prompt, gemini_ai)

    # If no tool intent, just return Gemini's chat reply
    if tool_name.lower() == "none" or tool_name.strip() == "":
        reply = gemini_ai.get_response(prompt)
        return {"reply": reply}

    # Step 2: Call the corresponding tool function
    import requests
    base_url = str(request.base_url).rstrip("/")
    tool_result = None
    if tool_name == "get_gmail":
        resp = requests.get(f"{base_url}/tools/gmail")
        tool_result = resp.json()
    elif tool_name == "get_outlook":
        resp = requests.get(f"{base_url}/tools/get_outlook")
        tool_result = resp.json()
    elif tool_name == "get_tasks":
        resp = requests.get(f"{base_url}/tools/get_tasks")
        tool_result = resp.json()
    elif tool_name == "get_calendar_events":
        resp = requests.get(f"{base_url}/tools/get_calendar_events")
        tool_result = resp.json()
    elif tool_name == "get_whatsapp_messages":
        resp = requests.get(f"{base_url}/tools/whatsapp")
        tool_result = resp.json()
    else:
        return JSONResponse(
            status_code=422,
            content={"error": f"No tool intent detected or unknown tool: {tool_name}"},
        )

    # Step 3: Compose final prompt for Gemini
    full_prompt = f"{prompt}\n\nTool result from {tool_name}:\n{tool_result}"
    reply = gemini_ai.get_response(full_prompt)
    return {"reply": reply}

# RAG search endpoint
@api.post("/rag_search")
def rag_search(query: str, top_k: int = 3):
    """Semantic search using RAG pipeline."""
    results = rag_pipeline.search(query, top_k=top_k, return_text_only=True)
    return {"results": results}

@api.get("/")
def root():
    return {"message": "Unified MCP API is running."}



if __name__ == "__main__":
    import uvicorn
    uvicorn.run(api, host="0.0.0.0", port=8000)