from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
import importlib
from pathlib import Path

app = FastAPI()

# Gmail API endpoint
@app.get("/gmail")
def get_gmail():
	try:
		gmail_api = importlib.import_module("src.tools.google_listener.gmail_api")
		return gmail_api.get_gmail_data()  # You must implement get_gmail_data in gmail_api.py
	except Exception as e:
		raise HTTPException(status_code=500, detail=str(e))


# New Outlook endpoint THIS ONLY WORKING ONE
@app.get("/get_outlook")
def get_outlook():
	try:
		api_fetch = importlib.import_module("src.tools.microsoft_listener.api_fetch")
		return api_fetch.get_new_emails()
	except Exception as e:
		raise HTTPException(status_code=500, detail=str(e))
	
# Weather info endpoint
@app.get("/weather")
def get_weather():
	try:
		weather_info = importlib.import_module("src.tools.other_listener.weather_info")
		return weather_info.get_weather_data()  # You must implement get_weather_data in weather_info.py
	except Exception as e:
		raise HTTPException(status_code=500, detail=str(e))

# WhatsApp endpoint
@app.get("/whatsapp")
def get_whatsapp():
	try:
		import subprocess
		import json
		import os
		import sys
		
		# Path to index.js
		js_path = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "whatsapp_listener", "index.js"))
		
		# Configure subprocess to run without showing console window
		startupinfo = None
		if sys.platform == "win32":
			startupinfo = subprocess.STARTUPINFO()
			startupinfo.dwFlags |= subprocess.STARTF_USESHOWWINDOW
			startupinfo.wShowWindow = subprocess.SW_HIDE
		
		_path = js_path.replace('\\', '/')
		# Run Node.js and call getAllUnreadMessages, print result as JSON
		result = subprocess.run([
			"node",
			"-e",
			f"(async () => {{ const m = require('{_path}'); const res = await m.getAllUnreadMessages(); console.log(JSON.stringify(res)); }})()" \
			], 
		capture_output=True, 
		text=True,
		startupinfo=startupinfo,
		creationflags=subprocess.CREATE_NO_WINDOW if sys.platform == "win32" else 0
		)
		
		if result.returncode != 0:
			raise Exception(result.stderr)
		data = json.loads(result.stdout)
		return data
	except Exception as e:
		raise HTTPException(status_code=500, detail=str(e))

# Root endpoint
@app.get("/")
def root():
	return {"message": "Unified Tools API is running."}
