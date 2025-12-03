from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse
from fastapi.middleware.cors import CORSMiddleware
from pathlib import Path
import sys

PROJECT_ROOT = Path(__file__).parent.parent.resolve()
if str(PROJECT_ROOT) not in sys.path:
	sys.path.insert(0, str(PROJECT_ROOT))
	
from src.database.rag_pipeline import RAGPipeline
from src.ai_brain.gemini_integration import GeminiIntegration
from src.ai_brain.groq_integration import GroqIntegration
from src.ai_brain.function_calling import llm_tools
from fastapi import Request
import os
import json
import httpx
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

def build_tool_system_prompt() -> str:
	"""Build a system prompt that includes available tools and instructs Gemini on JSON format."""
	tools_schema = llm_tools.get_schema()
	tools_description = []
	
	for tool in tools_schema:
		params_desc = ""
		if tool.get("parameters"):
			props = tool["parameters"].get("properties", {})
			required = tool["parameters"].get("required", [])
			param_list = []
			for param_name, param_info in props.items():
				req_marker = " (required)" if param_name in required else " (optional)"
				param_list.append(f"  - {param_name}{req_marker}: {param_info.get('description', 'No description')}")
			params_desc = "\n".join(param_list)
		else:
			params_desc = "  No parameters required"
		
		tools_description.append(
			f"- {tool['name']}: {tool['description']}\n  Parameters:\n{params_desc}"
		)
	
	tools_text = "\n\n".join(tools_description)
	
	system_prompt = f"""
	You are a helpful AI assistant with access to the following tools: {tools_text}. If the user requests information that can be obtained using one of these tools, you MUST respond ONLY with a JSON object specifying the tool to use and its parameters.

	Refer : "my email, my task" as the user tasks. 

	Rules:
	1. If the user asks for something that requires a tool, respond ONLY with a valid JSON object:
	{{
		"tool": "tool_name",
		"parameters": {{ "param1": "value1", "param2": "value2" }}
	}}
	If the tool needs no parameters:
	{{
		"tool": "tool_name",
		"parameters": {{}}
	}}
	No extra text, no markdown — the response must be pure JSON.

	2. If the request does NOT require a tool, answer normally in natural language (not JSON).

	3. When using a tool, the response MUST be only the JSON object and nothing else.
	"""
	
	return system_prompt


def parse_tool_call(response: str) -> dict | None:
	"""Try to parse the response as a tool call JSON. Returns dict if valid, None otherwise."""
	response = response.strip()
	
	# Try to extract JSON if it's wrapped in markdown code blocks
	if response.startswith("```"):
		lines = response.split("\n")
		json_lines = []
		in_code_block = False
		for line in lines:
			if line.startswith("```"):
				in_code_block = not in_code_block
				continue
			if in_code_block:
				json_lines.append(line)
		response = "\n".join(json_lines).strip()
	
	try:
		data = json.loads(response)
		if isinstance(data, dict) and "tool" in data:
			return data
	except json.JSONDecodeError:
		pass
	
	return None


async def execute_tool(tool_name: str, parameters: dict, base_url: str) -> dict:
	"""Execute the specified tool with given parameters."""
	try:
		async with httpx.AsyncClient(timeout=30.0) as client:
			if tool_name == "get_gmail":
				resp = await client.get(f"{base_url}/tools/gmail")
				data = resp.json()
				# Only return subject and sender for mails if present
				filtered_emails = []
				if "emails" in data:
					for mail in data["emails"]:
						subject = mail.get("subject") or mail.get("title")
						sender = mail.get("sender") or mail.get("senderName") or mail.get("from")
						filtered_emails.append({"subject": subject, "sender": sender})
				return filtered_emails
			
			elif tool_name == "get_outlook":
				resp = await client.get(f"{base_url}/tools/outlook")
				data = resp.json()
				# Only return title for mails if present
				filtered_emails = []
				if "emails" in data:
					for mail in data["emails"]:
						subject = mail.get("subject") or mail.get("title")
						sender = mail.get("sender") or mail.get("senderName") or mail.get("from")
						filtered_emails.append({"subject": subject, "sender": sender})
				return filtered_emails
			
			elif tool_name == "get_tasks":
				# Outlook tasks are part of the outlook endpoint
				resp = await client.get(f"{base_url}/tools/outlook")
				data = resp.json()
				return {"tasks": data.get("tasks", [])}
			
			elif tool_name == "get_calendar_events":
				# Calendar events are part of the outlook endpoint
				resp = await client.get(f"{base_url}/tools/outlook")
				data = resp.json()
				return {"events": data.get("events", [])}
			
			elif tool_name == "get_whatsapp_messages":
				resp = await client.get(f"{base_url}/tools/whatsapp")
				return resp.json()
			
			elif tool_name == "get_weather_info":
				city = parameters.get("city")
				days = parameters.get("days", 1)
				formatted = parameters.get("formatted", True)
				
				if not city:
					return {"error": "City parameter is required for weather info"}
				
				from urllib.parse import urlencode
				params = urlencode({"city": city, "days": days, "formatted": formatted})
				resp = await client.get(f"{base_url}/tools/weather?{params}")
				return resp.json()
			
			elif tool_name == "search":
				query = parameters.get("query")
				max_results = parameters.get("max_results", 3)
				formatted = parameters.get("formatted", True)
				region = parameters.get("region", "us-en")
				
				if not query:
					return {"error": "Query parameter is required for search"}
				
				from urllib.parse import urlencode
				params = urlencode({"query": query, "max_results": max_results, "formatted": formatted, "region": region})
				resp = await client.get(f"{base_url}/tools/search?{params}")
				return resp.json()
			
			else:
				return {"error": f"Unknown tool: {tool_name}"}
	
	except Exception as e:
		return {"error": f"Tool execution failed: {str(e)}"}


@api.post("/gemini_chat")
async def gemini_chat(request: Request):
	"""Get a response from Gemini AI with JSON-based tool calling."""
	data = await request.json()
	user_prompt = data.get("prompt", "")
	user_system_prompt = data.get("system_prompt", None)
	
	# Build tool-aware system prompt
	tool_system_prompt = build_tool_system_prompt()
	print("built system prompt")
	print(tool_system_prompt)
	
	# Combine user's system prompt with tool instructions
	if user_system_prompt:
		combined_system_prompt = f"{user_system_prompt}\n\n{tool_system_prompt}"
	else:
		combined_system_prompt = tool_system_prompt
	print("made system prompt")
	# Initialize Gemini with tool-aware system prompt
	gemini_ai = GroqIntegration(system_prompt=combined_system_prompt)
	
	# Get Gemini's response
	response = gemini_ai.get_response(user_prompt)
	
	# Try to parse as tool call
	print("parsing tool call")
	tool_call = parse_tool_call(response)
	
	print(tool_call)
	if tool_call is None:
		# No tool call detected, return the response as-is
		print("no tool call")
		return {"reply": response}
	
	# Execute the tool
	tool_name = tool_call.get("tool", "")
	parameters = tool_call.get("parameters", {})
	
	base_url = str(request.base_url).rstrip("/")
	tool_result = await execute_tool(tool_name, parameters, base_url)
	print(f"executed tool {tool_name} with result {tool_result}")

	# Send tool result back to Gemini for final response
	follow_up_prompt = f"""The tool '{tool_name}' returned the following result:

{json.dumps(tool_result, indent=2)}

Based on this result and the user's original request: "{user_prompt}", please provide a helpful response to the user."""
	
	final_reply = gemini_ai.get_response(follow_up_prompt)
	
	return {
		"reply": final_reply,
		"tool_used": tool_name,
		"tool_result": tool_result
	}

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