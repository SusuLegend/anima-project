from typing import Callable, Dict, Any

class LLMToolRegistry:
    def __init__(self):
        self.tools: Dict[str, Callable] = {}
        self.schema: Dict[str, Any] = []

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

    def get_schema(self):
        return self.schema

    def call(self, name: str, args: dict):
        if name not in self.tools:
            raise Exception(f"Tool '{name}' not registered.")
        return self.tools[name](**args)

llm_tools = LLMToolRegistry()

llm_tools.schema.append({
    "name": "get_gmail",
    "description": "Get Gmail messages using the MCP server.",
    "parameters": {}
})
llm_tools.schema.append({
    "name": "get_outlook",
    "description": "Get Outlook unread emails using the MCP server.",
    "parameters": {}
})
llm_tools.schema.append({
    "name": "get_tasks",
    "description": "Get Microsoft tasks using the MCP server.",
    "parameters": {}
})
llm_tools.schema.append({
    "name": "get_calendar_events",
    "description": "Get Microsoft calendar events using the MCP server.",
    "parameters": {}
})
llm_tools.schema.append({
    "name": "get_whatsapp_messages",
    "description": "Get WhatsApp unread messages using the MCP server.",
    "parameters": {}
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
