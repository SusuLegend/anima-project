from email_api import authenticate_gmail, get_new_email_subject_and_body
import threading
import time
from typing import List
from fastapi import FastAPI
from pydantic import BaseModel
import os

app = FastAPI(title="Notification API", description="Unified notification system for email (Gmail)")

class EmailNotification(BaseModel):
    subject: str
    body: str
    sender: str

service = None
email_notifications = []

def poll_emails():
    global service, email_notifications
    while True:
        try:
            new_emails = get_new_email_subject_and_body(service)
            if new_emails:
                email_notifications.extend(new_emails)
        except Exception as e:
            print(f"Email polling error: {e}")
        time.sleep(10)

@app.on_event("startup")
def startup_event():
    global service
    service = authenticate_gmail(os.path.join(os.path.dirname(__file__), "email_credential.json"), "token.pickle")
    thread = threading.Thread(target=poll_emails, daemon=True)
    thread.start()

@app.get("/notifications/email", response_model=List[EmailNotification])
def get_email_notifications():
    global email_notifications
    notifications = email_notifications.copy()
    email_notifications.clear()
    return notifications

@app.get("/health")
def health():
    return {"status": "ok"}
