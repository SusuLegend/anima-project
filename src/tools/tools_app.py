from fastapi import FastAPI, HTTPException
from fastapi import BackgroundTasks
from contextlib import asynccontextmanager
from pydantic import BaseModel
import importlib
from pathlib import Path
import sys
import subprocess
import json
import os
import asyncio
import time
import logging

# Choosing a non-standard port to minimize chance of port collision
# Setup project root path - go up to the project root (anima-capstone)
PROJECT_ROOT = Path(__file__).parent.parent.parent.resolve()
if str(PROJECT_ROOT) not in sys.path:
	sys.path.insert(0, str(PROJECT_ROOT))

# Configure logging (after PROJECT_ROOT defined)
logger = logging.getLogger("tools_app")
if not logger.handlers:
	logger.setLevel(logging.INFO)
	log_path = PROJECT_ROOT / "src" / "tools" / "whatsapp_listener" / "whatsapp_listener.log"
	try:
		log_path.parent.mkdir(parents=True, exist_ok=True)
	except Exception:
		pass
	fh = logging.FileHandler(log_path, encoding="utf-8")
	fmt = logging.Formatter('%(asctime)s [%(levelname)s] %(message)s')
	fh.setFormatter(fmt)
	logger.addHandler(fh)
	sh = logging.StreamHandler(sys.stdout)
	sh.setFormatter(fmt)
	logger.addHandler(sh)

# Global handle for background Node WhatsApp listener
WHATSAPP_PROC = None

def start_whatsapp_listener():
	"""Start the persistent Node.js WhatsApp listener if not already running."""
	global WHATSAPP_PROC
	if WHATSAPP_PROC and WHATSAPP_PROC.poll() is None:
		return  # already running
	listener_dir = PROJECT_ROOT / "src" / "tools" / "whatsapp_listener"
	entry = listener_dir / "index.js"
	if not entry.exists():
		print(f"[whatsapp] index.js not found at {entry}")
		return
	creationflags = 0
	startupinfo = None
	if sys.platform == "win32":
		startupinfo = subprocess.STARTUPINFO()
		startupinfo.dwFlags |= subprocess.STARTF_USESHOWWINDOW
		startupinfo.wShowWindow = subprocess.SW_HIDE
		creationflags = subprocess.CREATE_NO_WINDOW
	try:
		# Convert Windows path to file:// URL for ESM import
		from pathlib import Path
		file_url = entry.as_uri()  # Converts to file:///E:/anima-capstone/...
		node_cmd = [
			"node",
			"--input-type=module",
			"-e",
			f"import('{file_url}').then(m=>m.startWhatsAppListener()).catch(e=>console.error(e))"
		]
		# Capture output to log file for debugging
		node_log = listener_dir / "node_output.log"
		log_file = open(node_log, "a", encoding="utf-8")
		WHATSAPP_PROC = subprocess.Popen(
			node_cmd,
			cwd=str(listener_dir),
			stdout=log_file,
			stderr=subprocess.STDOUT,
			startupinfo=startupinfo,
			creationflags=creationflags
		)
		logger.info(f"[whatsapp] listener started pid={WHATSAPP_PROC.pid}, log: {node_log}")
	except Exception as e:
			logger.error(f"[whatsapp] failed to start listener: {e}")

def stop_whatsapp_listener():
	"""Terminate the Node.js WhatsApp listener if running."""
	global WHATSAPP_PROC
	if WHATSAPP_PROC and WHATSAPP_PROC.poll() is None:
		try:
			WHATSAPP_PROC.terminate()
			WHATSAPP_PROC.wait(timeout=5)
			logger.info("[whatsapp] listener terminated")
		except Exception as e:
			logger.error(f"[whatsapp] error terminating listener: {e}")
	WHATSAPP_PROC = None

RESTART_COUNT = 0

async def _heartbeat_task():
	global RESTART_COUNT
	while True:
		await asyncio.sleep(30)
		# poll() returns None if process is still running, non-None exit code if terminated
		alive = WHATSAPP_PROC is not None and WHATSAPP_PROC.poll() is None
		if alive:
			pid = WHATSAPP_PROC.pid if WHATSAPP_PROC else None
			logger.info(f"[whatsapp] heartbeat ok pid={pid}")
		else:
			logger.warning("[whatsapp] process not running, attempting restart")
			start_whatsapp_listener()
			# Check again after restart attempt
			if WHATSAPP_PROC is not None and WHATSAPP_PROC.poll() is None:
				RESTART_COUNT += 1
				logger.info(f"[whatsapp] restart successful (count={RESTART_COUNT})")

@asynccontextmanager
async def lifespan(app: FastAPI):
	start_whatsapp_listener()
	heartbeat = asyncio.create_task(_heartbeat_task())
	try:
		yield
	finally:
		heartbeat.cancel()
		stop_whatsapp_listener()

app = FastAPI(lifespan=lifespan)

# New Outlook endpoint - returns emails, events, and tasks
@app.get("/outlook")
def get_outlook():
	"""Aggregate Microsoft 365 data.

	Returns a JSON payload combining:
	- emails: recent unread messages from Inbox (deduped across calls)
	- events: newly seen calendar events
	- reminders: time-based reminders (1 day, 1 hour, 15 minutes before)
	- tasks: current pending tasks (excludes completed)
	- new_tasks: tasks first seen in this session

	Notes:
	- Uses OAuth via the `login` helper and Microsoft Graph.
	- Each call may return empty lists if nothing new or if Graph is unreachable.

	Examples:
	- http://127.0.0.1:8576/get_outlook
	"""
	'''
	
	'''
	try:
		api_fetch = importlib.import_module("src.tools.microsoft_listener.api_fetch")
		emails = api_fetch.get_new_emails()
		events_data = api_fetch.get_upcoming_events()
		tasks_data = api_fetch.get_pending_tasks()
		return {
			"status": "success",
			"emails": emails,
			"events": events_data.get("events", []),
			"reminders": events_data.get("reminders", []),
			"tasks": tasks_data.get("tasks", []),
			"new_tasks": tasks_data.get("new_tasks", [])
		}
	except Exception as e:
		raise HTTPException(status_code=500, detail=str(e))
	
# Weather info endpoint - requires city, optional days & formatted
@app.get("/weather")
def get_weather(city: str, days: int = 1, formatted: bool = False):
	"""Fetch weather for a city using Open‑Meteo.

	Query params:
	- city: required city name (e.g., "Sydney", "New York")
	- days: optional forecast length (1–7, clamped)
	- formatted: when true, returns a human‑readable summary string; otherwise returns structured JSON.

	Behavior:
	- Geocodes the city, then fetches current + daily forecast.
	- On error (city not found or network issues), returns HTTP 404/500.

	Examples:
	- JSON:      http://127.0.0.1:8576/weather?city=Sydney&days=3
	- Formatted: http://127.0.0.1:8576/weather?city=New%20York&days=2&formatted=true
	"""
	'''
	
	'''
	try:
		weather_info = importlib.import_module("src.tools.other_listener.weather_info")
		# Clamp days between 1 and 7 for reasonable responses
		days = max(1, min(days, 7))
		if formatted:
			# Return a readable string combining current + forecast
			text = weather_info.get_weather_forecast(city, days=days)
			return {"city": city, "days": days, "formatted": True, "text": text}
		else:
			# Return structured JSON using WeatherFetcher
			fetcher = weather_info.WeatherFetcher()
			data = fetcher.get_weather_by_location(city, forecast_days=days)
			if isinstance(data, dict) and data.get("error"):
				raise HTTPException(status_code=404, detail=data["error"])
			return data
	except HTTPException:
		raise
	except Exception as e:
		raise HTTPException(status_code=500, detail=str(e))

# Web search endpoint
@app.get("/search")
def search(query: str, max_results: int = 5, formatted: bool = False, region: str = "wt-wt"):
	"""DuckDuckGo web search.

	Query params:
	- query: required search text
	- max_results: 1–20, clamped
	- region: locale bias (e.g., "us-en", "au-en", "wt-wt")
	- formatted: when true, returns formatted text; otherwise returns list of results.

	Returns:
	- formatted: { text }
	- json: { results: [{ title, link, snippet }] }

	Examples:
	- JSON:      http://127.0.0.1:8576/search?query=best%20coffee&max_results=5&region=au-en
	- Formatted: http://127.0.0.1:8576/search?query=fastapi%20tutorial&formatted=true&region=us-en
	"""
	'''
	
	'''
	try:
		web_search_mod = importlib.import_module("src.tools.other_listener.web_search")
		max_results = max(1, min(max_results, 20))
		# basic region sanity: ddg expects patterns like 'us-en', 'au-en', 'wt-wt'
		region = (region or "wt-wt").strip()
		if formatted:
			# Use helper with region support
			text = web_search_mod.web_search(query, max_results=max_results, region=region)
			return {"query": query, "formatted": True, "text": text}
		else:
			searcher = web_search_mod.WebSearcher()
			results = searcher.search(query, max_results=max_results, region=region)
			return {"query": query, "results": results}
	except Exception as e:
		raise HTTPException(status_code=500, detail=str(e))

@app.get("/whatsapp")
def get_whatsapp():
	"""Return collected WhatsApp messages from the persistent Node listener.

	Behavior:
	- Ensures the background Node process is running (auto‑restart if down).
	- Reads `messages.json` written by the listener and returns messages with count.
	- If no messages yet or file missing, returns an empty list and status note.

	Examples:
	- http://127.0.0.1:8576/whatsapp
	"""
	try:
		# Ensure listener running (auto-restart if crashed)
		start_whatsapp_listener()
		messages_file = PROJECT_ROOT / "src" / "tools" / "whatsapp_listener" / "messages.json"
		if not messages_file.exists():
			return {"messages": [], "count": 0, "status": "listener starting or no messages yet"}
		try:
			with messages_file.open("r", encoding="utf-8") as f:
				data = json.load(f)
			if isinstance(data, list):
				return {"messages": data, "count": len(data)}
			elif isinstance(data, dict) and "messages" in data:
				msgs = data.get("messages", [])
				return {"messages": msgs, "count": len(msgs)}
			else:
				return {"messages": [], "count": 0, "status": "unexpected format"}
		except Exception as read_err:
			raise HTTPException(status_code=500, detail=f"Failed reading messages: {read_err}")
	except Exception as e:
		raise HTTPException(status_code=500, detail=str(e))

@app.get("/whatsapp/health")
def whatsapp_health():
	"""Report health of the WhatsApp Node listener.

	Returns:
	- running: boolean indicating process state
	- pid: OS process id when running
	- restart_count: number of auto‑restarts performed by heartbeat

	Examples:
	- http://127.0.0.1:8576/whatsapp/health
	"""
	alive = WHATSAPP_PROC is not None and WHATSAPP_PROC.poll() is None
	pid = WHATSAPP_PROC.pid if alive and WHATSAPP_PROC is not None else None
	return {
		"running": bool(alive),
		"pid": pid,
		"restart_count": RESTART_COUNT
	}

# Root endpoint
@app.get("/")
def root():
	"""Service ping endpoint.

	Returns a simple JSON message confirming the Tools API is up.
	"""
	return {"message": "Unified Tools API is running."}
