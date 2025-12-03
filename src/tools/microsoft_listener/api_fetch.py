# api_fetch.py
import json
import requests
import time
from datetime import datetime, timedelta, timezone
import sys
import os
sys.path.append(os.path.dirname(__file__))
from login import login

# Track seen items
seen_events = set()
seen_tasks = set()

def get_headers():
    access_token = login()
    return {"Authorization": f"Bearer {access_token}"}

def get_new_emails():
    try:
        url = "https://graph.microsoft.com/v1.0/me/mailFolders/Inbox/messages?$top=10&$orderby=receivedDateTime desc"
        resp = requests.get(url, headers=get_headers(), timeout=10).json().get("value", [])
        unread_emails = [mail for mail in resp if not mail.get("isRead", True)]
        return unread_emails
    except Exception as e:
        print(f"Error fetching emails: {e}")
        return []

def get_upcoming_events():
    global seen_events
    try:
        url = "https://graph.microsoft.com/v1.0/me/events?$top=20&$orderby=start/dateTime asc"
        resp = requests.get(url, headers=get_headers(), timeout=10).json().get("value", [])
        reminders = []
        new_events = []
        now = datetime.now(timezone.utc)
        for ev in resp:
            # Track new events
            if ev["id"] not in seen_events:
                new_events.append(ev)
                seen_events.add(ev["id"])
            
            start_str = ev["start"]["dateTime"]
            try:
                if start_str.endswith('Z'):
                    start_dt = datetime.fromisoformat(start_str.replace('Z', '+00:00'))
                else:
                    start_dt = datetime.fromisoformat(start_str)
                if start_dt.tzinfo is None:
                    start_dt = start_dt.replace(tzinfo=timezone.utc)
            except Exception:
                continue
            reminder_times = [
                (start_dt - timedelta(days=1), "1 day before"),
                (start_dt - timedelta(hours=1), "1 hour before"),
                (start_dt - timedelta(minutes=15), "15 minutes before")
            ]
            for r_time, label in reminder_times:
                if r_time.tzinfo is None:
                    r_time = r_time.replace(tzinfo=timezone.utc)
                if now <= r_time < now + timedelta(seconds=30):
                    reminders.append({
                        "event": ev["subject"],
                        "reminder": label,
                        "start": start_str,
                        "reminder_time": r_time.isoformat()
                    })
        return {"events": new_events, "reminders": reminders}
    except Exception as e:
        print(f"Error fetching events: {e}")
        return {"events": [], "reminders": []}

def get_pending_tasks():
    global seen_tasks
    try:
        url = "https://graph.microsoft.com/v1.0/me/todo/lists"
        lists = requests.get(url, headers=get_headers(), timeout=10).json().get("value", [])
        all_tasks = []
        new_tasks = []
        for lst in lists:
            # Filter to only get incomplete tasks
            t_url = f"https://graph.microsoft.com/v1.0/me/todo/lists/{lst['id']}/tasks?$filter=status ne 'completed'"
            t_resp = requests.get(t_url, headers=get_headers(), timeout=10).json().get("value", [])
            for task in t_resp:
                all_tasks.append(task)
                if task["id"] not in seen_tasks:
                    new_tasks.append(task)
                    seen_tasks.add(task["id"])
        return {"tasks": all_tasks, "new_tasks": new_tasks}
    except Exception as e:
        print(f"Error fetching tasks: {e}")
        return {"tasks": [], "new_tasks": []}

if __name__ == "__main__":
    print("Polling for new emails, events, and tasks every 30 seconds...")
    while True:
        try:
            emails = get_new_emails()
            for mail in emails:
                print(f"[Email] {mail['subject']} from {mail['from']['emailAddress']['name']}")
            
            events_data = get_upcoming_events()
            for ev in events_data["events"]:
                print(f"[Event] {ev['subject']} at {ev['start']['dateTime']}")
            for reminder in events_data["reminders"]:
                print(f"[Reminder] {reminder['event']} - {reminder['reminder']} (Event at {reminder['start']})")
            
            tasks_data = get_pending_tasks()
            for task in tasks_data["new_tasks"]:
                print(f"[New Task] {task['title']} - status: {task['status']}")
            
            time.sleep(30)
        except Exception as e:
            print("Error:", e)
            time.sleep(30)
