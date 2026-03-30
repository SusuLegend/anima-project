from typing import Callable, Dict, Any

class LLMToolRegistry:
    def __init__(self):
        self.tools: Dict[str, Callable] = {}
        self.schema: list[Dict[str, Any]] = []

    def register(self, name: str, description: str, parameters: dict):
        """Decorator to register a function as an LLM callable tool."""
        def wrapper(func: Callable):
            self.tools[name] = func
            self.schema.append({
                "name": name,
                "description": description,
                "parameters": parameters
            })
            return func
        return wrapper

    def get_schema(self) -> list[Dict[str, Any]]:
        return self.schema

    def call(self, name: str, args: dict):
        if name not in self.tools:
            raise Exception(f"Tool '{name}' not registered.")
        return self.tools[name](**args)

llm_tools = LLMToolRegistry()

llm_tools.schema.append({
    "name": "start_session",
    "description": "Start a tool-calling session. Use before running one or more tools for multi-step retrieval.",
    "parameters": {}
})

llm_tools.schema.append({
    "name": "stop_session",
    "description": "End the active tool-calling session after finalizing the user-facing answer.",
    "parameters": {}
})

llm_tools.schema.append({
    "name": "session_stop",
    "description": "Alias of stop_session. End the active tool-calling session after finalizing the user-facing answer.",
    "parameters": {}
})

llm_tools.schema.append({
    "name": "get_gmail",
    "description": (
        "Retrieve your most recent Gmail messages, including both read and unread emails. "
        "Use this tool to check for new, recent, or unread emails, updates, notifications, or messages in your Gmail account. "
        "Use this tool when asked for anything about emails, or gmail."
    ),
    "parameters": {}
})
llm_tools.schema.append({
    "name": "get_outlook",
    "description": "Fetch unread emails from your Outlook inbox. Use this tool to check for new messages in your Outlook account. Use this tool when asked for anything about emails, or outlook",
    "parameters": {}
})
llm_tools.schema.append({
    "name": "get_tasks",
    "description": "Retrieve your Microsoft To Do tasks. Use this tool to list your pending or completed tasks from your Microsoft account. Use this tool when asked for tasks.",
    "parameters": {}
})
llm_tools.schema.append({
    "name": "get_calendar_events",
    "description": "Fetch upcoming events from your Microsoft Outlook calendar. Use this tool to see your scheduled meetings and events. Use this tool when asked about events",
    "parameters": {}
})
llm_tools.schema.append({
    "name": "get_whatsapp_messages",
    "description": ("Retrieve unread WhatsApp messages. Returns only new messages that have not been read yet, including sender and content. Use this tool to check for new WhatsApp notifications"
                    "When creating an answer, always refer by name directly (<group chat name> said <topic>, or <user name> mentioned <activity>)"),
    "parameters": {}
})

llm_tools.schema.append({
    "name": "search",
    "description": "Search the internet for information on a given query. It is recommended to use 3 for max results and formatted results.",
    "parameters": {
        "type": "object",
        "properties": {
            "query": {"type": "string", "description": "The search query to look up on the internet."},
            "max_results": {"type": "integer", "description": "Maximum number of search results to return.", "default": 3},
            "formatted": {"type": "boolean", "description": "Whether to return formatted output.", "default": True}
        },
        "required": ["query"]
    }
})

llm_tools.schema.append({
    "name": "get_weather_info",
    "description": "Get weather information for a specified city.",
    "parameters": {
        "type": "object",
        "properties": {
            "city": {"type": "string", "description": "Name of the city."},
            "days": {"type": "integer", "description": "Number of days for forecast.", "default": 1},
            "formatted": {"type": "boolean", "description": "Whether to return formatted output.", "default": False}
        },
        "required": ["city"]
    }
})