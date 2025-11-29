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
seen_emails = set()
seen_events = set()
seen_tasks = set()

def get_headers():
    access_token = login()
    return {"Authorization": f"Bearer {access_token}"}

def get_new_emails():
    global seen_emails
    url = "https://graph.microsoft.com/v1.0/me/mailFolders/Inbox/messages?$top=10&$orderby=receivedDateTime desc"
    resp = requests.get(url, headers=get_headers()).json().get("value", [])
    unread_emails = [mail for mail in resp if not mail.get("isRead", True)]
    new_unread_emails = [mail for mail in unread_emails if mail["id"] not in seen_emails]
    for mail in new_unread_emails:
        seen_emails.add(mail["id"])
    return {"status": "success", "emails": new_unread_emails}

def get_upcoming_events():
    url = "https://graph.microsoft.com/v1.0/me/events?$top=20&$orderby=start/dateTime asc"
    resp = requests.get(url, headers=get_headers()).json().get("value", [])
    reminders = []
    now = datetime.now(timezone.utc)
    for ev in resp:
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
    return reminders

def get_pending_tasks():
    url = "https://graph.microsoft.com/v1.0/me/todo/lists"
    lists = requests.get(url, headers=get_headers()).json().get("value", [])
    tasks = []
    for lst in lists:
        t_url = f"https://graph.microsoft.com/v1.0/me/todo/lists/{lst['id']}/tasks"
        t_resp = requests.get(t_url, headers=get_headers()).json().get("value", [])
        tasks.extend(t_resp)
    return tasks

if __name__ == "__main__":
    print("Polling for new emails, events, and tasks every 30 seconds...")
    while True:
        try:
            for mail in get_new_emails()["emails"]:
                print(f"[Email] {mail['subject']} from {mail['from']['emailAddress']['name']}")
            for reminder in get_upcoming_events():
                print(reminder)
                print(f"[Reminder] {reminder['event']} - {reminder['reminder']} (Event at {reminder['start']})")
            for task in get_pending_tasks():
                print(f"[Task] {task['title']} - status: {task['status']}")
            time.sleep(30)
        except Exception as e:
            print("Error:", e)
            time.sleep(30)
