from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from pathlib import Path
import sys
from typing import Any
import re
import time

PROJECT_ROOT = Path(__file__).parent.parent.resolve()
if str(PROJECT_ROOT) not in sys.path:
	sys.path.insert(0, str(PROJECT_ROOT))

CONFIG_PATH = PROJECT_ROOT / "config.json"
	
from src.database.rag_pipeline import RAGPipeline
from src.ai_brain.groq_integration import GroqIntegration
from src.ai_brain.local_ollama_integration import LocalOllamaIntegration
from src.ai_brain.function_calling import llm_tools
import os
import json
import httpx
from dotenv import load_dotenv
from datetime import datetime

api = FastAPI()

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
pinecone_api_key = os.getenv('PINECONE_API_KEY', '')
pinecone_index_name = os.getenv('PINECONE_INDEX_NAME', 'rag-documents')
pinecone_embedding_model = os.getenv('PINECONE_EMBEDDING_MODEL', 'all-MiniLM-L6-v2')
rag_pipeline = RAGPipeline(
	pinecone_api_key=pinecone_api_key,
	index_name=pinecone_index_name,
	embedding_model=pinecone_embedding_model
)

CONTROL_START_TOOLS = {"start_session", "session_start"}
CONTROL_STOP_TOOLS = {"stop_session", "session_stop"}
CONTROL_TOOLS = CONTROL_START_TOOLS | CONTROL_STOP_TOOLS
MAX_SESSION_TURNS = 8
ORCHESTRATION_TIMEOUT_SECONDS = 45.0

FORCED_CLOSE_HEADER = (
	"[SESSION_GUARD_NOTICE] You reached the tool-session guard limit. "
	"You must respond immediately in this turn and include stop_session in your JSON tool block."
)


def _terminal_log(label: str, payload: Any = None) -> None:
	"""Write structured runtime logs to terminal."""
	stamp = datetime.now().astimezone().isoformat()
	print(f"[MCP][{stamp}] {label}")
	if payload is None:
		return
	if isinstance(payload, str):
		print(payload)
		return
	try:
		print(json.dumps(payload, indent=2, ensure_ascii=False, default=str))
	except Exception:
		print(str(payload))


def _load_runtime_llm_config() -> dict[str, Any]:
	"""Load llm settings from config.json."""
	default_cfg: dict[str, Any] = {"model": "groq", "timeout": 30.0}
	try:
		if CONFIG_PATH.exists():
			with open(CONFIG_PATH, "r", encoding="utf-8") as f:
				cfg = json.load(f)
			llm_cfg = cfg.get("llm", {})
			if isinstance(llm_cfg, dict):
				default_cfg.update(llm_cfg)
	except Exception as e:
		_terminal_log("Config load warning", {"error": str(e)})
	return default_cfg


def _create_llm_client(system_prompt: str):
	"""Create llm client based on configured model value."""
	llm_cfg = _load_runtime_llm_config()
	model = str(llm_cfg.get("model", "groq") or "groq").strip()
	model_lower = model.lower()

	# Ollama models are typically formatted like "llama3.2:3b".
	if ":" in model or model_lower.startswith(("llama", "mistral", "qwen", "phi", "gemma")):
		_terminal_log("LLM backend selected", {"backend": "ollama", "model": model})
		return LocalOllamaIntegration(model=model, system_prompt=system_prompt)

	if model_lower.startswith("groq"):
		_terminal_log("LLM backend selected", {"backend": "groq", "model": "llama-3.1-8b-instant"})
		return GroqIntegration(system_prompt=system_prompt)

	# Fallback to local Ollama for unknown backend strings.
	_terminal_log("LLM backend selected", {"backend": "ollama", "model": model})
	return LocalOllamaIntegration(model=model, system_prompt=system_prompt)


def _load_memory() -> str:
	"""Load persistent memory from /memory/memory.md."""
	memory_path = PROJECT_ROOT / "memory" / "memory.md"
	if not memory_path.exists():
		return ""
	try:
		with open(memory_path, "r", encoding="utf-8") as f:
			content = f.read().strip()
		return content
	except Exception as e:
		_terminal_log("Memory load error", str(e))
		return ""


def _save_memory(content: str) -> str:
	"""Append content to persistent memory file."""
	memory_dir = PROJECT_ROOT / "memory"
	memory_path = memory_dir / "memory.md"
	try:
		memory_dir.mkdir(parents=True, exist_ok=True)
		timestamp = datetime.now().astimezone().isoformat()
		with open(memory_path, "a", encoding="utf-8") as f:
			f.write(f"\n[{timestamp}] {content}\n")
		_terminal_log("Memory saved", {"content": content})
		return f"Memory saved: {content}"
	except Exception as e:
		_terminal_log("Memory save error", str(e))
		return f"Failed to save memory: {str(e)}"


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
	# Use local timezone-aware current time so the model sees a real timestamp.
	current_time = datetime.now().astimezone().isoformat()

	system_prompt = f"""
	You are a helpful AI assistant with access to the following tools: {tools_text}.

	Your goal is to fulfill the user's request as accurately and efficiently as possible.
	Everything that can change with time should be verified with a tool call.
	ONLY USE THE TOOLS MENTIONED ABOVE.

	General behavior:
	- Answer the user's actual request directly. Be extremely concise. Keep natural text response within 20-25 word.
	- Do not invent facts, data, or tool results. Any fact you can confirm with a tool should be confirmed by calling that tool.
	- Do not assume information that should be retrieved from a tool.
	- Make only minimal operational assumptions when necessary, and state them clearly.
	- Do not apologize for lacking information before attempting an appropriate tool call.

	User-owned data interpretation:
	- Treat references such as "my email", "my task", "my outlook", and "my whatsapp" as requests involving the user's personal or connected data.
	- Prefer tool calls over model knowledge for those requests.

	Decision policy:
	1. First determine whether the request can be answered reliably from general knowledge alone.
	2. You MUST use a tool when:
	- the request depends on current or time-sensitive information
	- the request refers to the user's own data, messages, tasks, files, or accounts
	- the request explicitly asks to search, retrieve, check, send, update, or inspect something
	- the answer should come from a tool instead of general knowledge
	3. If a tool is required, do not answer from memory in place of the tool.
	4. If a tool is not required, answer normally in natural language.
	5. If required information for a tool call is missing, ask for only the minimum missing information.

	Tool-call output rules:
	- If one or more tool calls are needed, respond with:
	1. a brief explanation of why the tool is needed
	2. exactly one fenced JSON code block at the end
	- Session protocol is mandatory for tool workflows.
	- If any executable tool is required, include start_session before or with the first executable tool call.
	- While session is active, you may include user-visible progress text outside JSON.
	- When the mission is fulfilled, include stop_session to close the session.
	- stop_session must be emitted in the same response as the final user-facing answer text outside the JSON block.
	- The JSON block must contain a valid JSON array.
	- If a tool takes no parameters, use an empty object.
	- Do not emit executable tools after stop_session. Do not mention not using a tool after this
	- Never output bare tool names in prose. If a tool is needed, it must appear in the JSON block.

	Format examples:

	```json
	[
	{{
		"tool": "tool_name",
		"parameters": {{
		"param1": "value1"
		}}
	}}
	]
	````

	```json
	[
	{{
		"tool": "tool_one",
		"parameters": {{}}
	}},
	{{
		"tool": "tool_two",
		"parameters": {{
		"paramA": "valueA"
		}}
	}}
	]
	```

	Natural-language output rules:

	* If no tool is needed, answer normally in natural language.
	* Do not include JSON if no tool is needed.

	Tool selection rules:

	* If the answer cannot be established reliably from built-in knowledge and an available tool can verify it, prefer the tool.
	* If multiple tools are needed, choose the smallest valid sequence.
	* Do not call tools redundantly.

	Failure handling:

	* If a tool would help but the needed input is missing, ask a targeted follow-up question.
	* If a tool is unavailable or unsuitable, say so briefly and provide the best safe answer possible.

	Context:

	* Current time is {current_time}
	"""
	
	# Load and inject persistent memory if available
	loaded_memory = _load_memory()
	if loaded_memory:
		system_prompt += f"""
	Persistent Memory (facts about the user to remember and reference):
	{loaded_memory}
	"""
		
	return system_prompt


def _trim_visible_text(text: str) -> str:
	"""Strip trailing spaces from each line and trim overall text."""
	return "\n".join(line.rstrip() for line in text.splitlines()).strip()


def _normalize_commands(raw: Any) -> list[dict[str, Any]]:
	"""Normalize parsed JSON into a list of command objects."""
	if isinstance(raw, dict):
		raw = [raw]
	if not isinstance(raw, list):
		return []

	commands: list[dict[str, Any]] = []
	for item in raw:
		if not isinstance(item, dict):
			continue
		tool_name = item.get("tool")
		if not isinstance(tool_name, str) or not tool_name:
			continue
		if tool_name == "session_start":
			tool_name = "start_session"
		elif tool_name == "session_stop":
			tool_name = "stop_session"
		parameters = item.get("parameters", {})
		if not isinstance(parameters, dict):
			parameters = {}
		commands.append({"tool": tool_name, "parameters": parameters})
	return commands


def _inject_control_tools_from_text(response: str, commands: list[dict[str, Any]]) -> list[dict[str, Any]]:
	"""Detect session control tool mentions in raw text and inject canonical commands."""
	text = (response or "").lower()
	tools_found: list[str] = []
	if re.search(r"\b(start_session|session_start)\b", text):
		tools_found.append("start_session")
	if re.search(r"\b(stop_session|session_stop)\b", text):
		tools_found.append("stop_session")

	if not tools_found:
		return commands

	existing_tools = {cmd.get("tool") for cmd in commands}
	for tool_name in tools_found:
		if tool_name not in existing_tools:
			commands.append({"tool": tool_name, "parameters": {}})
			existing_tools.add(tool_name)

	return commands


def _inject_executable_tools_from_text(response: str, commands: list[dict[str, Any]]) -> list[dict[str, Any]]:
	"""Best-effort recovery when model mentions a known tool in prose without JSON."""
	if commands:
		return commands

	text = (response or "")
	text_lower = text.lower()
	intent_markers = ("use", "call", "check", "checking", "fetch", "retrieve", "look up", "search")
	if not any(marker in text_lower for marker in intent_markers):
		return commands

	for tool in llm_tools.get_schema():
		name = tool.get("name") if isinstance(tool, dict) else None
		if not isinstance(name, str) or not name or name in CONTROL_TOOLS:
			continue
		if re.search(rf"\b{re.escape(name)}\b", text):
			commands.append({"tool": name, "parameters": {}})

	return commands


def parse_llm_response(response: str) -> tuple[str, list[dict[str, Any]], bool]:
	"""Parse visible text and JSON command block from model output."""
	response = response or ""
	code_blocks = list(re.finditer(r"```(?:json)?\s*(.*?)```", response, flags=re.IGNORECASE | re.DOTALL))

	visible_parts: list[str] = []
	commands: list[dict[str, Any]] = []
	parse_error = False
	last_end = 0

	for match in code_blocks:
		visible_parts.append(response[last_end:match.start()])
		block_content = match.group(1).strip()
		if commands:
			last_end = match.end()
			continue
		try:
			parsed = json.loads(block_content)
			commands = _normalize_commands(parsed)
		except json.JSONDecodeError:
			parse_error = True
		last_end = match.end()

	if code_blocks:
		visible_parts.append(response[last_end:])
	else:
		visible_parts.append(response)
		stripped = response.strip()
		if stripped.startswith("[") or stripped.startswith("{"):
			try:
				commands = _normalize_commands(json.loads(stripped))
			except json.JSONDecodeError:
				parse_error = True

	visible_text = _trim_visible_text("".join(visible_parts))
	commands = _inject_control_tools_from_text(response, commands)
	commands = _inject_executable_tools_from_text(response, commands)
	return visible_text, commands, parse_error


def _collapse_linebreaks(text: str) -> str:
	"""Replace one or more line breaks with a single space for compact history context."""
	text = re.sub(r"\s*\n+\s*", " ", text)
	text = re.sub(r" {2,}", " ", text)
	return text.strip()


def _sanitize_history_value(value: Any) -> Any:
	"""Recursively sanitize history payload values before reusing them in prompts."""
	if isinstance(value, str):
		return _collapse_linebreaks(value)
	if isinstance(value, list):
		return [_sanitize_history_value(item) for item in value]
	if isinstance(value, dict):
		# Exclude 'raw' field from assistant responses to avoid backtick spam in prompt serialization
		sanitized = {}
		for key, val in value.items():
			if key == "raw":
				continue
			sanitized[key] = _sanitize_history_value(val)
		return sanitized
	return value


def _to_jsonl(records: list[dict[str, Any]]) -> str:
	"""Serialize records as compact JSONL for prompt-efficient context passing."""
	if not records:
		return ""
	return "\n".join(
		json.dumps(_sanitize_history_value(item), ensure_ascii=False, separators=(",", ":"), default=str)
		for item in records
	)


def build_session_follow_up_prompt(user_prompt: str, conversation_history: list[dict[str, Any]], force_close: bool = False) -> str:
	"""Build next-turn prompt using accumulated session history."""
	context_payload = _to_jsonl(conversation_history)
	header = FORCED_CLOSE_HEADER if force_close else "[SESSION_CONTINUE] Continue from this session context."
	return f"""{header}

Original user request:
{user_prompt}

Session conversation history:
{context_payload}

Instructions:
- Use the history exactly as provided.
- If tools are still needed, return one JSON block with tool commands.
- If you are done, provide final user-facing answer and include stop_session in the JSON block.
"""


def build_final_answer_prompt(user_prompt: str, conversation_history: list[dict[str, Any]], tool_trace: list[dict[str, Any]]) -> str:
	"""Force a final natural-language answer from the current session context."""
	context_payload = _to_jsonl(conversation_history)
	trace_payload = _to_jsonl(tool_trace)
	return f"""[FINAL_RESPONSE_REQUIRED]
The tool execution phase is complete. Respond to the user immediately.

Original user request:
{user_prompt}

Session conversation history:
{context_payload}

Tool trace:
{trace_payload}

Rules:
- Output only natural language.
- Do not output JSON.
- Do not call any tools.
- Give the final answer to the user now.
"""


async def execute_tool(tool_name: str, parameters: dict, base_url: str) -> Any:
	"""Execute the specified tool with given parameters."""
	_terminal_log("Tool execution start", {"tool": tool_name, "parameters": parameters})
	try:
		async with httpx.AsyncClient(timeout=30.0) as client:
			if tool_name == "save_memory":
				content = parameters.get("content", "").strip()
				if not content:
					return {"error": "Content parameter is required for save_memory"}
				return {"success": True, "message": _save_memory(content)}
			
			elif tool_name == "get_gmail":
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
				result = {"error": f"Unknown tool: {tool_name}"}
				_terminal_log("Tool execution result", {"tool": tool_name, "result": result})
				return result
	
	except Exception as e:
		error_result = {"error": f"Tool execution failed: {str(e)}"}
		_terminal_log("Tool execution error", {"tool": tool_name, "result": error_result})
		return error_result


@api.post("/gemini_chat")
async def gemini_chat(request: Request):
	"""Handle chat responses with session-based tool orchestration."""
	data = await request.json()
	user_prompt = (data.get("prompt") or "").strip()
	user_system_prompt = data.get("system_prompt")
	_terminal_log("Incoming /gemini_chat request", {"prompt": user_prompt, "has_system_prompt": bool(user_system_prompt)})

	if not user_prompt:
		return {"reply": "Please provide a prompt."}

	tool_system_prompt = build_tool_system_prompt()
	combined_system_prompt = f"{user_system_prompt}\n\n{tool_system_prompt}" if user_system_prompt else tool_system_prompt
	gemini_ai = _create_llm_client(system_prompt=combined_system_prompt)

	base_url = str(request.base_url).rstrip("/")
	conversation_history: list[dict[str, Any]] = []
	progress_messages: list[str] = []
	tool_trace: list[dict[str, Any]] = []
	session_active = False
	session_incomplete = False
	final_reply = ""
	last_visible_text = ""
	last_tool_signature = ""

	started_at = time.monotonic()
	pending_prompt = user_prompt

	for turn in range(1, MAX_SESSION_TURNS + 1):
		if time.monotonic() - started_at > ORCHESTRATION_TIMEOUT_SECONDS:
			_terminal_log("Session guard triggered: timeout", {"turn": turn})
			break

		if turn == 1:
			conversation_history.append({"type": "user_prompt", "turn": turn, "content": user_prompt})
		else:
			conversation_history.append({
				"type": "orchestration_turn",
				"turn": turn,
				"content": "[SESSION_CONTINUE_PROMPT_SENT]"
			})
		_terminal_log("LLM request", {"turn": turn, "prompt": pending_prompt})
		response = gemini_ai.get_response(pending_prompt)
		_terminal_log("LLM raw response", {"turn": turn, "response": response})
		visible_text, commands, parse_error = parse_llm_response(response)
		_terminal_log("LLM parsed response", {"turn": turn, "visible_text": visible_text, "commands": commands, "parse_error": parse_error})

		conversation_history.append({
			"type": "assistant_response",
			"turn": turn,
			"raw": response,
			"visible_text": visible_text,
			"commands": commands
		})

		if visible_text:
			progress_messages.append(visible_text)
			last_visible_text = visible_text

		if parse_error and not commands:
			_terminal_log("Parse error without commands; ending turn loop", {"turn": turn})
			break

		if not commands:
			if not session_active:
				_terminal_log("No commands and no active session; ending loop", {"turn": turn})
				break
			pending_prompt = build_session_follow_up_prompt(user_prompt, conversation_history)
			continue

		conversation_history.append({"type": "tool_call", "turn": turn, "commands": commands})

		start_called = any(cmd.get("tool") in CONTROL_START_TOOLS for cmd in commands)
		stop_called = any(cmd.get("tool") in CONTROL_STOP_TOOLS for cmd in commands)

		executable_commands = [cmd for cmd in commands if cmd.get("tool") not in CONTROL_TOOLS]

		if start_called or executable_commands:
			# Auto-start if model forgot start_session but attempted executable tools.
			session_active = True
			if executable_commands and not start_called:
				conversation_history.append({
					"type": "session_auto_start",
					"turn": turn,
					"reason": "Executable tool call detected without explicit start_session"
				})

		if executable_commands:
			tool_signature = json.dumps(executable_commands, sort_keys=True)
			if tool_signature == last_tool_signature:
				_terminal_log("Repeated tool signature guard hit; ending loop", {"turn": turn, "signature": tool_signature})
				break
			last_tool_signature = tool_signature

		for cmd in executable_commands:
			tool_name = cmd.get("tool", "")
			parameters = cmd.get("parameters", {})
			tool_result = await execute_tool(tool_name, parameters, base_url)
			_terminal_log("Tool output", {"turn": turn, "tool": tool_name, "parameters": parameters, "result": tool_result})
			tool_trace.append({"tool": tool_name, "parameters": parameters, "result": tool_result})
			conversation_history.append({
				"type": "tool_result",
				"turn": turn,
				"tool": tool_name,
				"parameters": parameters,
				"result": tool_result
			})

		if stop_called:
			if visible_text:
				# stop_session indicates completion; prefer the assistant's visible final text.
				final_reply = visible_text
			elif tool_trace:
				finalize_prompt = build_final_answer_prompt(user_prompt, conversation_history, tool_trace)
				conversation_history.append({"type": "finalize_prompt", "turn": turn, "content": finalize_prompt})
				_terminal_log("Finalize prompt", {"turn": turn, "prompt": finalize_prompt})
				finalize_response = gemini_ai.get_response(finalize_prompt)
				_terminal_log("Finalize raw response", {"turn": turn, "response": finalize_response})
				final_text, _, _ = parse_llm_response(finalize_response)
				_terminal_log("Finalize parsed response", {"turn": turn, "final_text": final_text})
				if final_text:
					progress_messages.append(final_text)
					final_reply = final_text
			elif not final_reply:
				final_reply = "Session completed."

			session_active = False
			conversation_history.clear()
			final_payload = {
				"reply": final_reply or "Session completed. I finished the tool workflow but could not generate a final message.",
				"tool_trace": tool_trace,
				"session_closed": True,
				"session_incomplete": False
			}
			_terminal_log("/gemini_chat response payload", final_payload)
			return final_payload

		if session_active:
			pending_prompt = build_session_follow_up_prompt(user_prompt, conversation_history)
		else:
			break

	if session_active:
		force_prompt = build_session_follow_up_prompt(user_prompt, conversation_history, force_close=True)
		conversation_history.append({"type": "forced_close_prompt", "content": force_prompt})
		_terminal_log("Forced-close prompt", {"prompt": force_prompt})
		force_response = gemini_ai.get_response(force_prompt)
		_terminal_log("Forced-close raw response", {"response": force_response})
		visible_text, force_commands, _ = parse_llm_response(force_response)
		_terminal_log("Forced-close parsed response", {"visible_text": visible_text, "commands": force_commands})

		conversation_history.append({
			"type": "forced_close_response",
			"raw": force_response,
			"visible_text": visible_text,
			"commands": force_commands
		})

		if visible_text:
			progress_messages.append(visible_text)
			last_visible_text = visible_text

		stop_called = any(cmd.get("tool") in CONTROL_STOP_TOOLS for cmd in force_commands)
		if stop_called and visible_text and not tool_trace:
			final_reply = visible_text

		if not final_reply and tool_trace:
			fallback_prompt = build_final_answer_prompt(user_prompt, conversation_history, tool_trace)
			_terminal_log("Fallback final prompt", {"prompt": fallback_prompt})
			fallback_response = gemini_ai.get_response(fallback_prompt)
			_terminal_log("Fallback final raw response", {"response": fallback_response})
			fallback_text, _, _ = parse_llm_response(fallback_response)
			_terminal_log("Fallback final parsed response", {"final_text": fallback_text})
			if fallback_text:
				progress_messages.append(fallback_text)
				final_reply = fallback_text

		session_incomplete = not stop_called
		conversation_history.clear()
		final_payload = {
			"reply": final_reply or "I could not safely finish the session. Please try again.",
			"tool_trace": tool_trace,
			"session_closed": stop_called,
			"session_incomplete": session_incomplete
		}
		_terminal_log("/gemini_chat response payload", final_payload)
		return final_payload

	if not final_reply and tool_trace:
		finalize_prompt = build_final_answer_prompt(user_prompt, conversation_history, tool_trace)
		_terminal_log("Post-loop finalize prompt", {"prompt": finalize_prompt})
		finalize_response = gemini_ai.get_response(finalize_prompt)
		_terminal_log("Post-loop finalize raw response", {"response": finalize_response})
		final_text, _, _ = parse_llm_response(finalize_response)
		_terminal_log("Post-loop finalize parsed response", {"final_text": final_text})
		if final_text:
			progress_messages.append(final_text)
			final_reply = final_text

	conversation_history.clear()
	final_payload = {
		"reply": final_reply or last_visible_text or "(No reply)",
		"tool_trace": tool_trace,
		"session_closed": True,
		"session_incomplete": False
	}
	_terminal_log("/gemini_chat response payload", final_payload)
	return final_payload

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