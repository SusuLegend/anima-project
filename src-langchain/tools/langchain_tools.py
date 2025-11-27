"""
LangChain Tools Integration

Wraps existing tools (web search, weather, notifications) into LangChain Tool format.
These tools can be used by LangChain agents for automatic tool selection and execution.

Available Tools:
- web_search: Search the internet using DuckDuckGo
- weather: Get current weather for any location
- notifications: Read email and system notifications
"""

import sys
from pathlib import Path
from typing import List, Dict, Any, Optional

# Add src directory to path to import existing tools
src_path = Path(__file__).parent.parent.parent / "src"
sys.path.insert(0, str(src_path))

from langchain.tools import Tool, StructuredTool
from langchain.pydantic_v1 import BaseModel, Field


# ============= Import Existing Tools =============

try:
    from tools.web_search import web_search, quick_search
    WEB_SEARCH_AVAILABLE = True
except ImportError as e:
    WEB_SEARCH_AVAILABLE = False
    print(f"Warning: web_search not available: {e}")

try:
    from tools.weather_info import get_current_weather, get_weather_forecast
    WEATHER_AVAILABLE = True
except ImportError as e:
    WEATHER_AVAILABLE = False
    print(f"Warning: weather_info not available: {e}")

try:
    from tools.read_notifications import read_notifications
    NOTIFICATIONS_AVAILABLE = True
except ImportError as e:
    NOTIFICATIONS_AVAILABLE = False
    print(f"Warning: read_notifications not available: {e}")


# ============= Input Schemas for Structured Tools =============

class WebSearchInput(BaseModel):
    """Input schema for web search tool"""
    query: str = Field(..., description="The search query string")
    max_results: int = Field(default=5, description="Maximum number of results to return")


class WeatherInput(BaseModel):
    """Input schema for weather tool"""
    location: str = Field(..., description="City name or location (e.g., 'Tokyo', 'New York')")


class WeatherForecastInput(BaseModel):
    """Input schema for weather forecast tool"""
    location: str = Field(..., description="City name or location")
    days: int = Field(default=3, description="Number of days to forecast (1-7)")


# ============= Tool Wrapper Functions =============

def search_web(query: str, max_results: int = 5) -> str:
    """
    Search the internet for information.
    
    Args:
        query: Search query string
        max_results: Maximum number of results
    
    Returns:
        Formatted search results
    """
    if not WEB_SEARCH_AVAILABLE:
        return "Web search tool is not available. Please install required dependencies."
    
    try:
        return web_search(query, max_results)
    except Exception as e:
        return f"Error performing web search: {str(e)}"


def get_weather(location: str) -> str:
    """
    Get current weather information for a location.
    
    Args:
        location: City name or location
    
    Returns:
        Current weather information
    """
    if not WEATHER_AVAILABLE:
        return "Weather tool is not available. Please install required dependencies."
    
    try:
        return get_current_weather(location)
    except Exception as e:
        return f"Error fetching weather: {str(e)}"


def get_forecast(location: str, days: int = 3) -> str:
    """
    Get weather forecast for a location.
    
    Args:
        location: City name or location
        days: Number of days to forecast
    
    Returns:
        Weather forecast information
    """
    if not WEATHER_AVAILABLE:
        return "Weather tool is not available. Please install required dependencies."
    
    try:
        return get_weather_forecast(location, days)
    except Exception as e:
        return f"Error fetching forecast: {str(e)}"


def check_notifications() -> str:
    """
    Check for new notifications (email and system).
    
    Returns:
        Summary of all notifications
    """
    if not NOTIFICATIONS_AVAILABLE:
        return "Notification tool is not available. Please install required dependencies."
    
    try:
        return read_notifications()
    except Exception as e:
        return f"Error checking notifications: {str(e)}"


# ============= LangChain Tool Definitions =============

def create_web_search_tool() -> Tool:
    """Create web search tool for LangChain"""
    return Tool(
        name="web_search",
        func=lambda query: search_web(query, max_results=5),
        description=(
            "Search the internet for information using DuckDuckGo. "
            "Useful for finding current information, news, facts, or any topic that requires web search. "
            "Input should be a search query string. "
            "Returns formatted search results with titles, links, and snippets."
        )
    )


def create_web_search_structured_tool() -> StructuredTool:
    """Create structured web search tool with arguments"""
    return StructuredTool.from_function(
        func=search_web,
        name="web_search",
        description=(
            "Search the internet for information using DuckDuckGo. "
            "Useful for finding current information, news, facts, or any topic."
        ),
        args_schema=WebSearchInput
    )


def create_weather_tool() -> Tool:
    """Create weather information tool for LangChain"""
    return Tool(
        name="weather",
        func=get_weather,
        description=(
            "Get current weather information for any location. "
            "Input should be a city name or location (e.g., 'Tokyo', 'New York', 'London'). "
            "Returns current temperature, conditions, humidity, wind speed, and precipitation."
        )
    )


def create_weather_structured_tool() -> StructuredTool:
    """Create structured weather tool"""
    return StructuredTool.from_function(
        func=get_weather,
        name="weather",
        description="Get current weather information for any location worldwide.",
        args_schema=WeatherInput
    )


def create_forecast_tool() -> StructuredTool:
    """Create weather forecast tool"""
    return StructuredTool.from_function(
        func=get_forecast,
        name="weather_forecast",
        description=(
            "Get weather forecast for a location for multiple days. "
            "Useful when user asks about future weather conditions."
        ),
        args_schema=WeatherForecastInput
    )


def create_notifications_tool() -> Tool:
    """Create notifications checking tool for LangChain"""
    return Tool(
        name="notifications",
        func=check_notifications,
        description=(
            "Check for new notifications including emails and system notifications. "
            "No input required. "
            "Returns a summary of unread emails and recent system notifications (Windows/macOS). "
            "Useful when user asks about messages, emails, or notifications."
        )
    )


# ============= Tool Collections =============

def get_all_tools(structured: bool = False) -> List[Tool]:
    """
    Get all available tools.
    
    Args:
        structured: If True, return StructuredTools with argument schemas
    
    Returns:
        List of LangChain Tool objects
    """
    tools = []
    
    if WEB_SEARCH_AVAILABLE:
        if structured:
            tools.append(create_web_search_structured_tool())
        else:
            tools.append(create_web_search_tool())
    
    if WEATHER_AVAILABLE:
        if structured:
            tools.append(create_weather_structured_tool())
            tools.append(create_forecast_tool())
        else:
            tools.append(create_weather_tool())
    
    if NOTIFICATIONS_AVAILABLE:
        tools.append(create_notifications_tool())
    
    return tools


def get_tool_names() -> List[str]:
    """Get list of available tool names"""
    tools = get_all_tools()
    return [tool.name for tool in tools]


def get_tool_by_name(name: str) -> Optional[Tool]:
    """
    Get a specific tool by name.
    
    Args:
        name: Tool name
    
    Returns:
        Tool object or None if not found
    """
    tools = get_all_tools()
    for tool in tools:
        if tool.name == name:
            return tool
    return None


# ============= Tool Information =============

def print_tool_info():
    """Print information about all available tools"""
    tools = get_all_tools()
    
    print("=" * 60)
    print(f"Available Tools: {len(tools)}")
    print("=" * 60)
    
    for i, tool in enumerate(tools, 1):
        print(f"\n{i}. {tool.name}")
        print(f"   Description: {tool.description}")
        print(f"   Available: ✅")
    
    # Print unavailable tools
    unavailable = []
    if not WEB_SEARCH_AVAILABLE:
        unavailable.append("web_search")
    if not WEATHER_AVAILABLE:
        unavailable.append("weather")
    if not NOTIFICATIONS_AVAILABLE:
        unavailable.append("notifications")
    
    if unavailable:
        print("\n" + "=" * 60)
        print("Unavailable Tools:")
        print("=" * 60)
        for tool_name in unavailable:
            print(f"  ❌ {tool_name}")


# Example usage and testing
if __name__ == "__main__":
    print_tool_info()
    
    # Test each tool
    print("\n" + "=" * 60)
    print("Testing Tools")
    print("=" * 60)
    
    tools = get_all_tools()
    
    for tool in tools:
        print(f"\n📌 Testing: {tool.name}")
        try:
            if tool.name == "web_search":
                result = tool.run("Python programming language")
                print(result[:200] + "..." if len(result) > 200 else result)
            
            elif tool.name == "weather":
                result = tool.run("Tokyo")
                print(result)
            
            elif tool.name == "notifications":
                result = tool.run("")
                print(result[:200] + "..." if len(result) > 200 else result)
            
        except Exception as e:
            print(f"❌ Error: {e}")
