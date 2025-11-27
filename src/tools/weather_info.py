"""
Weather Information Tool

This tool provides weather information using the Open-Meteo API (free, no API key required).
It can fetch current weather and forecasts for any location.

Requirements:
- pip install requests
"""

import sys
from pathlib import Path
from typing import Dict, Optional, Tuple
import requests
from datetime import datetime


class WeatherFetcher:
    """
    Fetches weather information using Open-Meteo API.
    """
    
    # Open-Meteo API endpoints (free, no API key needed)
    GEOCODING_URL = "https://geocoding-api.open-meteo.com/v1/search"
    WEATHER_URL = "https://api.open-meteo.com/v1/forecast"
    
    def __init__(self):
        """Initialize weather fetcher."""
        self.session = requests.Session()
    
    def geocode_location(self, location: str) -> Optional[Tuple[float, float, str]]:
        """
        Convert location name to coordinates.
        
        Args:
            location: City name or location string
        
        Returns:
            Tuple of (latitude, longitude, full_name) or None if not found
        """
        try:
            params = {
                'name': location,
                'count': 1,
                'language': 'en',
                'format': 'json'
            }
            
            response = self.session.get(self.GEOCODING_URL, params=params, timeout=10)
            response.raise_for_status()
            data = response.json()
            
            if 'results' in data and len(data['results']) > 0:
                result = data['results'][0]
                lat = result['latitude']
                lon = result['longitude']
                name = result['name']
                
                # Build full name with country
                full_name = name
                if 'admin1' in result and result['admin1']:
                    full_name += f", {result['admin1']}"
                if 'country' in result:
                    full_name += f", {result['country']}"
                
                return (lat, lon, full_name)
            
            return None
        
        except Exception as e:
            print(f"Geocoding error: {e}")
            return None
    
    def get_weather(
        self, 
        latitude: float, 
        longitude: float,
        forecast_days: int = 1
    ) -> Optional[Dict]:
        """
        Get weather information for coordinates.
        
        Args:
            latitude: Latitude
            longitude: Longitude
            forecast_days: Number of forecast days (1-16)
        
        Returns:
            Dict with weather information or None if error
        """
        try:
            params = {
                'latitude': latitude,
                'longitude': longitude,
                'current': 'temperature_2m,relative_humidity_2m,apparent_temperature,precipitation,weather_code,wind_speed_10m',
                'daily': 'temperature_2m_max,temperature_2m_min,precipitation_sum,weather_code',
                'timezone': 'auto',
                'forecast_days': forecast_days
            }
            
            response = self.session.get(self.WEATHER_URL, params=params, timeout=10)
            response.raise_for_status()
            data = response.json()
            
            return data
        
        except Exception as e:
            print(f"Weather fetch error: {e}")
            return None
    
    def get_weather_by_location(
        self, 
        location: str,
        forecast_days: int = 1
    ) -> Optional[Dict]:
        """
        Get weather for a location by name.
        
        Args:
            location: City name or location string
            forecast_days: Number of forecast days
        
        Returns:
            Dict with weather data and location info
        """
        # Geocode location
        geo_result = self.geocode_location(location)
        
        if not geo_result:
            return {
                'error': f"Location '{location}' not found"
            }
        
        lat, lon, full_name = geo_result
        
        # Get weather
        weather_data = self.get_weather(lat, lon, forecast_days)
        
        if not weather_data:
            return {
                'error': f"Could not fetch weather for {full_name}"
            }
        
        # Add location info
        weather_data['location'] = full_name
        weather_data['coordinates'] = {'latitude': lat, 'longitude': lon}
        
        return weather_data
    
    @staticmethod
    def interpret_weather_code(code: int) -> str:
        """
        Interpret WMO weather code.
        
        Args:
            code: WMO weather code
        
        Returns:
            Human-readable weather description
        """
        weather_codes = {
            0: "Clear sky",
            1: "Mainly clear",
            2: "Partly cloudy",
            3: "Overcast",
            45: "Foggy",
            48: "Depositing rime fog",
            51: "Light drizzle",
            53: "Moderate drizzle",
            55: "Dense drizzle",
            61: "Slight rain",
            63: "Moderate rain",
            65: "Heavy rain",
            71: "Slight snow",
            73: "Moderate snow",
            75: "Heavy snow",
            77: "Snow grains",
            80: "Slight rain showers",
            81: "Moderate rain showers",
            82: "Violent rain showers",
            85: "Slight snow showers",
            86: "Heavy snow showers",
            95: "Thunderstorm",
            96: "Thunderstorm with slight hail",
            99: "Thunderstorm with heavy hail"
        }
        
        return weather_codes.get(code, f"Unknown ({code})")
    
    def format_current_weather(self, weather_data: Dict) -> str:
        """
        Format current weather into readable string.
        
        Args:
            weather_data: Weather data dict from API
        
        Returns:
            Formatted weather string
        """
        if 'error' in weather_data:
            return weather_data['error']
        
        location = weather_data.get('location', 'Unknown location')
        current = weather_data.get('current', {})
        
        temp = current.get('temperature_2m', 'N/A')
        feels_like = current.get('apparent_temperature', 'N/A')
        humidity = current.get('relative_humidity_2m', 'N/A')
        precipitation = current.get('precipitation', 0)
        wind_speed = current.get('wind_speed_10m', 'N/A')
        weather_code = current.get('weather_code', 0)
        
        condition = self.interpret_weather_code(weather_code)
        
        output = f"Weather in {location}:\n"
        output += f"  Condition: {condition}\n"
        output += f"  Temperature: {temp}°C (feels like {feels_like}°C)\n"
        output += f"  Humidity: {humidity}%\n"
        output += f"  Wind Speed: {wind_speed} km/h\n"
        
        if precipitation > 0:
            output += f"  Precipitation: {precipitation} mm\n"
        
        return output
    
    def format_forecast(self, weather_data: Dict, days: int = 3) -> str:
        """
        Format weather forecast into readable string.
        
        Args:
            weather_data: Weather data dict from API
            days: Number of days to include
        
        Returns:
            Formatted forecast string
        """
        if 'error' in weather_data:
            return weather_data['error']
        
        location = weather_data.get('location', 'Unknown location')
        daily = weather_data.get('daily', {})
        
        output = f"Weather forecast for {location}:\n\n"
        
        dates = daily.get('time', [])
        max_temps = daily.get('temperature_2m_max', [])
        min_temps = daily.get('temperature_2m_min', [])
        precip = daily.get('precipitation_sum', [])
        weather_codes = daily.get('weather_code', [])
        
        for i in range(min(days, len(dates))):
            date_str = dates[i]
            date_obj = datetime.fromisoformat(date_str)
            day_name = date_obj.strftime('%A, %B %d')
            
            condition = self.interpret_weather_code(weather_codes[i]) if i < len(weather_codes) else 'N/A'
            max_temp = max_temps[i] if i < len(max_temps) else 'N/A'
            min_temp = min_temps[i] if i < len(min_temps) else 'N/A'
            precipitation = precip[i] if i < len(precip) else 0
            
            output += f"{day_name}:\n"
            output += f"  {condition}\n"
            output += f"  High: {max_temp}°C, Low: {min_temp}°C\n"
            
            if precipitation > 0:
                output += f"  Precipitation: {precipitation} mm\n"
            
            output += "\n"
        
        return output


def get_current_weather(location: str) -> str:
    """
    Simple function to get current weather for a location.
    
    Args:
        location: City name or location string
    
    Returns:
        Formatted current weather string
    """
    fetcher = WeatherFetcher()
    weather_data = fetcher.get_weather_by_location(location, forecast_days=1)
    if weather_data is None:
        return f"Could not fetch weather for {location}"
    return fetcher.format_current_weather(weather_data)


def get_weather_forecast(location: str, days: int = 3) -> str:
    """
    Simple function to get weather forecast for a location.
    
    Args:
        location: City name or location string
        days: Number of forecast days (1-7)
    
    Returns:
        Formatted weather forecast string
    """
    fetcher = WeatherFetcher()
    weather_data = fetcher.get_weather_by_location(location, forecast_days=max(1, min(days, 7)))
    
    if weather_data is None:
        return f"Could not fetch weather forecast for {location}"
    
    # Include current weather + forecast
    current = fetcher.format_current_weather(weather_data)
    forecast = fetcher.format_forecast(weather_data, days)
    
    return f"{current}\n\n{forecast}"


# Example usage for testing
if __name__ == "__main__":
    print("=" * 60)
    print("Weather Information Tool - Test")
    print("=" * 60)
    
    fetcher = WeatherFetcher()
    
    # Test current weather
    test_location = "Sydney"
    print(f"\nFetching current weather for: {test_location}")
    print(get_current_weather(test_location))
    
    # Test forecast
    print("\n" + "=" * 60)
    print(f"\nFetching 3-day forecast for: {test_location}")
    print(get_weather_forecast(test_location, days=3))
